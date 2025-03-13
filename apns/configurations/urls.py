from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AppleAppConfigurationViewSet, NotificationTemplateViewSet

router = DefaultRouter()
router.register(r'app-configs', AppleAppConfigurationViewSet)
router.register(r'notification-templates', NotificationTemplateViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 