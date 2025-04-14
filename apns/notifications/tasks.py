from celery import shared_task
from django.utils import timezone
import pytz
from .models import Notifications
from devices.models import DeviceToken
from .service.apple import AppleService
from .services import NotificationScheduleService


# 定义每周的通知内容
# WEEKLY_NOTIFICATIONS = {
#     0: {  # 周一
#         "title": "财源滚滚，欢乐连连！✨",
#         "body": "为今天的进步感到开心——立即记录，享受旅程"
#     },
#     1: {  # 周二
#         "title": "坚持是关键！🔑",
#         "body": "小胜利带来大影响，记录今天让成功自然展开！"
#     },
#     2: {  # 周三
#         "title": "梦想基金加油！🌈",
#         "body": "离你的快乐天地更近了！立即记录，让梦想保持鲜活"
#     },
#     3: {  # 周四
#         "title": "更近一步！🚀",
#         "body": "快乐就在旅程中！记录今天，感受梦想触手可及"
#     },
#     4: {  # 周五
#         "title": "幸福基金提醒！😊",
#         "body": "梦想通过每次记录成真，今天也为梦想基金添砖加瓦吧！"
#     },
#     5: {  # 周六
#         "title": "每日能量行动！💪",
#         "body": "今日选择成就明日梦想，立即记录保持动力！"
#     },
#     6: {  # 周日
#         "title": "目标近在眼前！👀​",
#         "body": "你比想象的更接近目标，记录今日进展保持正轨！"
#     }
# }


WEEKLY_NOTIFICATIONS = {
    0: {  # 周一
        "title": "新的一周，钱包还行吗？💰",
        "body": "这周打算怎么安排？快来记一笔，给钱包立个 flag！"
    },
    1: {  # 周二
        "title": "你不会真把我忘了吧？👀",
        "body": "看看账本，回忆一下钱都去哪儿了——买快乐，还是存梦想？"
    },
    2: {  # 周三
        "title": "小富婆/小财主，看看战绩吧！✨",
        "body": "梦想基金进展不错哦~点开看看，离目标又近了一步！"
    },
    3: {  # 周四
        "title": "你猜这周花了多少？😏",
        "body": "我不说，你自己心里也有数。敢不敢打开账本看看？"
    },
    4: {  # 周五
        "title": "周五了，预算还能撑住吗？🍻",
        "body": "周末来了，要放肆还是要克制？先来看看钱包怎么说！"
    },
    5: {  # 周六
        "title": "我刚看了你的账本…🤭",
        "body": "嗯……大佬风范，还是豪气冲天？快来看看你这周的操作！"
    },
    6: {  # 周日
        "title": "一周结束了，给你算了笔账！📊",
        "body": "今天存一点，未来多一点！看看这周的成果，给下周定个小目标吧！"
    }
}

# @shared_task
# def send_scheduled_notifications():
#     """发送定时通知"""
#     print(f"[{timezone.now()}] 开始检查定时通知...")
#     count = NotificationScheduleService.should_send_notification()
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