from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeviceTokenViewSet

router = DefaultRouter()
router.register(r'tokens', DeviceTokenViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # 添加 token/ 路径，指向 DeviceTokenViewSet 的 create 方法
] 