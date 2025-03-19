import logging
from django.conf import settings
import requests
import datetime
from configurations.models import AppleAppConfiguration

logger = logging.getLogger(__name__)


class PurchaseService:
    """购买服务类，处理与购买相关的业务逻辑"""

    @staticmethod
    def verify_and_process_receipt(receipt_data, user_id, sandbox=False, app_id='pocket_ai'):
        """
        验证并处理苹果收据

        Args:
            receipt_data: 苹果收据数据
            user_id: 用户ID
            sandbox: 是否使用沙盒环境
            app_id: 应用ID

        Returns:
            tuple: (成功标志, 结果或错误信息)
        """
        try:
            # 避免循环导入
            from purchase.models import Purchase

            # 验证收据
            verification_result = Purchase.verify_receipt(receipt_data, sandbox, app_id)

            if verification_result.get('status') != 0:
                error_message = f"收据验证失败，状态码: {verification_result.get('status')}"
                logger.error(error_message)
                return False, error_message

            # 处理验证结果
            purchase = Purchase.process_verification_result(verification_result, user_id)

            if not purchase:
                error_message = "处理购买记录失败"
                logger.error(error_message)
                return False, error_message

            # 更新用户权限
            Purchase.update_user_privileges(user_id, purchase)

            return True, purchase

        except Exception as e:
            logger.exception(f"验证并处理收据时出错: {str(e)}")
            return False, str(e)

    @staticmethod
    def get_active_purchases(user_id):
        """
        获取用户的有效购买记录

        Args:
            user_id: 用户ID

        Returns:
            QuerySet: 有效的购买记录
        """
        from django.utils import timezone
        from purchase.models import Purchase

        return Purchase.objects.filter(
            user_id=user_id,
            is_active=True,
            is_successful=True,
            expires_at__gt=timezone.now()
        )

    @staticmethod
    def has_active_subscription(user_id, product_id=None):
        """
        检查用户是否有有效的订阅

        Args:
            user_id: 用户ID
            product_id: 产品ID，可选

        Returns:
            tuple: (是否有有效订阅, 到期时间)
        """
        from django.utils import timezone
        from purchase.models import Purchase

        query = {
            'user_id': user_id,
            'is_active': True,
            'is_successful': True,
            'expires_at__gt': timezone.now()
        }

        if product_id:
            query['product_id'] = product_id

        # 获取最晚到期的订阅
        latest_subscription = Purchase.objects.filter(**query).order_by('-expires_at').first()

        if latest_subscription:
            return True, latest_subscription.expires_at

        return False, None


class UserService:
    """用户服务类，处理与用户中心的通信"""

    @staticmethod
    def update_premium_status(user_id, is_premium, app_id='pocket_ai', expires_at=None):
        """
        更新用户的会员状态

        Args:
            user_id: 用户ID
            is_premium: 是否是会员
            app_id: 应用ID
            expires_at: 会员到期时间，可以是datetime对象或ISO格式的字符串

        Returns:
            bool: 更新是否成功
        """
        try:
            # 构建请求URL
            api_url = f"{settings.BASE_URL}/users/api/users/{user_id}/update_premium_status/"

            # 构建请求数据
            data = {
                "user_id": user_id,
                "is_premium": is_premium
            }

            if expires_at:
                data["expires_at"] = expires_at

            logger.error(f"data: {data}")

            # 获取API密钥
            headers = {}
            if app_id:
                try:
                    config = AppleAppConfiguration.objects.get(name=app_id)
                    if hasattr(config, 'admin_token'):
                        headers['Authorization'] = f"{config.admin_token}"
                except AppleAppConfiguration.DoesNotExist:
                    logger.error(f"找不到应用 {app_id} 的配置")

            # 发送请求
            response = requests.post(
                api_url,
                json=data,
                headers=headers,
                timeout=10  # 设置超时时间
            )

            # 检查响应
            response.raise_for_status()  # 如果状态码不是200，抛出异常

            result = response.json()

            if result.get('success'):
                logger.info(f"成功更新用户 {user_id} 的会员状态: is_premium={is_premium}, expires_at={expires_at}")
                return True
            else:
                logger.error(f"更新用户 {user_id} 的会员状态失败: {result.get('message')}")
                return False

        except requests.RequestException as e:
            logger.exception(f"请求用户中心API时出错: {str(e)}")
            return False
        except Exception as e:
            logger.exception(f"更新用户会员状态时出错: {str(e)}")
            return False
