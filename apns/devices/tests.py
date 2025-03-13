from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from .models import DeviceToken


class DeviceTokenTests(TestCase):
    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # 创建测试设备令牌
        self.device_token = DeviceToken.objects.create(
            user_id=1,
            device_id='test-device-id',
            device_token='test-device-token',
            is_active=True
        )
        
        # API URL
        self.list_url = reverse('devicetoken-list')
        self.detail_url = reverse('devicetoken-detail', args=[self.device_token.id])
    
    def test_create_device_token(self):
        """测试创建设备令牌"""
        data = {
            'user_id': 2,
            'device_id': 'new-device-id',
            'device_token': 'new-device-token'
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DeviceToken.objects.count(), 2)
    
    def test_get_device_tokens(self):
        """测试获取设备令牌列表"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_get_device_token_detail(self):
        """测试获取设备令牌详情"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['device_id'], 'test-device-id')
    
    def test_update_device_token(self):
        """测试更新设备令牌"""
        data = {'device_token': 'updated-token'}
        response = self.client.patch(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.device_token.refresh_from_db()
        self.assertEqual(self.device_token.device_token, 'updated-token')
    
    def test_deactivate_device_token(self):
        """测试停用设备令牌"""
        url = reverse('devicetoken-deactivate', args=[self.device_token.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.device_token.refresh_from_db()
        self.assertFalse(self.device_token.is_active)
    
    def test_register_device_token(self):
        """测试注册设备令牌功能"""
        data = {
            'user_id': 1,
            'device_id': 'test-device-id',  # 使用已存在的设备ID
            'device_token': 'updated-device-token'
        }
        url = reverse('devicetoken-register')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # 验证是更新而不是创建新记录
        self.assertEqual(DeviceToken.objects.count(), 1)
        self.device_token.refresh_from_db()
        self.assertEqual(self.device_token.device_token, 'updated-device-token')
