from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationsViewSet, NotificationsSendViewSet

router = DefaultRouter()
router.register(r'send', NotificationsSendViewSet, basename='notification-send')
router.register(r'settings', NotificationsViewSet, basename='notification-settings')

urlpatterns = [
    path('', include(router.urls)),
]
