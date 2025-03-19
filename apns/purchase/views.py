from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Purchase
from .serializers import (
    VerifyReceiptSerializer,
    NotificationSerializer,
    PurchaseSerializer
)
from .services import PurchaseService, UserService
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import logging
from .tasks import sync_user_premium_status
from django.utils import timezone
from utils.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from utils.permissions import IsAuthenticatedExternal
from rest_framework.viewsets import GenericViewSet

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
        sandbox = serializer.validated_data.get('sandbox', True)
        app_id = serializer.validated_data.get('app_id', 'pocket_ai')

        # 验证并处理收据
        success, result = PurchaseService.verify_and_process_receipt(receipt_data, user_id, sandbox, app_id)

        if not success:
            return Response({
                'success': False,
                'message': result
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'data': PurchaseSerializer(result).data
        })


class AppleWebhookView(CreateModelMixin, GenericViewSet):
    """
    处理来自Apple的服务器通知
    """
    permission_classes = [permissions.AllowAny]  # Apple服务器通知无需认证

    def create(self, request, *args, **kwargs):
        try:
            logger.info("收到苹果服务器通知")

            # 记录原始请求数据，便于调试
            logger.debug(f"通知原始数据: {request.data}")

            serializer = NotificationSerializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"通知数据无效: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # 异步处理通知
            Purchase.process_notification.delay(serializer.validated_data)

            # 立即返回成功响应，避免苹果服务器重试
            return Response({'success': True, 'message': '通知已接收，正在处理'})

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
            'success': True,
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

        return Response(response_data)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def sync_premium_status(self, request):
        """手动触发同步用户会员状态的任务"""
        try:
            # 异步执行同步任务
            sync_user_premium_status.delay()

            return Response({
                'success': True,
                'message': '同步任务已启动，请稍后查看结果'
            })

        except Exception as e:
            logger.exception(f"启动同步任务时出错: {str(e)}")
            return Response({
                'success': False,
                'message': f'启动同步任务失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def sync_user_status(self, request):
        user_id = request.data.get('user_id')

        if not user_id:
            return Response({
                'success': False,
                'message': '缺少用户ID'
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
                        'success': True,
                        'message': f'用户 {user_id} 的会员状态已更新为有效，到期时间: {latest_subscription.expires_at}'
                    })
                else:
                    return Response({
                        'success': False,
                        'message': f'更新用户 {user_id} 的会员状态失败'
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
                        'success': True,
                        'message': f'用户 {user_id} 的会员状态已更新为无效'
                    })
                else:
                    return Response({
                        'success': False,
                        'message': f'更新用户 {user_id} 的会员状态失败'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.exception(f"同步用户 {user_id} 的会员状态时出错: {str(e)}")
            return Response({
                'success': False,
                'message': f'同步用户状态失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
