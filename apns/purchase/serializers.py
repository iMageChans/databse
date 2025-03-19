from rest_framework import serializers
from .models import Purchase


class PurchaseSerializer(serializers.ModelSerializer):
    """购买记录序列化器"""

    class Meta:
        model = Purchase
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class VerifyReceiptSerializer(serializers.Serializer):
    """验证收据请求序列化器"""
    receipt_data = serializers.CharField(required=True, help_text='苹果收据数据')
    user_id = serializers.IntegerField(required=True, help_text='用户ID')
    sandbox = serializers.BooleanField(required=False, default=True, help_text='是否使用沙盒环境')
    app_id = serializers.CharField(required=False, allow_null=True, help_text='应用ID')


class NotificationSerializer(serializers.Serializer):
    """苹果通知序列化器"""
    notification_type = serializers.CharField(required=False, help_text='通知类型')
    unified_receipt = serializers.DictField(required=False, help_text='统一收据信息')
    auto_renew_status = serializers.BooleanField(required=False, help_text='自动续订状态')
    auto_renew_product_id = serializers.CharField(required=False, allow_null=True, help_text='自动续订产品ID')
    environment = serializers.CharField(required=False, help_text='环境（沙盒/生产）')

    def validate(self, data):
        """验证通知数据"""
        unified_receipt = data.get('unified_receipt', {})
        if not unified_receipt.get('latest_receipt'):
            raise serializers.ValidationError("缺少latest_receipt")
        if not unified_receipt.get('latest_receipt_info'):
            raise serializers.ValidationError("缺少latest_receipt_info")
        return data
