from django.db import models
from django.utils.translation import gettext_lazy as _
import os
from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_p8_file(value):
    """验证上传的文件是否为.p8格式"""
    ext = os.path.splitext(value.name)[1]
    if ext.lower() != '.p8':
        raise ValidationError(_('只允许上传.p8格式的密钥文件'))


class AppleAppConfiguration(models.Model):
    """苹果应用配置模型，用于存储多个苹果应用的配置信息"""
    
    name = models.CharField(_('应用名称'), max_length=100, help_text=_('应用的显示名称'))
    bundle_id = models.CharField(_('Bundle ID'), max_length=255, unique=True, 
                               help_text=_('应用的Bundle ID，例如：com.example.app'))
    team_id = models.CharField(_('Team ID'), max_length=20, 
                             help_text=_('苹果开发者账号的Team ID'))
    key_id = models.CharField(_('Key ID'), max_length=20, 
                            help_text=_('APNs认证密钥的ID'))
    auth_key = models.TextField(_('认证密钥'), 
                              help_text=_('APNs认证密钥内容（.p8文件内容）'))
    auth_key_file = models.FileField(_('认证密钥文件'), upload_to='apple_keys/', 
                                   validators=[validate_p8_file], 
                                   null=True, blank=True,
                                   help_text=_('上传.p8格式的认证密钥文件'))
    
    is_production = models.BooleanField(_('生产环境'), default=True, 
                                      help_text=_('是否为生产环境，否则为开发环境'))
    shared_secret = models.CharField(_('shared_secret'), max_length=255,
                            help_text=_('内购密码'), default='')
    is_active = models.BooleanField(_('是否启用'), default=True)
    
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    
    class Meta:
        verbose_name = _('苹果应用配置')
        verbose_name_plural = _('苹果应用配置')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.bundle_id})"
    
    def save(self, *args, **kwargs):
        """保存前处理上传的密钥文件"""
        if self.auth_key_file and not self.auth_key:
            # 如果上传了文件但没有设置密钥内容，则从文件中读取
            self.auth_key = self.auth_key_file.read().decode('utf-8')
        super().save(*args, **kwargs)
    
    def get_apns_host(self):
        """根据环境返回APNs服务器地址"""
        if self.is_production:
            return "api.push.apple.com"
        return "api.sandbox.push.apple.com"


class NotificationTemplate(models.Model):
    """通知模板，用于存储预定义的通知内容"""
    
    app_config = models.ForeignKey(AppleAppConfiguration, on_delete=models.CASCADE, 
                                  related_name='templates',
                                  verbose_name=_('应用配置'))
    name = models.CharField(_('模板名称'), max_length=100)
    title = models.CharField(_('通知标题'), max_length=255)
    body = models.TextField(_('通知内容'))
    sound = models.CharField(_('声音'), max_length=50, default='default')
    badge = models.IntegerField(_('角标数'), default=1)
    
    custom_data = models.JSONField(_('自定义数据'), default=dict, blank=True,
                                 help_text=_('JSON格式的自定义数据'))
    
    is_active = models.BooleanField(_('是否启用'), default=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    
    class Meta:
        verbose_name = _('通知模板')
        verbose_name_plural = _('通知模板')
        ordering = ['-created_at']
        unique_together = ('app_config', 'name')
    
    def __str__(self):
        return f"{self.app_config.name} - {self.name}"
