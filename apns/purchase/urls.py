from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PurchaseVerificationView, AppleWebhookView, PurchaseListView

# 创建路由器
router = DefaultRouter()
router.register(r'verify', PurchaseVerificationView, basename='purchase-verify')
router.register(r'webhook', AppleWebhookView, basename='apple-webhook')
router.register(r'list', PurchaseListView, basename='purchase-list')

# URL模式
urlpatterns = [
    path('', include(router.urls)),
    # 添加一个简单的状态检查接口
    path('status/<int:user_id>/', PurchaseListView.as_view({'get': 'get_user_status'}), name='user-subscription-status'),
] 