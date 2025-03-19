from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
import requests
import json
from django.conf import settings
from celery import shared_task
from configurations.models import AppleAppConfiguration
import logging
from .services import UserService

logger = logging.getLogger(__name__)


class Purchase(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    NOTIFY_CHOICES = [
        ('INITIAL_BUY', '用户首次订阅'),
        ('DID_CHANGE_RENEWAL_STATUS', '订阅状态更改'),
        ('INTERACTIVE_RENEWAL', '通过互动方式续订订阅'),
        ('DID_CHANGE_RENEWAL_PREF', "订阅计划更改"),
        ('CONSUMPTION_REQUEST', '发起退款'),
        ('CANCEL', '退订'),
        ('DID_FAIL_TO_RENEW', '账单问题而未能续订的订阅'),
        ('DID_RECOVER', '指示之前未能续订的已过期订阅成功自动续订'),
        ('DID_RENEW', '客户的订阅已成功自动续订至新的交易周期'),
        ('PRICE_INCREASE_CONSENT', '用户同意自动续订的价格调整，继续续订'),
        ('REFUND', '已成功退还了应用内购买的消耗品、非消耗品或非续订订阅的交易'),
        ('REVOKE', '用户通过家庭共享获得的内购项目不再通过共享可用')
    ]

    user_id = models.IntegerField('用户ID', db_index=True, help_text='UserCenter的用户ID')
    app_id = models.CharField("具体苹果的应用", max_length=255, blank=True, null=True)
    product_id = models.CharField(max_length=255, blank=True, null=True)
    transaction_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    original_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    receipt_data = models.TextField(blank=True, null=True)
    purchase_date = models.DateTimeField()
    expires_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_successful = models.BooleanField(default=False)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    notification_type = models.CharField('订单通知类型', max_length=255, blank=True, null=True, choices=NOTIFY_CHOICES)

    # 添加状态字段，便于跟踪订单状态
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # 添加备注字段，记录处理过程中的问题
    notes = models.TextField(blank=True, null=True, help_text='处理过程中的备注信息')

    class Meta:
        verbose_name = '苹果内购'
        verbose_name_plural = '苹果内购'
        ordering = ['-created_at']
        # 添加索引以提高查询性能
        indexes = [
            models.Index(fields=['user_id', 'is_active']),
            models.Index(fields=['original_transaction_id']),
        ]

    def __str__(self):
        return f"用户ID:{self.user_id} - {self.product_id} - {'成功' if self.is_successful else '处理中'}"

    @classmethod
    def verify_receipt(cls, receipt_data, sandbox=True, app_id='pocket_ai'):
        """
        验证苹果收据

        Args:
            receipt_data: 苹果收据数据
            sandbox: 是否使用沙盒环境
            app_id: 应用ID，用于获取对应的共享密钥

        Returns:
            dict: 验证结果
        """
        try:
            # 根据环境选择验证URL
            if sandbox:
                verify_url = 'https://sandbox.itunes.apple.com/verifyReceipt'
            else:
                verify_url = 'https://buy.itunes.apple.com/verifyReceipt'

            # 获取应用配置
            shared_secret = None
            if app_id:
                try:
                    config = AppleAppConfiguration.objects.get(name=app_id)
                    shared_secret = config.shared_secret
                except AppleAppConfiguration.DoesNotExist:
                    logger.error(f"找不到应用 {app_id} 的配置")
                    # 如果找不到特定应用的配置，尝试使用默认配置
                    shared_secret = settings.APPSTORE_SHARED_SECRET
            else:
                # 使用默认配置
                shared_secret = settings.APPSTORE_SHARED_SECRET

            if not shared_secret:
                raise ValueError("缺少App Store共享密钥")

            # 准备请求数据
            request_data = {
                'receipt-data': receipt_data,
                'password': shared_secret,
                'exclude-old-transactions': False,  # 包含所有交易记录
                'include-history': True  # 确保包含历史记录
            }

            # 发送验证请求
            response = requests.post(
                verify_url,
                data=json.dumps(request_data),
                headers={'Content-Type': 'application/json'},
                timeout=30  # 设置超时时间
            )

            # 解析响应
            result = response.json()

            # 如果状态码为21007，表示这是沙盒收据，需要使用沙盒环境重新验证
            if result.get('status') == 21007 and not sandbox:
                return cls.verify_receipt(receipt_data, sandbox=True, app_id=app_id)

            # 如果状态码为21008，表示这是正式环境收据，需要使用正式环境重新验证
            if result.get('status') == 21008 and sandbox:
                return cls.verify_receipt(receipt_data, sandbox=False, app_id=app_id)

            return result
        except Exception as e:
            logger.error(f"收据验证错误: {str(e)}")
            return {'status': -1, 'error': str(e)}

    @classmethod
    def process_verification_result(cls, verification_result, user_id):
        """
        处理验证结果，创建或更新购买记录

        Args:
            verification_result: 验证结果
            user_id: 用户ID

        Returns:
            Purchase: 创建或更新的购买记录
        """
        try:
            if verification_result.get('status') != 0:
                logger.error(f"Receipt verification failed: {verification_result}")
                return None

            receipt = verification_result.get('receipt', {})
            latest_receipt_info = verification_result.get('latest_receipt_info', [])

            # 如果有latest_receipt_info，使用最新的一条
            if latest_receipt_info and isinstance(latest_receipt_info, list):
                transaction = latest_receipt_info[-1]
            # 否则使用receipt中的in_app最新的一条
            elif 'in_app' in receipt and receipt['in_app']:
                transaction = receipt['in_app'][-1]
            else:
                logger.error("No transaction found in verification result")
                return None

            # 提取交易信息
            transaction_id = transaction.get('transaction_id')
            original_transaction_id = transaction.get('original_transaction_id')
            product_id = transaction.get('product_id')
            purchase_date_ms = int(transaction.get('purchase_date_ms', 0))
            expires_date_ms = int(transaction.get('expires_date_ms', 0)) if 'expires_date_ms' in transaction else None

            from django.utils import timezone
            import datetime

            # 转换时间戳为datetime对象
            purchase_date = timezone.make_aware(
                datetime.datetime.fromtimestamp(purchase_date_ms / 1000)
            )

            expires_at = None
            if expires_date_ms:
                expires_at = timezone.make_aware(
                    datetime.datetime.fromtimestamp(expires_date_ms / 1000)
                )

            # 检查是否已存在该交易
            purchase, created = cls.objects.update_or_create(
                transaction_id=transaction_id,
                defaults={
                    'user_id': user_id,
                    'app_id': 'pocket_ai',
                    'product_id': product_id,
                    'original_transaction_id': original_transaction_id,
                    'receipt_data': verification_result.get('latest_receipt', verification_result.get('receipt-data')),
                    'purchase_date': purchase_date,
                    'expires_at': expires_at,
                    'is_active': True,
                    'is_successful': True,
                    'status': 'success',
                    'notes': f"验证成功记录"
                }
            )

            return purchase
        except Exception as e:
            logger.error(f"Process verification result error: {str(e)}")
            return None

    @shared_task
    def process_notification(notification_data):
        """
        处理苹果服务器发送的通知

        Args:
            notification_data: 通知数据
        """
        try:
            notification_type = notification_data.get('notification_type')
            unified_receipt = notification_data.get('unified_receipt', {})
            latest_receipt = unified_receipt.get('latest_receipt')
            latest_receipt_info = unified_receipt.get('latest_receipt_info', [])
            app_id = 'pocket_ai'

            logger.info(f"收到苹果通知: 类型={notification_type}, 应用={app_id}")

            if not latest_receipt or not latest_receipt_info:
                logger.error("通知中缺少收据信息")
                return

            # 处理每个交易前，先获取最新的到期时间
            latest_expires_date = None
            for transaction in latest_receipt_info:
                if 'expires_date_ms' in transaction:
                    expires_date_ms = int(transaction.get('expires_date_ms', 0))
                    if not latest_expires_date or expires_date_ms > latest_expires_date:
                        latest_expires_date = expires_date_ms

            # 验证收据
            verification_result = Purchase.verify_receipt(latest_receipt, app_id=app_id)

            if verification_result.get('status') != 0:
                logger.error(f"通知收据验证失败: {verification_result}")
                return

            # 处理每个交易
            for transaction in latest_receipt_info:
                transaction_id = transaction.get('transaction_id')
                original_transaction_id = transaction.get('original_transaction_id')
                product_id = transaction.get('product_id')
                purchase_date_ms = int(transaction.get('purchase_date_ms', 0))
                expires_date_ms = int(
                    transaction.get('expires_date_ms', 0)) if 'expires_date_ms' in transaction else None

                from django.utils import timezone
                import datetime

                # 转换时间戳为datetime对象
                purchase_date = timezone.make_aware(
                    datetime.datetime.fromtimestamp(purchase_date_ms / 1000)
                )

                expires_at = None
                if expires_date_ms:
                    expires_at = timezone.make_aware(
                        datetime.datetime.fromtimestamp(expires_date_ms / 1000)
                    )

                # 使用最新的到期时间，而不是当前交易的到期时间
                if latest_expires_date:
                    expires_at = timezone.make_aware(
                        datetime.datetime.fromtimestamp(latest_expires_date / 1000)
                    )

                # 根据通知类型确定购买状态
                is_active = True
                status = 'success'
                notes = f"通知类型: {notification_type}"

                # 严谨处理每种通知类型
                if notification_type == 'INITIAL_BUY':
                    # 用户首次订阅，激活订阅
                    is_active = True
                    status = 'success'
                    notes += ", 用户首次订阅"

                elif notification_type == 'DID_CHANGE_RENEWAL_STATUS':
                    # 订阅状态更改，需要检查auto_renew_status
                    auto_renew_status = notification_data.get('auto_renew_status', False)
                    if auto_renew_status:
                        notes += ", 用户开启了自动续订"
                    else:
                        notes += ", 用户关闭了自动续订"
                        # 注意：关闭自动续订不影响当前订阅的有效性，只是到期后不再续订
                        # 检查是否已过期
                        if expires_at and expires_at < timezone.now():
                            is_active = False
                            status = 'failed'
                            notes += ", 订阅已过期"
                        else:
                            notes += ", 但当前订阅仍然有效至到期日"

                elif notification_type == 'INTERACTIVE_RENEWAL':
                    # 用户手动续订
                    is_active = True
                    status = 'success'
                    notes += ", 用户手动续订"

                elif notification_type == 'DID_CHANGE_RENEWAL_PREF':
                    # 用户更改了订阅计划
                    auto_renew_product_id = notification_data.get('auto_renew_product_id')
                    notes += f", 用户更改订阅计划为: {auto_renew_product_id}"
                    # 计划更改不影响当前订阅的有效性

                elif notification_type == 'CONSUMPTION_REQUEST':
                    # 发起退款请求，但尚未处理
                    notes += ", 用户发起退款请求"
                    # 此时不改变订阅状态，等待REFUND通知

                elif notification_type == 'CANCEL':
                    # 用户取消订阅
                    notes += ", 用户取消订阅"
                    # 重要：取消订阅不会立即失效，而是在当前订阅周期结束后才失效
                    if expires_at and expires_at < timezone.now():
                        is_active = False
                        status = 'failed'
                        notes += ", 订阅已过期"
                    else:
                        notes += ", 但当前订阅仍然有效至到期日"

                elif notification_type == 'DID_FAIL_TO_RENEW':
                    # 由于账单问题未能续订
                    notes += ", 由于账单问题未能续订"
                    # 检查是否已过期
                    if expires_at and expires_at < timezone.now():
                        is_active = False
                        status = 'failed'
                        notes += ", 订阅已过期"
                    else:
                        notes += ", 但当前订阅仍然有效至到期日"

                elif notification_type == 'DID_RECOVER':
                    # 之前失败的订阅恢复
                    is_active = True
                    status = 'success'
                    notes += ", 之前失败的订阅已恢复"

                elif notification_type == 'DID_RENEW':
                    # 订阅自动续订成功
                    is_active = True
                    status = 'success'
                    notes += ", 订阅自动续订成功"

                elif notification_type == 'PRICE_INCREASE_CONSENT':
                    # 用户同意价格调整
                    notes += ", 用户同意价格调整"
                    # 不改变订阅状态

                elif notification_type == 'REFUND':
                    # 退款成功
                    is_active = False
                    status = 'failed'
                    notes += ", 退款成功，订阅已失效"
                    # 退款通常会立即使订阅失效

                elif notification_type == 'REVOKE':
                    # 家庭共享被撤销
                    notes += ", 家庭共享被撤销"
                    # 检查是否已过期
                    if expires_at and expires_at < timezone.now():
                        is_active = False
                        status = 'failed'
                        notes += ", 订阅已过期"
                    else:
                        notes += ", 但当前订阅仍然有效至到期日"

                # 查找用户ID
                # 首先尝试通过original_transaction_id查找
                existing_purchase = Purchase.objects.filter(
                    original_transaction_id=original_transaction_id
                ).first()

                user_id = None
                if existing_purchase:
                    user_id = existing_purchase.user_id

                if not user_id:
                    # 如果找不到用户ID，记录错误并跳过
                    logger.error(f"无法找到交易 {transaction_id} 的用户ID")
                    continue

                # 更新或创建购买记录
                purchase, created = Purchase.objects.update_or_create(
                    transaction_id=transaction_id,
                    defaults={
                        'user_id': user_id,
                        'app_id': app_id,
                        'product_id': product_id,
                        'original_transaction_id': original_transaction_id,
                        'receipt_data': latest_receipt,
                        'purchase_date': purchase_date,
                        'expires_at': expires_at,
                        'is_active': is_active,
                        'is_successful': status == 'success',
                        'status': status,
                        'notification_type': notification_type,
                        'notes': notes + (", 新建记录" if created else ", 更新记录")
                    }
                )

                logger.info(
                    f"处理通知: 类型={notification_type}, 用户ID={user_id}, 产品={product_id}, 状态={status}, 到期时间={expires_at}")

                # 更新用户权限
                Purchase.update_user_privileges(user_id, purchase)

        except Exception as e:
            logger.exception(f"处理通知时出错: {str(e)}")

    @classmethod
    def update_user_privileges(cls, user_id, purchase):
        """根据购买记录更新用户权限"""
        try:
            from django.utils import timezone

            # 获取用户所有有效的订阅，按产品分组
            active_subscriptions = {}

            # 查询用户所有有效的订阅
            all_subscriptions = cls.objects.filter(
                user_id=user_id,
                is_active=True,
                is_successful=True,
                expires_at__gt=timezone.now()
            )

            # 按产品分组，找出每个产品的最新到期时间
            for sub in all_subscriptions:
                product_id = sub.product_id
                if product_id not in active_subscriptions or sub.expires_at > active_subscriptions[
                    product_id].expires_at:
                    active_subscriptions[product_id] = sub

            # 检查用户是否有任何有效订阅
            has_active_subscription = bool(active_subscriptions)

            # 如果有有效订阅，使用最晚的到期时间
            latest_expires_at = None
            if has_active_subscription:
                # 找出最晚的到期时间
                for product_id, sub in active_subscriptions.items():
                    if latest_expires_at is None or sub.expires_at > latest_expires_at:
                        latest_expires_at = sub.expires_at

                logger.info(f"用户 {user_id} 有有效订阅，最晚到期时间: {latest_expires_at}")

                # 更新用户会员状态为有效
                UserService.update_premium_status(
                    user_id=user_id,
                    is_premium=True,
                    expires_at=latest_expires_at
                )
            else:
                logger.info(f"用户 {user_id} 没有有效订阅，取消会员状态")

                # 更新用户会员状态为无效
                UserService.update_premium_status(
                    user_id=user_id,
                    is_premium=False
                )

        except Exception as e:
            logger.exception(f"更新用户权限时出错: {str(e)}")