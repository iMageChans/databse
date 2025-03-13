from rest_framework import serializers

from utils.serializers_fields import TimestampField
from .models import DeviceToken


class DeviceTokenSerializer(serializers.ModelSerializer):
    """设备令牌序列化器"""

    created_at = TimestampField(read_only=True)
    updated_at = TimestampField(read_only=True)
    
    class Meta:
        model = DeviceToken
        fields = ['id', 'user_id', 'device_id', 'device_token', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class DeviceTokenCreateSerializer(serializers.ModelSerializer):
    """设备令牌创建序列化器"""
    
    class Meta:
        model = DeviceToken
        fields = ['user_id', 'device_id', 'device_token']
    
    def create(self, validated_data):
        """创建或更新设备令牌"""
        user_id = validated_data.get('user_id')
        device_id = validated_data.get('device_id')
        
        # 尝试查找现有设备令牌
        try:
            device_token = DeviceToken.objects.get(
                user_id=user_id,
                device_id=device_id
            )
            # 更新现有记录
            for key, value in validated_data.items():
                setattr(device_token, key, value)
            device_token.is_active = True  # 确保设置为活跃状态
            device_token.save()
        except DeviceToken.DoesNotExist:
            # 创建新记录
            device_token = DeviceToken.objects.create(**validated_data)
        
        return device_token 