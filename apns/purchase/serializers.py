from rest_framework import serializers
from django.utils import timezone
from utils.serializers_fields import TimestampField
from .models import Purchase


class PurchaseSerializer(serializers.ModelSerializer):
    """
    购买记录序列化器
    """
    created_at = TimestampField(read_only=True)
    updated_at = TimestampField(read_only=True)
    # 添加剩余时间字段
    days_remaining = serializers.SerializerMethodField()
    # 添加状态显示字段
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Purchase
        fields = '__all__'
        read_only_fields = ['id', 'user_id', 'transaction_id', 'purchase_date', 
                           'is_active', 'is_successful', 'created_at', 'updated_at',
                           'days_remaining', 'status_display']
    
    def get_days_remaining(self, obj):
        """
        计算剩余天数
        """
        if not obj.expires_at:
            return None
            
        now = timezone.now()
        if now > obj.expires_at:
            return 0
            
        delta = obj.expires_at - now
        return delta.days


class PurchaseVerificationSerializer(serializers.Serializer):
    """
    购买验证序列化器
    """
    receipt_data = serializers.CharField(help_text='苹果收据数据')
    user_id = serializers.IntegerField(help_text='用户ID')
    product_id = serializers.CharField(help_text='产品ID')
    transaction_id = serializers.CharField(help_text='交易ID')
    app_id = serializers.CharField(help_text='应用ID')
    original_transaction_id = serializers.CharField(required=False, help_text='原始交易ID，续订时使用')
    
    def validate_receipt_data(self, value):
        """
        验证收据数据不为空
        """
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("收据数据不能为空")
        return value
    
    def validate_product_id(self, value):
        """
        验证产品ID是否为支持的类型
        """
        valid_products = ["Weekly_Subscription", "Monthly_Subscription", "Yearly_Subscription"]
        if value not in valid_products:
            raise serializers.ValidationError(f"不支持的产品类型: {value}，支持的类型: {', '.join(valid_products)}")
        return value


class PurchaseStatusSerializer(serializers.ModelSerializer):
    """
    购买状态序列化器，用于查询订阅状态
    """
    created_at = TimestampField(read_only=True)
    updated_at = TimestampField(read_only=True)
    days_remaining = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = Purchase
        fields = ['user_id', 'product_id', 'is_active', 'is_successful', 
                 'purchase_date', 'expires_at', 'status', 'days_remaining', 
                 'is_expired', 'created_at', 'updated_at']
        read_only_fields = fields
    
    def get_days_remaining(self, obj):
        """
        计算剩余天数
        """
        if not obj.expires_at:
            return None
            
        now = timezone.now()
        if now > obj.expires_at:
            return 0
            
        delta = obj.expires_at - now
        return delta.days
    
    def get_is_expired(self, obj):
        """
        判断是否已过期
        """
        if not obj.expires_at:
            return True
            
        return timezone.now() > obj.expires_at


class AppleWebhookSerializer(serializers.Serializer):
    """
    苹果服务器通知序列化器
    """
    notification_type = serializers.CharField(required=True, help_text='通知类型')
    app_id = serializers.CharField(required=True, help_text='应用ID')
    latest_receipt = serializers.CharField(required=True, help_text='最新收据')
    latest_receipt_info = serializers.JSONField(required=False, help_text='最新收据信息')
    auto_renew_status = serializers.BooleanField(required=False, help_text='自动续订状态')
    user_id = serializers.IntegerField(required=False, help_text='用户ID')
