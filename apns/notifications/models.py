from django.db import models
from django.utils.translation import gettext_lazy as _

class Notifications(models.Model):
    user_id = models.IntegerField(_('用户ID'), db_index=True, help_text=_('UserCenter的用户ID'))
    timezone = models.CharField('时区', max_length=50, default='Asia/Shanghai')
    notify_time = models.CharField('通知时间', max_length=5)  # HH:mm 格式
    days_remaining = models.IntegerField('剩余天数', default=21)
    is_active = models.BooleanField('是否启用', default=True)
    last_sent = models.DateTimeField('上次发送时间', null=True, blank=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        verbose_name = '定时通知设置'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def decrease_days(self):
        self.days_remaining -= 1
        if self.days_remaining <= 0:
            self.is_active = False
        self.save()
