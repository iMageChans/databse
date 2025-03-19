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
    sandbox = serializers.BooleanField(required=False, default=False, help_text='是否使用沙盒环境')
    app_id = serializers.CharField(required=False, allow_null=True, help_text='应用ID')


class TransactionInfoSerializer(serializers.Serializer):
    """交易信息序列化器"""
    transactionId = serializers.CharField(required=True)
    originalTransactionId = serializers.CharField(required=True)
    webOrderLineItemId = serializers.CharField(required=False, allow_null=True)
    bundleId = serializers.CharField(required=True)
    productId = serializers.CharField(required=True)
    purchaseDate = serializers.IntegerField(required=True)
    originalPurchaseDate = serializers.IntegerField(required=True)
    expiresDate = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.IntegerField(required=False, default=1)
    type = serializers.CharField(required=False)
    inAppOwnershipType = serializers.CharField(required=False)
    signedDate = serializers.IntegerField(required=False)
    environment = serializers.CharField(required=False)
    transactionReason = serializers.CharField(required=False, allow_null=True)
    price = serializers.IntegerField(required=False, allow_null=True)
    currency = serializers.CharField(required=False, allow_null=True)


class RenewalInfoSerializer(serializers.Serializer):
    """续订信息序列化器"""
    originalTransactionId = serializers.CharField(required=True)
    autoRenewProductId = serializers.CharField(required=False, allow_null=True)
    productId = serializers.CharField(required=False)
    autoRenewStatus = serializers.IntegerField(required=False)
    renewalDate = serializers.IntegerField(required=False, allow_null=True)


class NotificationDataSerializer(serializers.Serializer):
    """通知数据序列化器"""
    appAppleId = serializers.IntegerField(required=False)
    bundleId = serializers.CharField(required=True)
    environment = serializers.CharField(required=True)
    transactionInfo = TransactionInfoSerializer(required=False)
    renewalInfo = RenewalInfoSerializer(required=False)


class NotificationSerializer(serializers.Serializer):
    """苹果通知V2序列化器"""
    notificationType = serializers.CharField(required=True, help_text='通知类型')
    subtype = serializers.CharField(required=False, allow_null=True, help_text='通知子类型')
    notificationUUID = serializers.CharField(required=True, help_text='通知UUID')
    version = serializers.CharField(required=True, help_text='通知版本')
    signedDate = serializers.IntegerField(required=True, help_text='签名时间')
    data = NotificationDataSerializer(required=True, help_text='通知数据')

    def validate(self, data):
        """验证通知数据"""
        notification_data = data.get('data', {})
        if not notification_data.get('bundleId'):
            raise serializers.ValidationError("缺少bundleId")

        # 对于订阅相关的通知，需要验证交易信息
        notification_type = data.get('notificationType')
        if notification_type in ['DID_RENEW', 'DID_FAIL_TO_RENEW', 'EXPIRED',
                                 'RENEWAL_EXTENDED', 'RENEWAL', 'REFUND', 'REVOKE']:
            transaction_info = notification_data.get('transactionInfo')
            if not transaction_info:
                raise serializers.ValidationError("缺少transactionInfo")

        return data


class OldNotificationSerializer(serializers.Serializer):
    """旧版苹果通知序列化器"""
    notification_type = serializers.CharField(required=True, help_text='通知类型')
    unified_receipt = serializers.DictField(required=True, help_text='统一收据信息')
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