from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from utils.mixins import *
from django.utils import timezone

from .models import DeviceToken
from .serializers import DeviceTokenSerializer, DeviceTokenCreateSerializer
from utils.permissions import IsAuthenticatedExternal


# Create your views here.

class DeviceTokenViewSet(CreateModelMixin,
                         UpdateModelMixin,
                         PartialUpdateModelMixin,
                         RetrieveModelMixin,
                         ListModelMixin,
                         GenericViewSet):
    """设备令牌视图集，提供完整的CRUD功能"""
    queryset = DeviceToken.objects.all()
    permission_classes = [IsAuthenticatedExternal]

    def get_serializer_class(self):
        """根据操作类型返回不同的序列化器"""
        if self.action == 'create':
            return DeviceTokenCreateSerializer
        return DeviceTokenSerializer

    def get_queryset(self):
        """可以根据用户ID过滤设备令牌"""
        queryset = DeviceToken.objects.all()
        user_id = self.request.remote_user.get('id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """停用设备令牌"""
        device_token = self.get_object()
        device_token.mark_inactive()
        return Response({
            'code': 200,
            'msg': 'device token deactivated',
            'data': 'device token deactivated'
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def deactivate_by_user(self, request):
        """停用用户的所有设备令牌"""
        user_id = self.request.remote_user.get('id')
        if not user_id:
            return Response({
                'code': status.HTTP_400_BAD_REQUEST,
                'msg': '必须提供用户ID',
                'data': '必须提供用户ID'
            },
                status=status.HTTP_400_BAD_REQUEST
            )

        devices = DeviceToken.objects.filter(user_id=user_id, is_active=True)
        count = devices.count()
        devices.update(is_active=False, updated_at=timezone.now())

        return Response({
            'code': status.HTTP_200_OK,
            'msg': '设置成功',
            'data': count
        }, status=status.HTTP_200_OK)
