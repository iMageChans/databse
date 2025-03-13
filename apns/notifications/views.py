from devices.models import DeviceToken
from notifications.serializers import NotificationSendSerializer
from notifications.service.apple import AppleService
from utils.mixins import *
from rest_framework.viewsets import GenericViewSet
from django.utils.translation import gettext_lazy as _
from .models import Notifications
from .serializers import NotificationsSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from utils.permissions import IsAuthenticatedExternal


class NotificationsSendViewSet(CreateModelMixin,
                               GenericViewSet):

    permission_classes = [IsAuthenticatedExternal]
    serializer_class = NotificationSendSerializer


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = request.remote_user.get('id')

        device_token_record = DeviceToken.objects.filter(
            user_id=user_id,
            device_id=serializer.validated_data.get('device_id')).order_by('-created_at').first()
        if not device_token_record:
            return Response({
                'code': status.HTTP_404_NOT_FOUND,
                'msg': _('未找到设备'),
                'data': {}
            }, status=status.HTTP_404_NOT_FOUND)

        apple_service = AppleService(serializer.validated_data.get('app_id'))

        rsp = apple_service.send_push_notification(
            device_token=device_token_record.device_token,
            title=serializer.validated_data.get('title'),
            body=serializer.validated_data.get('body')
        )

        if rsp:
            return Response({
                'data': '发送成功',
                'msg': '发送成功',
                'code': status.HTTP_201_CREATED,
            })
        return Response({
            'data': 'Invalid or expired device token. Token is marked inactive.',
            'msg':'Invalid or expired device token. Token is marked inactive.',
            'code': status.HTTP_400_BAD_REQUEST,
        })


class NotificationsViewSet(CreateModelMixin,
                          UpdateModelMixin,
                          PartialUpdateModelMixin,
                          RetrieveModelMixin,
                          ListModelMixin,
                          GenericViewSet):
    """通知设置视图集"""
    queryset = Notifications.objects.all()
    serializer_class = NotificationsSerializer
    permission_classes = [IsAuthenticatedExternal]
    
    def get_queryset(self):
        """只返回当前用户的通知设置"""
        queryset = Notifications.objects.all()
        user_id = self.request.remote_user.get('id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset
    
    def perform_create(self, serializer):
        """创建通知设置时自动设置用户ID"""
        user_id = self.request.remote_user.get('id')
        time_zone = self.request.remote_user.get('timezone')
        serializer.save(user_id=user_id, timezone=time_zone)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """获取当前用户的激活通知设置"""
        user_id = request.remote_user.get('id')
        notification = Notifications.objects.filter(user_id=user_id, is_active=True).first()
        
        if notification:
            serializer = self.get_serializer(notification)
            return Response({
                'code': status.HTTP_200_OK,
                'msg': '获取成功',
                'data': serializer.data
            })
        
        return Response({
            'code': status.HTTP_404_NOT_FOUND,
            'msg': '未找到激活的通知设置',
            'data': {}
        }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """激活指定的通知设置，并将用户的其他设置设为非激活状态"""
        notification = self.get_object()
        user_id = notification.user_id
        
        # 将该用户的所有通知设置设为非激活状态
        Notifications.objects.filter(user_id=user_id, is_active=True).update(is_active=False)
        
        # 激活当前通知设置
        notification.is_active = True
        notification.save()
        
        serializer = self.get_serializer(notification)
        return Response({
            'code': status.HTTP_200_OK,
            'msg': '激活成功',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """停用指定的通知设置"""
        notification = self.get_object()
        notification.is_active = False
        notification.save()
        
        serializer = self.get_serializer(notification)
        return Response({
            'code': status.HTTP_200_OK,
            'msg': '停用成功',
            'data': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def decrease_days(self, request):
        """减少所有激活通知设置的剩余天数"""
        user_id = request.remote_user.get('id')
        notification = Notifications.objects.filter(user_id=user_id, is_active=True).first()
        
        if notification:
            notification.decrease_days()
            serializer = self.get_serializer(notification)
            return Response({
                'code': status.HTTP_200_OK,
                'msg': '更新成功',
                'data': serializer.data
            })
        
        return Response({
            'code': status.HTTP_404_NOT_FOUND,
            'msg': '未找到激活的通知设置',
            'data': {}
        }, status=status.HTTP_404_NOT_FOUND)

