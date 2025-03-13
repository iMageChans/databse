from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Purchase(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    user_id = models.IntegerField('用户ID', db_index=True, help_text='UserCenter的用户ID')
    app_id = models.CharField("具体苹果的应用", max_length=255, blank=True, null=True)
    product_id = models.CharField(max_length=255, blank=True, null=True)
    transaction_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    original_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    receipt_data = models.TextField(blank=True, null=True)
    purchase_date = models.DateTimeField()
    expires_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_successful = models.BooleanField(default=False)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    
    # 添加状态字段，便于跟踪订单状态
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # 添加备注字段，记录处理过程中的问题
    notes = models.TextField(blank=True, null=True, help_text='处理过程中的备注信息')

    class Meta:
        verbose_name = '苹果内购'
        verbose_name_plural = '苹果内购'
        ordering = ['-created_at']
        # 添加索引以提高查询性能
        indexes = [
            models.Index(fields=['user_id', 'is_active']),
            models.Index(fields=['original_transaction_id']),
        ]

    def __str__(self):
        return f"用户ID:{self.user_id} - {self.product_id} - {'成功' if self.is_successful else '处理中'}"