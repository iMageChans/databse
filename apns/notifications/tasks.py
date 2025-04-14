from celery import shared_task
from django.utils import timezone
import pytz
from .models import Notifications
from devices.models import DeviceToken
from .service.apple import AppleService
from .services import NotificationScheduleService


# 定义每周的通知内容
WEEKLY_NOTIFICATIONS = {
    0: {  # 周一
        "title": "Money Flows, Joy Grows! ✨",
        "body": "Feel good about today's progress—log it in and savor the journey."
    },
    1: {  # 周二
        "title": "Consistency Is Key! 🔑",
        "body": "Small wins make big impacts. Log today and let success unfold!"
    },
    2: {  # 周三
        "title": "Dream Fund Fuel! 🌈",
        "body": "Closer to your happy place! Log today and keep your dreams alive."
    },
    3: {  # 周四
        "title": "One Step Closer! 🚀",
        "body": "Joy is in the journey! Track today and feel your dreams within reach."
    },
    4: {  # 周五
        "title": "Happiness Fund Alert! 😊",
        "body": "Dreams come true one entry at a time. Add to your Dream Fund today!"
    },
    5: {  # 周六
        "title": "Your Daily Power Move! 💪",
        "body": "Today's choices, tomorrow's dreams. Log in and stay inspired!"
    },
    6: {  # 周日
        "title": "Goals in Sight! 👀​",
        "body": "You're closer than you think. Record today's progress and stay on track!"
    }
}


# @shared_task
# def send_scheduled_notifications():
#     """发送定时通知"""
#     print(f"[{timezone.now()}] 开始检查定时通知...")
#     count = NotificationScheduleService.send_scheduled_notifications()
#     print(f"[{timezone.now()}] 发送了 {count} 条通知")
#     return count


@shared_task
def send_scheduled_notifications():
    """发送定时通知"""
    apple_service = AppleService(app_id="pocket_ai")
    utc_now = timezone.now()

    # 获取所有活跃的通知计划
    schedules = Notifications.objects.filter(
        is_active=True,
        days_remaining__gt=0  # 确保还有剩余天数
    )

    for schedule in schedules:
        try:
            # 转换到用户时区
            user_tz = pytz.timezone(schedule.timezone)
            user_time = utc_now.astimezone(user_tz)
            
            # 解析计划时间
            schedule_hour, schedule_minute = map(int, schedule.notify_time.split(':'))
            
            # 创建用户时区的目标时间
            target_time = user_time.replace(
                hour=schedule_hour,
                minute=schedule_minute,
                second=0,
                microsecond=0
            )
            
            # 计算时间差（分钟）
            time_diff = abs((user_time - target_time).total_seconds() / 60)
            
            # 如果在5分钟误差范围内且今天还未发送
            if time_diff <= 5 and (
                not schedule.last_sent or 
                schedule.last_sent.astimezone(user_tz).date() < user_time.date()
            ):
                # 获取当前是周几（0-6，0是周一）
                weekday = user_time.weekday()
                notification = WEEKLY_NOTIFICATIONS[weekday]
                
                # 获取用户的所有活跃设备
                devices = DeviceToken.objects.filter(
                    user_id=schedule.user_id,
                    is_active=True
                )

                # 计算进度信息
                days_passed = 21 - schedule.days_remaining + 1
                progress_message = f"第 {days_passed} 天 / 共 21 天"

                # 发送通知
                for device in devices:
                    success = apple_service.send_push_notification(
                        device_token=device.device_token,
                        title=notification['title'],
                        body=notification['body']
                    )

                    if not success:
                        device.mark_inactive()

                # 更新通知计划
                schedule.last_sent = utc_now
                schedule.decrease_days()
                
                if schedule.days_remaining <= 0:
                    schedule.is_active = False
                    print(f"用户 {schedule.user_id} 已完成21天计划")
                
                schedule.save()
                
        except Exception as e:
            print(f"处理用户 {schedule.user_id} 的通知计划时出错: {str(e)}")
            continue