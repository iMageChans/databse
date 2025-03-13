from rest_framework import serializers
from .models import Notifications
from utils.serializers_fields import TimestampField
import pytz

class NotificationSendSerializer(serializers.Serializer):
    device_id = serializers.CharField(required=True)
    title = serializers.CharField(required=True)
    body = serializers.CharField(required=True)
    app_id = serializers.CharField(required=True)


class NotificationsSerializer(serializers.ModelSerializer):
    """通知设置序列化器"""
    
    created_at = TimestampField(read_only=True)
    updated_at = TimestampField(read_only=True)
    
    class Meta:
        model = Notifications
        fields = ['id', 'user_id', 'timezone', 'notify_time', 'days_remaining', 
                 'is_active', 'last_sent', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_sent']
    
    def validate_timezone(self, value):
        """验证时区是否有效"""
        try:
            pytz.timezone(value)
            return value
        except pytz.exceptions.UnknownTimeZoneError:
            raise serializers.ValidationError("无效的时区")
    
    def validate_notify_time(self, value):
        """验证通知时间格式是否正确 (HH:mm)"""
        try:
            hour, minute = value.split(':')
            if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
                raise ValueError
            return value
        except (ValueError, AttributeError):
            raise serializers.ValidationError("通知时间格式应为 HH:mm")
    
    def create(self, validated_data):
        """创建通知设置，并将用户的其他设置设为非激活状态"""
        user_id = validated_data.get('user_id')
        
        # 将该用户的所有其他通知设置设为非激活状态
        Notifications.objects.filter(user_id=user_id, is_active=True).update(is_active=False)
        
        # 创建新的通知设置
        notification = Notifications.objects.create(**validated_data)
        return notification
