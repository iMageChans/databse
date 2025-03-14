from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.forms import ModelForm, PasswordInput
from .models import AppleAppConfiguration, NotificationTemplate


class AppleAppConfigurationForm(ModelForm):
    """自定义表单，为敏感字段提供更好的输入控件"""

    class Meta:
        model = AppleAppConfiguration
        fields = '__all__'
        widgets = {
            'shared_secret': PasswordInput(attrs={'autocomplete': 'new-password'}),
        }


@admin.register(AppleAppConfiguration)
class AppleAppConfigurationAdmin(admin.ModelAdmin):
    form = AppleAppConfigurationForm
    list_display = ('name', 'bundle_id', 'team_id', 'is_production', 'is_active', 'environment_badge', 'created_at')
    list_filter = ('is_production', 'is_active', 'created_at')
    search_fields = ('name', 'bundle_id', 'team_id', 'key_id')
    readonly_fields = ('created_at', 'updated_at', 'formatted_auth_key', 'apns_host', 'masked_shared_secret', 'masked_admin_token')
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'bundle_id', 'is_active')
        }),
        ('认证信息', {
            'fields': ('team_id', 'key_id', 'auth_key', 'auth_key_file')
        }),
        ('内购设置', {
            'fields': ('shared_secret', 'masked_shared_secret'),
            'description': '内购共享密钥用于验证收据。输入新密钥后，原密钥将被替换。'
        }),
        ('管理员Token', {
            'fields': ('admin_token', 'masked_admin_token'),
            'description': '管理员Token。'
        }),
        ('环境设置', {
            'fields': ('is_production', 'apns_host')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['mark_as_active', 'mark_as_inactive', 'switch_to_production', 'switch_to_development']

    def environment_badge(self, obj):
        """
        显示环境标签
        """
        if obj.is_production:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 7px; '
                'border-radius: 3px; font-weight: bold;">生产环境</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #17a2b8; color: white; padding: 3px 7px; '
                'border-radius: 3px; font-weight: bold;">开发环境</span>'
            )

    environment_badge.short_description = '环境'

    def masked_admin_token(self, obj):
        """
        显示掩码后的共享密钥
        """
        if not obj.admin_token:
            return '未设置共享密钥'

        # 只显示前4位和后4位，中间用星号代替
        secret_len = len(obj.admin_token)
        if secret_len <= 8:
            masked = '*' * secret_len
        else:
            masked = obj.admin_token[:4] + '*' * (secret_len - 8) + obj.admin_token[-4:]

        return format_html('<code style="font-size: 1.1em;">{}</code>', masked)

    masked_admin_token.short_description = 'AdminToken(掩码显示)'

    def masked_shared_secret(self, obj):
        """
        显示掩码后的共享密钥
        """
        if not obj.shared_secret:
            return '未设置共享密钥'

        # 只显示前4位和后4位，中间用星号代替
        secret_len = len(obj.shared_secret)
        if secret_len <= 8:
            masked = '*' * secret_len
        else:
            masked = obj.shared_secret[:4] + '*' * (secret_len - 8) + obj.shared_secret[-4:]

        return format_html('<code style="font-size: 1.1em;">{}</code>', masked)

    masked_shared_secret.short_description = '当前共享密钥(掩码显示)'

    def formatted_auth_key(self, obj):
        """
        格式化显示认证密钥
        """
        if not obj.auth_key:
            return '未设置认证密钥'

        # 只显示密钥的前后部分，中间部分用省略号代替
        key_parts = obj.auth_key.split('\n')
        if len(key_parts) > 4:
            formatted_key = '\n'.join(key_parts[:2]) + '\n...\n' + '\n'.join(key_parts[-2:])
        else:
            formatted_key = obj.auth_key

        return format_html('<pre style="max-height: 200px; overflow-y: auto;">{}</pre>', formatted_key)

    formatted_auth_key.short_description = '认证密钥预览'

    def apns_host(self, obj):
        """
        显示APNs服务器地址
        """
        host = obj.get_apns_host()
        if obj.is_production:
            return format_html('<span style="color: #28a745;">{}</span>', host)
        else:
            return format_html('<span style="color: #17a2b8;">{}</span>', host)

    apns_host.short_description = 'APNs服务器'

    def mark_as_active(self, request, queryset):
        """
        批量激活应用配置
        """
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功将 {updated} 个应用配置标记为活跃状态')

    mark_as_active.short_description = "将选中的应用配置标记为活跃"

    def mark_as_inactive(self, request, queryset):
        """
        批量停用应用配置
        """
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功将 {updated} 个应用配置标记为非活跃状态')

    mark_as_inactive.short_description = "将选中的应用配置标记为非活跃"

    def switch_to_production(self, request, queryset):
        """
        批量切换到生产环境
        """
        updated = queryset.update(is_production=True)
        self.message_user(request, f'成功将 {updated} 个应用配置切换到生产环境')

    switch_to_production.short_description = "切换到生产环境"

    def switch_to_development(self, request, queryset):
        """
        批量切换到开发环境
        """
        updated = queryset.update(is_production=False)
        self.message_user(request, f'成功将 {updated} 个应用配置切换到开发环境')

    switch_to_development.short_description = "切换到开发环境"

    def save_model(self, request, obj, form, change):
        """
        保存模型前处理上传的密钥文件
        """
        if obj.auth_key_file and not obj.auth_key:
            # 如果上传了文件但没有设置密钥内容，则从文件中读取
            try:
                obj.auth_key = obj.auth_key_file.read().decode('utf-8')
            except Exception as e:
                self.message_user(request, f"读取密钥文件失败: {str(e)}", level='ERROR')

        # 如果提交了空的shared_secret，保留原值
        if change and not obj.shared_secret and 'shared_secret' in form.changed_data:
            original_obj = AppleAppConfiguration.objects.get(pk=obj.pk)
            obj.shared_secret = original_obj.shared_secret
            self.message_user(request, "共享密钥未更改，保留原值", level='INFO')

        super().save_model(request, obj, form, change)

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'app_config', 'title', 'is_active', 'created_at')
    list_filter = ('is_active', 'app_config', 'created_at')
    search_fields = ('name', 'title', 'body')
    readonly_fields = ('created_at', 'updated_at', 'formatted_custom_data')
    fieldsets = (
        ('基本信息', {
            'fields': ('app_config', 'name', 'is_active')
        }),
        ('通知内容', {
            'fields': ('title', 'body', 'sound', 'badge')
        }),
        ('高级设置', {
            'fields': ('custom_data', 'formatted_custom_data'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['mark_as_active', 'mark_as_inactive']

    def formatted_custom_data(self, obj):
        """
        格式化显示自定义数据
        """
        if not obj.custom_data:
            return '无自定义数据'

        import json
        try:
            formatted = json.dumps(obj.custom_data, indent=2, ensure_ascii=False)
            return format_html('<pre style="max-height: 200px; overflow-y: auto;">{}</pre>', formatted)
        except Exception as e:
            return format_html('<p style="color: #dc3545;">格式化失败: {}</p>', str(e))

    formatted_custom_data.short_description = '格式化自定义数据'

    def mark_as_active(self, request, queryset):
        """
        批量激活通知模板
        """
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功将 {updated} 个通知模板标记为活跃状态')

    mark_as_active.short_description = "将选中的通知模板标记为活跃"

    def mark_as_inactive(self, request, queryset):
        """
        批量停用通知模板
        """
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功将 {updated} 个通知模板标记为非活跃状态')

    mark_as_inactive.short_description = "将选中的通知模板标记为非活跃"

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
