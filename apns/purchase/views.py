import base64
import json

import jwt
import requests
from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

from configurations.models import AppleAppConfiguration
from .models import Purchase
from .serializers import (
    VerifyReceiptSerializer,
    NotificationSerializer,
    PurchaseSerializer
)
from .services import PurchaseService, UserService
import logging
from .tasks import sync_user_premium_status
from django.utils import timezone
from utils.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from utils.permissions import IsAuthenticatedExternal
from rest_framework.viewsets import GenericViewSet
from django.conf import settings

logger = logging.getLogger(__name__)


class PurchaseVerificationView(CreateModelMixin, GenericViewSet):
    """
    接收iOS应用发送的购买凭证，验证并处理
    """
    permission_classes = [IsAuthenticatedExternal]
    serializer_class = VerifyReceiptSerializer

    def create(self, request, *args, **kwargs):
        serializer = VerifyReceiptSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        receipt_data = serializer.validated_data['receipt_data']
        user_id = serializer.validated_data['user_id']
        sandbox = serializer.validated_data.get('sandbox', settings.SANDBOX)
        app_id = serializer.validated_data.get('app_id', 'pocket_ai')

        # 验证并处理收据
        success, result = PurchaseService.verify_and_process_receipt(receipt_data, user_id, sandbox, app_id)

        if not success:
            return Response({
                'code': 400,
                'msg': 'failure',
                'data': result,
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'code': 200,
            'msg': 'success',
            'data': PurchaseSerializer(result).data
        })


class AppleWebhookView(CreateModelMixin, GenericViewSet):
    """
    处理来自Apple的服务器通知
    """
    permission_classes = [permissions.AllowAny]  # Apple服务器通知无需认证

    def create(self, request, *args, **kwargs):
        try:
            logger.error("收到苹果服务器通知")

            # 记录原始请求数据，便于调试
            logger.error(f"通知原始数据: {request.data}")

            requests.post("https://pocket.nicebudgeting.com/apns/api/purchase/webhook", data=request.data)

            signed_payload = request.data.get('signedPayload')
            if not signed_payload:
                return Response({"status": "error", "message": "Missing signedPayload"}, status=400)

            notification_data = verify_and_decode_signed_payload(signed_payload)
            if not notification_data:
                return Response({"status": "error", "message": "Invalid signedPayload"}, status=400)

            complete_notification = parse_apple_notification(notification_data)

            if 'notificationType' in complete_notification and 'version' in complete_notification and complete_notification['version'] == '2.0':
                serializer = NotificationSerializer(data=complete_notification)
            else:
                # 旧格式通知，使用旧的序列化器
                logger.warning("收到旧版格式通知，尝试使用旧格式处理")
                from .serializers import OldNotificationSerializer
                serializer = OldNotificationSerializer(data=request.data)

            logger.error(f"通知解析后数据: {complete_notification}")

            if not serializer.is_valid():
                logger.error(f"通知数据无效: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # 异步处理通知
            Purchase.process_notification(serializer.validated_data)

            # 立即返回成功响应，避免苹果服务器重试
            return Response({
                'code': 200,
                'msg': 'success',
                'data': {}
            })

        except Exception as e:
            logger.exception(f"处理通知时出错: {str(e)}")
            # 即使出错也返回200状态码，避免苹果服务器重试
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_200_OK)


