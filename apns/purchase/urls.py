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
] 