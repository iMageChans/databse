from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Purchase(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    NOTIFY_CHOICES = [
        ('INITIAL_BUY', '用户首次订阅'),
        ('DID_CHANGE_RENEWAL_STATUS', '订阅状态更改'),
        ('INTERACTIVE_RENEWAL', '通过互动方式续订订阅'),
        ('DID_CHANGE_RENEWAL_PREF', "订阅计划更改"),
        ('CONSUMPTION_REQUEST', '发起退款'),
        ('CANCEL', '退订'),
        ('DID_FAIL_TO_RENEW', '账单问题而未能续订的订阅'),
        ('DID_RECOVER', '指示之前未能续订的已过期订阅成功自动续订'),
        ('DID_RENEW', '客户的订阅已成功自动续订至新的交易周期'),
        ('PRICE_INCREASE_CONSENT', '用户同意自动续订的价格调整，继续续订'),
        ('REFUND', '已成功退还了应用内购买的消耗品、非消耗品或非续订订阅的交易'),
        ('REVOKE', '用户通过家庭共享获得的内购项目不再通过共享可用')
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

    notification_type = models.CharField('订单通知类型', max_length=255, blank=True, null=True, choices=STATUS_CHOICES)
    
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