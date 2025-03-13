from django.shortcuts import render
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from utils.mixins import *
from .models import AppleAppConfiguration, NotificationTemplate
from .serializers import (
    AppleAppConfigurationSerializer, 
    AppleAppConfigurationDetailSerializer,
    NotificationTemplateSerializer
)
from utils.permissions import IsAuthenticatedExternal
from rest_framework.permissions import IsAdminUser
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response
from rest_framework import status

# Create your views here.

class AppleAppConfigurationViewSet(CreateModelMixin,
                                  UpdateModelMixin,
                                  PartialUpdateModelMixin,
                                  RetrieveModelMixin,
                                  ListModelMixin,
                                  GenericViewSet):
    """苹果应用配置视图集"""
    queryset = AppleAppConfiguration.objects.all()
    permission_classes = [IsAdminUser]  # 仅管理员可访问
    
    def get_serializer_class(self):
        """根据操作类型返回不同的序列化器"""
        if self.action in ['retrieve', 'create', 'update', 'partial_update']:
            return AppleAppConfigurationDetailSerializer
        return AppleAppConfigurationSerializer
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """切换应用配置的启用状态"""
        app_config = self.get_object()
        app_config.is_active = not app_config.is_active
        app_config.save()
        
        return Response({
            'code': status.HTTP_200_OK,
            'msg': _('状态已更新'),
            'data': {'is_active': app_config.is_active}
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def toggle_environment(self, request, pk=None):
        """切换应用配置的环境（生产/开发）"""
        app_config = self.get_object()
        app_config.is_production = not app_config.is_production
        app_config.save()
        
        return Response({
            'code': status.HTTP_200_OK,
            'msg': _('环境已更新'),
            'data': {'is_production': app_config.is_production}
        }, status=status.HTTP_200_OK)


class NotificationTemplateViewSet(CreateModelMixin,
                                 UpdateModelMixin,
                                 PartialUpdateModelMixin,
                                 RetrieveModelMixin,
                                 ListModelMixin,
                                 DestroyModelMixin,
                                 GenericViewSet):
    """通知模板视图集"""
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAdminUser]  # 仅管理员可访问
    
    def get_queryset(self):
        """可以根据应用配置ID过滤通知模板"""
        queryset = NotificationTemplate.objects.all()
        app_config_id = self.request.query_params.get('app_config_id')
        if app_config_id:
            queryset = queryset.filter(app_config_id=app_config_id)
        return queryset
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """切换通知模板的启用状态"""
        template = self.get_object()
        template.is_active = not template.is_active
        template.save()
        
        return Response({
            'code': status.HTTP_200_OK,
            'msg': _('状态已更新'),
            'data': {'is_active': template.is_active}
        }, status=status.HTTP_200_OK)
