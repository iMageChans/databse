import json
import time
import httpx
import jwt
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.backends import default_backend
from django.utils import timezone
from .models import AppleAppConfiguration, NotificationTemplate
from devices.models import DeviceToken


class AppleNotificationService:
    """苹果推送通知服务"""
    
    def __init__(self, app_config_id=None, bundle_id=None):
        """
        初始化推送服务
        可以通过app_config_id或bundle_id指定应用配置
        """
        if app_config_id:
            self.app_config = AppleAppConfiguration.objects.get(id=app_config_id, is_active=True)
        elif bundle_id:
            self.app_config = AppleAppConfiguration.objects.get(bundle_id=bundle_id, is_active=True)
        else:
            raise ValueError("必须提供app_config_id或bundle_id")
        
        self.bundle_id = self.app_config.bundle_id
        self.team_id = self.app_config.team_id
        self.key_id = self.app_config.key_id
        self.private_key_str = self.app_config.auth_key
        self.apns_host = self.app_config.get_apns_host()
        self.apns_port = 443
        
        # 加载私钥
        self.private_key = load_pem_private_key(
            self.private_key_str.encode('utf-8'),
            password=None,
            backend=default_backend()
        )
    
    def _generate_token(self):
        """生成 APNs JWT token"""
        headers = {
            'alg': 'ES256',
            'kid': self.key_id
        }
        payload = {
            'iss': self.team_id,
            'iat': int(time.time())
        }
        return jwt.encode(payload, self.private_key, algorithm='ES256', headers=headers)
    
    def send_push_notification(self, device_token, title="", body="",
                              badge=1, sound="default", custom_data=None):
        """
        发送推送通知
        """
        try:
            # 准备通知内容
            notification = {
                "aps": {
                    "alert": {
                        "title": title,
                        "body": body
                    },
                    "badge": badge,
                    "sound": sound
                }
            }
            
            # 添加自定义数据
            if custom_data:
                notification.update(custom_data)
            
            # 准备请求头
            headers = {
                'apns-topic': self.bundle_id,
                'authorization': f'bearer {self._generate_token()}',
                'apns-push-type': 'alert',
                'apns-priority': '10',
                'apns-expiration': '0',
                'content-type': 'application/json'
            }
            
            # 使用 httpx 发送请求
            url = f'https://{self.apns_host}/3/device/{device_token}'
            
            with httpx.Client(http2=True) as client:
                response = client.post(
                    url,
                    json=notification,
                    headers=headers
                )
            
            if response.status_code == 200:
                print(f"推送发送成功: device_token={device_token}")
                return True
            else:
                error_response = response.json()
                reason = error_response.get('reason', 'Unknown error')
                print(f"推送发送失败: {reason}")
                
                if reason in ['BadDeviceToken', 'Unregistered']:
                    # 标记设备令牌为无效
                    DeviceToken.objects.filter(device_token=device_token).update(
                        is_active=False, 
                        updated_at=timezone.now()
                    )
                
                return False
        
        except Exception as e:
            print(f"推送发送异常: {str(e)}")
            return False
    
    def send_notification_by_template(self, device_token, template_id, context=None):
        """
        使用模板发送通知
        context: 用于替换模板中的变量，例如 {"name": "张三"}
        """
        try:
            template = NotificationTemplate.objects.get(
                id=template_id, 
                app_config=self.app_config,
                is_active=True
            )
            
            title = template.title
            body = template.body
            
            # 替换模板中的变量
            if context:
                for key, value in context.items():
                    placeholder = f"{{{{{key}}}}}"
                    title = title.replace(placeholder, str(value))
                    body = body.replace(placeholder, str(value))
            
            return self.send_push_notification(
                device_token=device_token,
                title=title,
                body=body,
                badge=template.badge,
                sound=template.sound,
                custom_data=template.custom_data
            )
        
        except NotificationTemplate.DoesNotExist:
            print(f"通知模板不存在或未激活: template_id={template_id}")
            return False
        except Exception as e:
            print(f"发送模板通知异常: {str(e)}")
            return False
    
    def send_notification_to_user(self, user_id, title, body, badge=1, sound="default", custom_data=None):
        """
        向用户的所有活跃设备发送通知
        """
        device_tokens = DeviceToken.objects.filter(user_id=user_id, is_active=True)
        success_count = 0
        
        for device in device_tokens:
            result = self.send_push_notification(
                device_token=device.device_token,
                title=title,
                body=body,
                badge=badge,
                sound=sound,
                custom_data=custom_data
            )
            if result:
                success_count += 1
        
        return {
            'total': device_tokens.count(),
            'success': success_count
        }
    
    def send_template_to_user(self, user_id, template_id, context=None):
        """
        使用模板向用户的所有活跃设备发送通知
        """
        device_tokens = DeviceToken.objects.filter(user_id=user_id, is_active=True)
        success_count = 0
        
        for device in device_tokens:
            result = self.send_notification_by_template(
                device_token=device.device_token,
                template_id=template_id,
                context=context
            )
            if result:
                success_count += 1
        
        return {
            'total': device_tokens.count(),
            'success': success_count
        } 