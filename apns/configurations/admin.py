from django.contrib import admin
from .models import AppleAppConfiguration, NotificationTemplate


@admin.register(AppleAppConfiguration)
class AppleAppConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'bundle_id', 'team_id', 'is_production', 'is_active', 'created_at')
    list_filter = ('is_production', 'is_active', 'created_at')
    search_fields = ('name', 'bundle_id', 'team_id')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'bundle_id', 'is_active')
        }),
        ('认证信息', {
            'fields': ('team_id', 'key_id', 'auth_key', 'auth_key_file', 'shared_secret')
        }),
        ('环境设置', {
            'fields': ('is_production',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['mark_as_active', 'mark_as_inactive', 'switch_to_production', 'switch_to_development']
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功将 {updated} 个应用配置标记为活跃状态')
    mark_as_active.short_description = "将选中的应用配置标记为活跃"
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功将 {updated} 个应用配置标记为非活跃状态')
    mark_as_inactive.short_description = "将选中的应用配置标记为非活跃"
    
    def switch_to_production(self, request, queryset):
        updated = queryset.update(is_production=True)
        self.message_user(request, f'成功将 {updated} 个应用配置切换到生产环境')
    switch_to_production.short_description = "切换到生产环境"
    
    def switch_to_development(self, request, queryset):
        updated = queryset.update(is_production=False)
        self.message_user(request, f'成功将 {updated} 个应用配置切换到开发环境')
    switch_to_development.short_description = "切换到开发环境"


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'app_config', 'title', 'is_active', 'created_at')
    list_filter = ('is_active', 'app_config', 'created_at')
    search_fields = ('name', 'title', 'body')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('基本信息', {
            'fields': ('app_config', 'name', 'is_active')
        }),
        ('通知内容', {
            'fields': ('title', 'body', 'sound', 'badge')
        }),
        ('高级设置', {
            'fields': ('custom_data',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['mark_as_active', 'mark_as_inactive']
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功将 {updated} 个通知模板标记为活跃状态')
    mark_as_active.short_description = "将选中的通知模板标记为活跃"
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功将 {updated} 个通知模板标记为非活跃状态')
    mark_as_inactive.short_description = "将选中的通知模板标记为非活跃"
