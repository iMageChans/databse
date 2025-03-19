from django.contrib import admin
from .models import Purchase

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'product_id', 'transaction_id', 'purchase_date',
                    'expires_at', 'is_active', 'is_successful', 'status', 'notification_type')
    list_filter = ('is_active', 'is_successful', 'status', 'notification_type')
    search_fields = ('user_id', 'transaction_id', 'original_transaction_id', 'product_id')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('基本信息', {
            'fields': ('user_id', 'app_id', 'product_id', 'transaction_id', 'original_transaction_id')
        }),
        ('状态信息', {
            'fields': ('status', 'is_active', 'is_successful', 'notification_type')
        }),
        ('时间信息', {
            'fields': ('purchase_date', 'expires_at', 'created_at', 'updated_at')
        }),
        ('详细数据', {
            'fields': ('receipt_data', 'notes'),
            'classes': ('collapse',)
        }),
    )
