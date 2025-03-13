# iap_app/views.py
import os
import json
import logging
import requests
from rest_framework import permissions, status
from rest_framework.response import Response
from django.utils import timezone

from utils.permissions import IsAuthenticatedExternal
from utils.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from .models import Purchase
from .serializers import PurchaseVerificationSerializer, PurchaseSerializer, PurchaseStatusSerializer
from .services import AppleIAPService

logger = logging.getLogger(__name__)


class PurchaseVerificationView(CreateModelMixin, GenericViewSet):
    """
    接收iOS应用发送的购买凭证，验证并处理
    """
    permission_classes = [IsAuthenticatedExternal]
    serializer_class = PurchaseVerificationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        receipt_data = serializer.validated_data['receipt_data']
        user_id = serializer.validated_data['user_id']
        app_id = serializer.validated_data['app_id']
        product_id = serializer.validated_data['product_id']
        transaction_id = serializer.validated_data['transaction_id']
        original_transaction_id = serializer.validated_data.get('original_transaction_id', transaction_id)

        try:
            # 检查是否已处理过该交易
            existing_purchase = Purchase.objects.filter(transaction_id=transaction_id).first()
            if existing_purchase and existing_purchase.is_successful:
                logger.info(f"Transaction {transaction_id} already processed successfully.")
                return Response({
                    'code': 200,
                    'msg': 'success',
                    'data': PurchaseSerializer(existing_purchase).data
                })

            # 创建或获取购买记录
            purchase = Purchase.objects.filter(transaction_id=transaction_id).first()
            if not purchase:
                purchase = Purchase.objects.create(
                    user_id=user_id,
                    app_id=app_id,
                    product_id=product_id,
                    transaction_id=transaction_id,
                    original_transaction_id=original_transaction_id,
                    receipt_data=receipt_data,
                    purchase_date=timezone.now(),
                    is_active=False,
                    is_successful=False,
                    status='pending'
                )

            # 验证收据
            verification_result = AppleIAPService.verify_receipt(receipt_data, app_id)
            res_status = verification_result.get('status')

            if res_status == 0:
                # 设置过期时间
                if product_id == "Weekly_Subscription":
                    duration_type = "week"
                    expires_at = timezone.now() + timezone.timedelta(days=7)
                elif product_id == "Monthly_Subscription":
                    duration_type = "month"
                    expires_at = timezone.now() + timezone.timedelta(days=30)
                elif product_id == "Yearly_Subscription":
                    duration_type = "year"
                    expires_at = timezone.now() + timezone.timedelta(days=365)
                else:
                    return Response({
                        'code': 400,
                        'msg': f'未知的订阅类型: {product_id}',
                    }, status=status.HTTP_400_BAD_REQUEST)

                purchase.expires_at = expires_at
                purchase.is_active = True
                purchase.save()

                # 调用用户服务更新会员状态
                token = os.environ.get("ADMIN_TOKEN")
                if not token:
                    logger.error("Missing ADMIN_TOKEN environment variable")
                    return Response({
                        'code': 500,
                        'msg': 'Server configuration error',
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                param = {
                    "is_premium": True,
                    "duration_type": duration_type
                }

                try:
                    rsp = requests.post(
                        url=f"https://users.pulseheath.com/users/api/users/{user_id}/update_premium_status/",
                        json=param,  # 使用json参数而不是data
                        headers={
                            'Content-Type': 'application/json',
                            'Authorization': token,
                        },
                        timeout=30  # 添加超时
                    )

                    if rsp.status_code == 200:
                        purchase.is_successful = True
                        purchase.status = 'success'
                        purchase.save()
                        return Response({
                            'code': 200,
                            'msg': 'success',
                            'data': PurchaseSerializer(purchase).data
                        })
                    else:
                        logger.error(f"Failed to update user premium status: {rsp.status_code} - {rsp.text}")
                        purchase.notes = f"用户服务调用失败: {rsp.status_code} - {rsp.text}"
                        purchase.status = 'failed'
                        purchase.save()
                        return Response({
                            'code': 400,
                            'msg': f'Failed to update user premium status: {rsp.status_code}',
                        }, status=status.HTTP_400_BAD_REQUEST)
                except requests.RequestException as e:
                    logger.error(f"Network error when calling user service: {str(e)}")
                    purchase.notes = f"用户服务网络错误: {str(e)}"
                    purchase.status = 'failed'
                    purchase.save()
                    return Response({
                        'code': 500,
                        'msg': f'Network error: {str(e)}',
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                # 验证失败
                purchase.is_successful = False
                purchase.status = 'failed'
                purchase.notes = f"验证失败，状态码: {res_status}"
                purchase.save()
                return Response({
                    'code': 400,
                    'msg': f'Receipt verification failed with status {res_status}',
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f"Error processing purchase: {str(e)}")
            return Response({
                'code': 500,
                'msg': f'Server error: {str(e)}',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AppleWebhookView(CreateModelMixin, GenericViewSet):
    """
    处理来自Apple的服务器通知
    """
    permission_classes = [permissions.AllowAny]  # Apple服务器通知无需认证

    def create(self, request, *args, **kwargs):
        try:
            # 获取请求数据
            request_data = request.data
            if isinstance(request_data, str):
                try:
                    request_data = json.loads(request_data)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in webhook request")
                    return Response({"status": "error", "message": "Invalid JSON"}, 
                                   status=status.HTTP_400_BAD_REQUEST)
            
            # 记录原始通知
            logger.info(f"Received Apple webhook: {json.dumps(request_data)}")
            
            # 获取通知类型和应用ID
            notification_type = request_data.get('notification_type')
            app_id = request_data.get('app_id')
            
            if not notification_type or not app_id:
                logger.error("Missing notification_type or app_id in webhook")
                return Response({"status": "error", "message": "Missing required fields"}, 
                               status=status.HTTP_400_BAD_REQUEST)
            
            # 处理通知
            AppleIAPService.process_receipt_from_notification(request_data, app_id)
            
            return Response({"status": "success"}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Webhook processing failed: {str(e)}")
            # 即使处理失败，也返回200状态码，避免Apple重复发送通知
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_200_OK)


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
        queryset = Purchase.objects.all()
        
        # 按用户ID过滤
        user_id = self.request.GET.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
            
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

    def get_user_status(self, request, user_id=None):
        """
        获取用户的订阅状态
        """
        if not user_id:
            return Response({
                'code': 400,
                'msg': '缺少用户ID',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 查找用户最新的有效订阅
        active_purchase = Purchase.objects.filter(
            user_id=user_id,
            is_active=True,
            is_successful=True,
            expires_at__gt=timezone.now()
        ).order_by('-expires_at').first()
        
        if not active_purchase:
            return Response({
                'code': 200,
                'msg': 'success',
                'data': {
                    'has_active_subscription': False,
                    'subscription_info': None
                }
            })
        
        # 使用状态序列化器
        serializer = PurchaseStatusSerializer(active_purchase)
        
        return Response({
            'code': 200,
            'msg': 'success',
            'data': {
                'has_active_subscription': True,
                'subscription_info': serializer.data
            }
        })
