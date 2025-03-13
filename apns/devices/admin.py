from django.contrib import admin
from .models import DeviceToken

@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'device_id', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('user_id', 'device_id', 'device_token')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['mark_as_inactive', 'mark_as_active']
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功将 {updated} 个设备标记为非活跃状态')
    mark_as_inactive.short_description = "将选中的设备标记为非活跃"
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功将 {updated} 个设备标记为活跃状态')
    mark_as_active.short_description = "将选中的设备标记为活跃"
