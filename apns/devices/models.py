from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class DeviceToken(models.Model):
    user_id = models.IntegerField(_('用户ID'), db_index=True, help_text=_('UserCenter的用户ID'))
    device_id = models.CharField(max_length=255)  # 设备ID，客户端传来
    device_token = models.CharField(max_length=255)  # APNs设备Token
    send_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)  # 标记该Token是否有效
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    def __str__(self):
        return f"{self.user_id}: {self.device_id} - {self.device_token}"

    class Meta:
        verbose_name = '设备管理'
        verbose_name_plural = '设备管理'
        ordering = ['-created_at']

    def mark_inactive(self):
        self.is_active = False
        self.updated_at = timezone.now()
        self.save()
