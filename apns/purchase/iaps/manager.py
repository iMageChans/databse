

import requests
from django.utils import timezone

from configurations.models import AppleAppConfiguration
from django.conf import settings
import logging
import json

from purchase.models import Purchase

logger = logging.getLogger(__name__)


class AppleIAPManager:

    @staticmethod
    def verify_receipt(receipt_data, app_id):
        try:
            app_config = AppleAppConfiguration.objects.get(name=app_id)
            shared_secret = app_config.shared_secret

            payload = {
                'receipt-data': receipt_data,
                'password': shared_secret,  # 使用配置中的共享密钥
                'exclude-old-transactions': True
            }

            response = requests.post('https://buy.itunes.apple.com/verifyReceipt', json=payload, timeout=30)
            result = response.json()

            if result.get('status') == 21007:
                response = requests.post('https://sandbox.itunes.apple.com/verifyReceipt', json=payload, timeout=30)
                result = response.json()

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
                return False

            purchase = Purchase.objects.filter(original_transaction_id=receipt_data['original_transaction_id']).first()
            if not purchase:
                purchase = Purchase.objects.create(
                    user_id=receipt_data['user_id'],
                    app_id=app_id,
                    product_id=receipt_data['product_id'],
                    transaction_id=receipt_data['transaction_id'],
                    original_transaction_id=receipt_data['original_transaction_id'],
                    receipt_data=receipt_data,
                    purchase_date=timezone.now(),
                    is_active=False,
                    is_successful=False,
                    status='pending'
                )

            token = app_config.admin_token
            if not token:
                logger.error("Missing ADMIN_TOKEN environment variable")

            param = {
                "is_premium": True,
            }

            try:
                rsp = requests.post(
                        url=f"{settings.BASE_URL}/users/api/users/{receipt_data['user_id']}/update_premium_status/",
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


            return True
        except AppleAppConfiguration.DoesNotExist:
            raise ValueError(f"找不到应用配置: {app_id}")
        except requests.RequestException as e:
            raise ValueError(f"验证收据时网络错误: {str(e)}")
        except Exception as e:
            raise ValueError(f"验证收据时发生错误: {str(e)}")