from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Purchase
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Purchase)
def handle_purchase_update(sender, instance, created, **kwargs):
    """
    处理购买记录更新的信号

    Args:
        sender: 发送信号的模型类
        instance: 保存的实例
        created: 是否是新创建的实例
    """
    try:
        # 记录日志
        action = "创建" if created else "更新"
        logger.info(f"{action}购买记录: 用户ID={instance.user_id}, 产品={instance.product_id}, 状态={instance.status}")

        # 如果需要，可以在这里添加其他业务逻辑
        # 例如：发送通知、更新缓存等

    except Exception as e:
        logger.exception(f"处理购买记录更新信号时出错: {str(e)}")