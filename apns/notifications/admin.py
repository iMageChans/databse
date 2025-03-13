from django.contrib import admin
from .models import Notifications

@admin.register(Notifications)
class NotificationsAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'timezone', 'notify_time', 'days_remaining', 'is_active', 'last_sent', 'created_at')
    list_filter = ('is_active', 'timezone', 'created_at')
    search_fields = ('user_id',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('基本信息', {
            'fields': ('user_id', 'is_active')
        }),
        ('通知设置', {
            'fields': ('timezone', 'notify_time', 'days_remaining')
        }),
        ('状态信息', {
            'fields': ('last_sent', 'created_at', 'updated_at')
        }),
    )
    actions = ['activate_notifications', 'deactivate_notifications']
    
    def activate_notifications(self, request, queryset):
        """激活选中的通知设置"""
        for notification in queryset:
            # 将该用户的所有通知设置设为非激活状态
            Notifications.objects.filter(user_id=notification.user_id, is_active=True).update(is_active=False)
            # 激活当前通知设置
            notification.is_active = True
            notification.save()
        
        self.message_user(request, f'成功激活 {queryset.count()} 个通知设置')
    activate_notifications.short_description = "激活选中的通知设置"
    
    def deactivate_notifications(self, request, queryset):
        """停用选中的通知设置"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功停用 {updated} 个通知设置')
    deactivate_notifications.short_description = "停用选中的通知设置"
