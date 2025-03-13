from rest_framework import serializers
from .models import AppleAppConfiguration, NotificationTemplate
from utils.serializers_fields import TimestampField


class AppleAppConfigurationSerializer(serializers.ModelSerializer):
    """苹果应用配置序列化器"""
    
    created_at = TimestampField(read_only=True)
    updated_at = TimestampField(read_only=True)
    
    class Meta:
        model = AppleAppConfiguration
        fields = ['id', 'name', 'bundle_id', 'team_id', 'key_id', 
                 'is_production', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AppleAppConfigurationDetailSerializer(AppleAppConfigurationSerializer):
    """包含敏感信息的苹果应用配置序列化器，仅用于管理员"""
    
    class Meta(AppleAppConfigurationSerializer.Meta):
        fields = AppleAppConfigurationSerializer.Meta.fields + ['auth_key']


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """通知模板序列化器"""
    
    created_at = TimestampField(read_only=True)
    updated_at = TimestampField(read_only=True)
    app_name = serializers.CharField(source='app_config.name', read_only=True)
    
    class Meta:
        model = NotificationTemplate
        fields = ['id', 'app_config', 'app_name', 'name', 'title', 'body', 
                 'sound', 'badge', 'custom_data', 'is_active', 
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'app_name'] 