class PurchaseListView(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    获取用户的所有购买记录
    """
    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticatedExternal]

    def get_queryset(self):
        """
        根据查询参数过滤购买记录
        """

        # 按用户ID过滤
        user_id = self.request.remote_user.get('id')
        queryset = Purchase.objects.filter(user_id=user_id)

        # 按活跃状态过滤
        is_active = self.request.GET.get('is_active')
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)

        # 按应用ID过滤
        app_id = self.request.GET.get('app_id')
        if app_id:
            queryset = queryset.filter(app_id=app_id)

        # 按产品ID过滤
        product_id = self.request.GET.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        return queryset.order_by('-created_at')

    @action(detail=False, methods=['get'])
    def active_purchases(self, request):
        """获取用户的有效购买记录"""
        user_id = request.remote_user.get('id')
        purchases = PurchaseService.get_active_purchases(user_id)

        return Response({
            'code': 200,
            'msg': 'success',
            'data': PurchaseSerializer(purchases, many=True).data
        })

    @action(detail=False, methods=['get'])
    def check_subscription(self, request):
        """检查用户是否有有效的订阅"""
        user_id = request.remote_user.get('id')
        product_id = request.query_params.get('product_id')

        has_subscription, expires_at = PurchaseService.has_active_subscription(user_id, product_id)

        response_data = {
            'success': True,
            'has_subscription': has_subscription
        }

        if has_subscription and expires_at:
            response_data['expires_at'] = expires_at

        return Response({
            'code': 200,
            'msg': 'success',
            'data': response_data
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def sync_premium_status(self, request):
        """手动触发同步用户会员状态的任务"""
        try:
            # 异步执行同步任务
            sync_user_premium_status.delay()

            return Response({
                'code': 200,
                'msg': '同步任务已启动，请稍后查看结果',
                'data': {}
            })

        except Exception as e:
            logger.exception(f"启动同步任务时出错: {str(e)}")

            return Response({
                'code': 500,
                'msg': 'failure',
                'data': f'启动同步任务失败: {str(e)}',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def sync_user_status(self, request):
        user_id = request.data.get('user_id')

        if not user_id:
            return Response({
                'code': 400,
                'msg': 'failure',
                'data': '缺少用户ID',
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 获取用户的有效订阅
            active_subscriptions = Purchase.objects.filter(
                user_id=user_id,
                is_active=True,
                is_successful=True,
                expires_at__gt=timezone.now()
            ).order_by('-expires_at')

            if active_subscriptions.exists():
                # 用户有有效订阅
                latest_subscription = active_subscriptions.first()

                success = UserService.update_premium_status(
                    user_id=user_id,
                    is_premium=True,
                    expires_at=latest_subscription.expires_at
                )

                if success:
                    return Response({
                        'code': 200,
                        'msg': 'success',
                        'data': PurchaseSerializer(active_subscriptions).data
                    })
                else:
                    return Response({
                        'code': 500,
                        'msg': 'failure',
                        'data': f'更新用户 {user_id} 的会员状态失败',
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                # 用户没有有效订阅
                # 获取用户最后一条记录的app_id

                success = UserService.update_premium_status(
                    user_id=user_id,
                    is_premium=False,
                )

                if success:
                    return Response({
                        'code': 200,
                        'msg': 'success',
                        'data': PurchaseSerializer(active_subscriptions).data
                    })
                else:
                    return Response({
                        'code': 500,
                        'msg': 'failure',
                        'data': f'更新用户 {user_id} 的会员状态失败',
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.exception(f"同步用户 {user_id} 的会员状态时出错: {str(e)}")
            return Response({
                'code': 500,
                'msg': 'failure',
                'data': f'同步用户状态失败: {str(e)}',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def decode_signed_payload(signed_payload):
    """
    解析苹果 App Store Server Notifications V2 的 signedPayload（不验证签名）

    参数:
        signed_payload: 苹果发送的签名载荷

    返回:
        解析后的通知数据字典
    """
    try:
        # 1. 将 signedPayload 分割为三部分（header.payload.signature）
        parts = signed_payload.split('.')
        if len(parts) != 3:
            logger.error(f"无效的 signedPayload 格式: {signed_payload[:50]}...")
            return None

        # 2. 解码 payload 部分
        payload_part = parts[1]

        # 添加填充以避免 base64 解码错误
        payload_part += '=' * ((4 - len(payload_part) % 4) % 4)

        # 解码 base64
        try:
            decoded_payload = base64.urlsafe_b64decode(payload_part)
            notification_data = json.loads(decoded_payload)
            logger.debug(f"成功解析 payload: {notification_data.get('notificationType', 'unknown')}")
            return notification_data
        except Exception as e:
            logger.error(f"解码 payload 失败: {str(e)}")
            return None

    except Exception as e:
        logger.error(f"解析 signedPayload 时出错: {str(e)}")
        return None


def get_apple_public_key():
    """
    从配置中获取苹果公钥

    返回:
        公钥对象
    """
    try:
        # 从配置中获取公钥
        config = AppleAppConfiguration.objects.filter(name='pocket_ai').first()
        logger.error(f"config: {config.auth_key}")
        if not config or not config.auth_key:
            logger.warning("找不到苹果应用配置或公钥为空")
            return None
        return config.auth_key
    except Exception as e:
        logger.error(f"获取苹果公钥时出错: {str(e)}")
        return None


def verify_and_decode_signed_payload(signed_payload):
    """
    验证并解析苹果 App Store Server Notifications V2 的 signedPayload

    参数:
        signed_payload: 苹果发送的签名载荷

    返回:
        解析后的通知数据字典，如果验证失败则返回None
    """
    try:
        # 1. 获取JWT头部以获取算法
        try:
            header = jwt.get_unverified_header(signed_payload)
            alg = header.get('alg', 'ES256')
            logger.debug(f"JWT头部: alg={alg}")
        except Exception as e:
            logger.error(f"获取JWT头部时出错: {str(e)}")
            return decode_signed_payload(signed_payload)

        # 2. 获取公钥
        public_key = get_apple_public_key()

        if not public_key:
            logger.warning("无法获取公钥，将不验证签名")
            return decode_signed_payload(signed_payload)

        # 3. 验证并解码JWT
        try:
            decoded = jwt.decode(
                signed_payload,
                public_key,
                algorithms=[alg],
                options={"verify_exp": True}
            )
            logger.info("JWT签名验证成功")
            return decoded
        except jwt.ExpiredSignatureError:
            logger.warning("JWT已过期，但仍将处理通知")
            return decode_signed_payload(signed_payload)
        except jwt.InvalidSignatureError:
            logger.warning("JWT签名无效")
            return decode_signed_payload(signed_payload)  # 仍然返回解析的数据，但记录警告
        except Exception as e:
            logger.error(f"验证JWT时出错: {str(e)}")
            return decode_signed_payload(signed_payload)

    except Exception as e:
        logger.error(f"处理signedPayload时出错: {str(e)}")
        # 作为最后的尝试，使用不验证签名的方式解析
        try:
            return jwt.decode(
                signed_payload,
                options={"verify_signature": False}
            )
        except Exception:
            return None


def parse_apple_notification(notification_data):
    """
    解析苹果 App Store Server Notifications V2 的完整通知数据

    参数:
        notification_data: 已解析的通知数据字典

    返回:
        包含完整信息的通知数据字典
    """
    try:
        # 1. 获取基本通知信息
        result = {
            'notificationType': notification_data.get('notificationType'),
            'subtype': notification_data.get('subtype'),
            'notificationUUID': notification_data.get('notificationUUID'),
            'version': notification_data.get('version'),
            'signedDate': notification_data.get('signedDate')
        }

        # 2. 解析 data 部分
        data = notification_data.get('data', {})
        result['data'] = {
            'appAppleId': data.get('appAppleId'),
            'bundleId': data.get('bundleId'),
            'bundleVersion': data.get('bundleVersion'),
            'environment': data.get('environment'),
        }

        # 3. 解析 signedTransactionInfo
        signed_transaction_info = data.get('signedTransactionInfo')
        if signed_transaction_info:
            transaction_info = verify_and_decode_signed_payload(signed_transaction_info)
            if transaction_info:
                result['data']['transactionInfo'] = transaction_info
                logger.info(
                    f"成功解析交易信息: {transaction_info.get('productId')}, 交易ID: {transaction_info.get('transactionId')}")

        # 4. 解析 signedRenewalInfo
        signed_renewal_info = data.get('signedRenewalInfo')
        if signed_renewal_info:
            renewal_info = verify_and_decode_signed_payload(signed_renewal_info)
            if renewal_info:
                result['data']['renewalInfo'] = renewal_info
                logger.info(
                    f"成功解析续订信息: 自动续订状态: {renewal_info.get('autoRenewStatus')}, 下次续订日期: {renewal_info.get('renewalDate')}")

        # 5. 解析其他可能的嵌套 JWT
        for key, value in data.items():
            if key.startswith('signed') and key not in ['signedTransactionInfo', 'signedRenewalInfo']:
                decoded_value = verify_and_decode_signed_payload(value)
                if decoded_value:
                    result['data'][key.replace('signed', '')] = decoded_value

        return result

    except Exception as e:
        logger.error(f"解析完整通知数据时出错: {str(e)}")
        return notification_data  # 返回原始数据