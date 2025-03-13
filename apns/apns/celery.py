# Boom/celery.py
from __future__ import absolute_import, unicode_literals

import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab

# 设置默认Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apns.settings')

app = Celery('apns')

# 使用字符串，这样worker不用序列化配置对象
app.config_from_object('django.conf:settings', namespace='CELERY')

# 设置 Celery 时区；若 settings.py 里 TIME_ZONE 已设为 UTC 或其它，也可直接使用
app.conf.timezone = settings.TIME_ZONE
app.conf.enable_utc = True

# 从所有已注册的app中加载任务模块
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'check-scheduled-notifications': {
        'task': 'notifications.tasks.send_scheduled_notifications',
        'schedule': crontab(minute='*'),  # 每分钟检查一次
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
