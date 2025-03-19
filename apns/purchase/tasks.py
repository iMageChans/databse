from celery import shared_task
import logging
from django.utils import timezone
from purchase.models import Purchase
from purchase.services import UserService

logger = logging.getLogger(__name__)


@shared_task
def sync_user_premium_status():
    """定期同步用户的会员状态"""
    try:
        logger.info("开始同步用户会员状态")

        # 获取所有用户ID（去重）
        user_ids = Purchase.objects.values_list('user_id', flat=True).distinct()

        for user_id in user_ids:
            try:
                # 获取用户的有效订阅
                active_subscriptions = Purchase.objects.filter(
                    user_id=user_id,
                    is_active=True,
                    is_successful=True,
                    expires_at__gt=timezone.now()
                ).order_by('-expires_at')

                if active_subscriptions.exists():
                    # 用户有有效订阅，使用最晚的到期时间
                    latest_subscription = active_subscriptions.first()
                    app_id = latest_subscription.app_id

                    UserService.update_premium_status(
                        user_id=user_id,
                        is_premium=True,
                        app_id=app_id,
                        expires_at=latest_subscription.expires_at
                    )

                    logger.info(f"同步用户 {user_id} 的会员状态: 有效，到期时间={latest_subscription.expires_at}")
                else:
                    # 用户没有有效订阅
                    # 获取用户最后一条记录的app_id
                    last_purchase = Purchase.objects.filter(user_id=user_id).order_by('-updated_at').first()
                    app_id = last_purchase.app_id if last_purchase else None

                    UserService.update_premium_status(
                        user_id=user_id,
                        is_premium=False,
                        app_id=app_id
                    )

                    logger.info(f"同步用户 {user_id} 的会员状态: 无效")

            except Exception as e:
                logger.exception(f"同步用户 {user_id} 的会员状态时出错: {str(e)}")

        logger.info("用户会员状态同步完成")

        return True

    except Exception as e:
        logger.exception(f"同步用户会员状态任务出错: {str(e)}")
        return False