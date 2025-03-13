import pytz
from datetime import datetime
from django.utils import timezone
from .models import Notifications
from configurations.services import AppleNotificationService
from devices.models import DeviceToken


class NotificationScheduleService:
    """通知调度服务"""
    
    @staticmethod
    def should_send_notification(notification):
        """检查是否应该发送通知"""
        if not notification.is_active or notification.days_remaining <= 0:
            return False
        
        # 获取用户时区的当前时间
        user_tz = pytz.timezone(notification.timezone)
        now = timezone.now().astimezone(user_tz)
        
        # 解析通知时间
        hour, minute = map(int, notification.notify_time.split(':'))
        
        # 检查是否是通知时间
        if now.hour == hour and now.minute == minute:
            # 检查今天是否已经发送过
            if notification.last_sent:
                last_sent = notification.last_sent.astimezone(user_tz)
                if last_sent.date() == now.date():
                    return False
            return True
        
        return False
    
    @staticmethod
    def send_scheduled_notifications():
        """发送所有应该发送的通知"""
        active_notifications = Notifications.objects.filter(is_active=True, days_remaining__gt=0)
        sent_count = 0
        
        for notification in active_notifications:
            if NotificationScheduleService.should_send_notification(notification):
                # 获取用户的设备令牌
                devices = DeviceToken.objects.filter(user_id=notification.user_id, is_active=True)
                
                if devices.exists():
                    # 获取第一个应用配置
                    try:
                        apple_service = AppleNotificationService(app_config_id=1)  # 使用默认应用配置
                        
                        # 发送通知
                        result = apple_service.send_notification_to_user(
                            user_id=notification.user_id,
                            title="每日提醒",
                            body=f"您还有 {notification.days_remaining} 天的会员时间",
                            badge=1,
                            sound="default",
                            custom_data={"type": "daily_reminder"}
                        )
                        
                        # 更新最后发送时间
                        notification.last_sent = timezone.now()
                        notification.save()
                        
                        sent_count += 1
                    except Exception as e:
                        print(f"发送通知失败: {str(e)}")
        
        return sent_count 