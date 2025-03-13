from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Purchase

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'app_id', 'product_id', 'transaction_id', 
                   'purchase_date', 'expires_at', 'status_badge', 'is_active', 
                   'created_at')
    list_filter = ('is_active', 'is_successful', 'status', 'app_id', 'product_id')
    search_fields = ('user_id', 'transaction_id', 'original_transaction_id')
    readonly_fields = ('created_at', 'updated_at', 'formatted_receipt_data')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('用户信息', {
            'fields': ('user_id', 'app_id')
        }),
        ('交易信息', {
            'fields': ('product_id', 'transaction_id', 'original_transaction_id')
        }),
        ('状态信息', {
            'fields': ('is_active', 'is_successful', 'status', 'purchase_date', 'expires_at')
        }),
        ('收据数据', {
            'fields': ('formatted_receipt_data', 'notes'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def status_badge(self, obj):
        """
        根据状态显示不同颜色的标签
        """
        colors = {
            'pending': 'orange',
            'success': 'green',
            'failed': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 7px; border-radius: 3px;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = '状态'
    
    def formatted_receipt_data(self, obj):
        """
        格式化显示收据数据
        """
        if not obj.receipt_data:
            return '无收据数据'
            
        try:
            # 尝试解析JSON
            receipt_data = obj.receipt_data
            if isinstance(receipt_data, str):
                # 如果是字符串，尝试解析为JSON
                import json
                receipt_json = json.loads(receipt_data)
                formatted = json.dumps(receipt_json, indent=2)
                return format_html('<pre>{}</pre>', formatted)
            return format_html('<pre>{}</pre>', str(receipt_data))
        except Exception as e:
            return format_html('<pre>{}</pre><p style="color: red;">解析错误: {}</p>', 
                              obj.receipt_data, str(e))
    formatted_receipt_data.short_description = '收据数据'
    
    def has_add_permission(self, request):
        """
        禁止手动添加购买记录
        """
        return False
        
    def get_queryset(self, request):
        """
        优化查询性能
        """
        qs = super().get_queryset(request)
        return qs.select_related()
        
    def save_model(self, request, obj, form, change):
        """
        保存模型时记录操作日志
        """
        if change:
            obj.notes = f"{obj.notes}\n管理员修改于 {timezone.now()} by {request.user.username}"
        super().save_model(request, obj, form, change)
