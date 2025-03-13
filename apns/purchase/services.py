# iap_app/ai_services.py

import requests
from django.conf import settings
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from configurations.models import AppleAppConfiguration
from .models import Purchase
from django.db import transaction
from django.contrib.auth import get_user_model
import logging
import json

logger = logging.getLogger(__name__)

User = get_user_model()

def calculate_expiration_date(subscription_type, current_time=None):
    """
    根据订阅类型计算订阅到期时间。

    参数:
        subscription_type (str): 订阅类型，支持 "Weekly_Subscription", "Monthly_Subscription", "Yearly_Subscription"
        current_time (datetime): 当前时间，如果为None则使用当前时间

    返回:
        datetime: 订阅到期的时间（带时区信息）
    """
    # 获取当前时间（带时区信息）
    if current_time is None:
        current_time = timezone.now()

    if subscription_type == "Weekly_Subscription":
        expiration_time = current_time + relativedelta(weeks=1)
    elif subscription_type == "Monthly_Subscription":
        expiration_time = current_time + relativedelta(months=1)
    elif subscription_type == "Yearly_Subscription":
        expiration_time = current_time + relativedelta(years=1)
    else:
        raise ValueError("未知的订阅类型: {}".format(subscription_type))

    return expiration_time


class AppleIAPService:
    @staticmethod
    def verify_receipt(receipt_data, app_id):
        """
        验证Apple购买收据
        
        参数:
            receipt_data (str): 苹果收据数据
            app_id (str): 应用ID，用于获取对应的配置
            
        返回:
            dict: 验证结果
        """
        try:
            app_config = AppleAppConfiguration.objects.get(name=app_id)
            shared_secret = app_config.shared_secret
            
            payload = {
                'receipt-data': receipt_data,
                'password': shared_secret,  # 使用配置中的共享密钥
                'exclude-old-transactions': True
            }

            # 先尝试生产环境验证
            response = requests.post('https://buy.itunes.apple.com/verifyReceipt', json=payload, timeout=30)
            result = response.json()

            # 记录验证结果
            logger.info(f"Receipt verification result for app {app_id}: status={result.get('status')}")
            
            # 如果返回21007，表示在沙盒环境
            if result.get('status') == 21007:
                logger.info(f"Receipt is from sandbox environment, retrying with sandbox URL")
                response = requests.post('https://sandbox.itunes.apple.com/verifyReceipt', json=payload, timeout=30)
                result = response.json()
                logger.info(f"Sandbox verification result: status={result.get('status')}")
            
            # 处理各种错误状态
            status = result.get('status')
            if status != 0:
                error_messages = {
                    21000: 'App Store无法读取你提供的JSON数据',
                    21002: '收据数据不符合格式',
                    21003: '收据无法被验证',
                    21004: '你提供的共享密钥和账户的共享密钥不一致',
                    21005: '收据服务器当前不可用',
                    21006: '收据是有效的，但订阅服务已经过期',
                    21008: '收据信息是产品环境中使用，但却被发送到测试环境中验证',
                }
                error_message = error_messages.get(status, f'未知错误，状态码: {status}')
                logger.error(f"Receipt verification error: {error_message}")
            
            return result
            
        except AppleAppConfiguration.DoesNotExist:
            logger.error(f"App configuration not found for app_id: {app_id}")
            raise ValueError(f"找不到应用配置: {app_id}")
        except requests.RequestException as e:
            logger.error(f"Network error during receipt verification: {str(e)}")
            raise ValueError(f"验证收据时网络错误: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during receipt verification: {str(e)}")
            raise ValueError(f"验证收据时发生错误: {str(e)}")

    @staticmethod
    @transaction.atomic
    def process_receipt(user_id, receipt_data, product_id, app_id, transaction_id, original_transaction_id=None):
        """
        处理并验证收据，创建购买记录
        
        参数:
            user_id (int): 用户ID
            receipt_data (str): 苹果收据数据
            product_id (str): 产品ID
            app_id (str): 应用ID
            transaction_id (str): 交易ID
            original_transaction_id (str): 原始交易ID，用于续订
            
        返回:
            Purchase: 创建或更新的购买记录
        """
        try:
            # 检查交易是否已存在，防止重复处理
            existing_purchase = Purchase.objects.filter(transaction_id=transaction_id).first()
            if existing_purchase:
                logger.info(f"Transaction {transaction_id} already processed.")
                return existing_purchase
                
            verification_result = AppleIAPService.verify_receipt(receipt_data, app_id)
            status = verification_result.get('status')
            
            # 创建购买记录
            purchase = Purchase.objects.create(
                user_id=user_id,
                app_id=app_id,
                product_id=product_id,
                transaction_id=transaction_id,
                original_transaction_id=original_transaction_id or transaction_id,
                receipt_data=receipt_data,
                purchase_date=timezone.now(),
                is_active=False,
                is_successful=(status == 0),
                status='success' if status == 0 else 'failed',
                notes=json.dumps(verification_result, indent=2)
            )
            
            # 如果验证成功，设置过期时间
            if status == 0:
                # 从验证结果中提取过期时间，如果没有则计算
                receipt_info = verification_result.get('receipt', {})
                latest_receipt_info = verification_result.get('latest_receipt_info', [])
                
                if latest_receipt_info and isinstance(latest_receipt_info, list) and len(latest_receipt_info) > 0:
                    # 使用最新的收据信息
                    latest_info = latest_receipt_info[0]
                    expires_date_ms = latest_info.get('expires_date_ms')
                    if expires_date_ms:
                        expires_at = timezone.datetime.fromtimestamp(int(expires_date_ms) / 1000, tz=timezone.utc)
                        purchase.expires_at = expires_at
                    else:
                        # 如果没有过期时间，根据产品ID计算
                        purchase.expires_at = calculate_expiration_date(product_id)
                else:
                    # 如果没有收据信息，根据产品ID计算
                    purchase.expires_at = calculate_expiration_date(product_id)
                
                purchase.is_active = True
                purchase.save()
                
                logger.info(f"Successfully processed transaction {transaction_id} for user {user_id}")
            else:
                logger.warning(f"Failed to verify receipt for transaction {transaction_id}, status: {status}")
            
            return purchase
            
        except Exception as e:
            logger.error(f"Error processing receipt: {str(e)}")
            raise

    @staticmethod
    @transaction.atomic
    def process_receipt_from_notification(notification_data, app_id):
        """
        处理来自服务器通知的收据
        
        参数:
            notification_data (dict): 通知数据
            app_id (str): 应用ID
            
        返回:
            Purchase: 更新的购买记录
        """
        try:
            notification_type = notification_data.get('notification_type')
            latest_receipt = notification_data.get('latest_receipt')
            latest_receipt_info = notification_data.get('latest_receipt_info', {})
            
            if not latest_receipt:
                logger.error("No receipt data in notification")
                raise ValueError("通知中没有收据数据")
                
            # 验证收据
            verification_result = AppleIAPService.verify_receipt(latest_receipt, app_id)
            status = verification_result.get('status')
            
            if status != 0:
                logger.error(f"Receipt verification failed with status {status}")
                raise ValueError(f"收据验证失败，状态码: {status}")
                
            # 获取交易信息
            transaction_id = latest_receipt_info.get('transaction_id')
            original_transaction_id = latest_receipt_info.get('original_transaction_id')
            product_id = latest_receipt_info.get('product_id')
            
            if not transaction_id or not original_transaction_id:
                logger.error("Missing transaction IDs in notification")
                raise ValueError("通知中缺少交易ID")
                
            # 查找原始购买记录
            purchase = None
            
            # 首先尝试通过transaction_id查找
            purchase = Purchase.objects.filter(transaction_id=transaction_id).first()
            
            # 如果找不到，尝试通过original_transaction_id查找
            if not purchase and original_transaction_id:
                purchase = Purchase.objects.filter(
                    original_transaction_id=original_transaction_id
                ).order_by('-created_at').first()
                
            # 如果仍然找不到，可能是新的订阅，创建新记录
            if not purchase:
                # 从通知中提取用户ID，如果没有则无法处理
                user_id = notification_data.get('user_id')
                if not user_id:
                    logger.error("Cannot process notification: missing user_id")
                    raise ValueError("无法处理通知：缺少用户ID")
                    
                purchase = Purchase.objects.create(
                    user_id=user_id,
                    app_id=app_id,
                    product_id=product_id,
                    transaction_id=transaction_id,
                    original_transaction_id=original_transaction_id,
                    receipt_data=latest_receipt,
                    purchase_date=timezone.now(),
                    is_active=False,
                    is_successful=False,
                    status='pending',
                    notes=f"从通知创建: {notification_type}"
                )
                
            # 根据通知类型更新购买记录
            if notification_type == 'DID_RENEW':
                # 续订成功
                purchase.is_active = True
                purchase.is_successful = True
                purchase.status = 'success'
                
                # 更新过期时间
                expires_date_ms = latest_receipt_info.get('expires_date_ms')
                if expires_date_ms:
                    expires_at = timezone.datetime.fromtimestamp(int(expires_date_ms) / 1000, tz=timezone.utc)
                    purchase.expires_at = expires_at
                else:
                    purchase.expires_at = calculate_expiration_date(product_id)
                    
            elif notification_type == 'CANCEL':
                # 取消订阅
                purchase.is_active = False
                purchase.status = 'failed'
                purchase.notes = f"{purchase.notes}\n取消订阅: {timezone.now()}"
                
            elif notification_type == 'DID_CHANGE_RENEWAL_STATUS':
                # 更新续订状态
                auto_renew_status = notification_data.get('auto_renew_status')
                purchase.notes = f"{purchase.notes}\n续订状态变更: {auto_renew_status} at {timezone.now()}"
                
            purchase.save()
            logger.info(f"Processed {notification_type} notification for transaction {transaction_id}")
            
            return purchase
            
        except Exception as e:
            logger.error(f"Error processing notification: {str(e)}")
            raise

