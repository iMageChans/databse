import json
import time

import httpx
import jwt
import requests
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.backends import default_backend
from django.conf import settings
from configurations.models import AppleAppConfiguration


class AppleService:
    def __init__(self, app_id):
        app_config = AppleAppConfiguration.objects.get(name=app_id)
        self.client_id = app_config.bundle_id  # 即bundle_id
        self.team_id = app_config.team_id
        self.key_id = app_config.key_id
        self.private_key_str = app_config.auth_key
        self.bundle_id = app_config.bundle_id  # 直接用同一个变量即可，因为client_id就是bundle_id
        # self.apns_endpoint = "https://api.push.apple.com:443"
        self.apns_host = "api.push.apple.com"
        self.apns_port = 443

        self.private_key = app_config.auth_key

        self.apns_client = None

    def generate_client_secret(self):
        """
        使用 iOS App 的 bundle_id 作为 client_id 生成 Apple Sign In 所需的 client_secret
        """
        headers = {
            'kid': self.key_id,
            'alg': 'ES256'
        }

        payload = {
            'iss': self.team_id,
            'iat': int(time.time()),
            'exp': int(time.time()) + 86400 * 180,
            'aud': 'https://appleid.apple.com',
            'sub': self.client_id,  # 这里的client_id就是你的bundle_id
        }

        client_secret = jwt.encode(
            payload,
            self.private_key,
            algorithm='ES256',
            headers=headers
        )

        return client_secret

    def get_apple_public_key(self, kid):
        """获取 Apple 的公钥"""
        try:
            response = requests.get('https://appleid.apple.com/auth/keys')
            keys = response.json().get('keys', [])

            for key in keys:
                if key['kid'] == kid:
                    return json.dumps(key)  # 转换为 JSON 字符串

            raise InvalidTokenError('未找到匹配的公钥')
        except Exception as e:
            print(f"获取公钥失败: {str(e)}")
            raise InvalidTokenError(f'获取公钥失败: {str(e)}')

    def verify_identity_token(self, identity_token):
        """验证 Apple 的 identity token"""
        try:
            # 解析 token 头部
            header = jwt.get_unverified_header(identity_token)
            kid = header.get('kid')

            if not kid:
                raise InvalidTokenError('Token header 中没有 kid')

            # 获取并处理公钥
            jwk_string = self.get_apple_public_key(kid)
            public_key = RSAAlgorithm.from_jwk(jwk_string)

            # 验证 token
            decoded = jwt.decode(
                identity_token,
                key=public_key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer='https://appleid.apple.com'
            )

            return decoded

        except ExpiredSignatureError as e:
            print(f"Token 已过期: {str(e)}")
            return None
        except InvalidTokenError as e:
            print(f"Token 无效: {str(e)}")
            return None
        except Exception as e:
            print(f"验证失败: {str(e)}")
            return None

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

                if reason == 'BadDeviceToken':
                    raise ValueError("无效的设备令牌")
                elif reason == 'Unregistered':
                    raise ValueError("设备未注册或已注销")
                else:
                    raise ValueError(f"推送失败: {reason}")

        except ValueError as ve:
            print(f"推送验证错误: {str(ve)}")
            return False
        except Exception as e:
            print(f"推送发送异常: {str(e)}")
            return False
