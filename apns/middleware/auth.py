# middleware/auth.py
import requests
from django.conf import settings
from django.http import JsonResponse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
logger = logging.getLogger(__name__)


class TokenAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.auth_api_url = f"{settings.BASE_URL.rstrip('/')}/users/api/users/me/"
        self.exempt_paths = [
            '/users/api/auth/login/',
            '/users/api/auth/register/',  # 添加注册接口
            '/users/api/auth/refresh/',   # 添加刷新令牌接口
            '/users/api/auth/verify/',    # 添加验证接口
            '/apns/api/purchase/verify/', # 添加内购验证接口
            '/apns/api/purchase/webhook/',         # 添加webhook接口
            '/admin/',
            '/openapi',
            '/static/',
            '/media/',
            '/swagger/',
            '/redoc/',
            '/health/',                   # 健康检查接口
            '/metrics/'
        ]

    def __call__(self, request):
        if request.method == 'OPTIONS':
            return self.get_response(request)

        path = request.path_info
        logger.debug(f"处理请求: {request.method} {path}")

        if self.should_authenticate(request):
            logger.debug(f"路径 {path} 需要认证")
            user_info = self.authenticate(request)
            if isinstance(user_info, JsonResponse):
                logger.warning(f"认证失败: {path}")
                return user_info
            request.remote_user = user_info
            logger.debug(f"认证成功: {path}, 用户ID: {user_info.get('id')}")
        else:
            logger.debug(f"路径 {path} 不需要认证")

        return self.get_response(request)

    def should_authenticate(self, request):
        path = request.path_info

        # 精确匹配
        if path in self.exempt_paths:
            logger.debug(f"路径 {path} 精确匹配排除规则，不需要认证")
            return False

        # 前缀匹配
        for exempt in self.exempt_paths:
            if path.startswith(exempt):
                logger.debug(f"路径 {path} 匹配排除规则 {exempt}，不需要认证")
                return False

        # 检查视图是否标记为不需要认证
        if hasattr(request, 'resolver_match') and request.resolver_match:
            view_func = request.resolver_match.func
            if getattr(view_func, 'auth_exempt', False):
                logger.debug(f"视图函数 {view_func.__name__} 标记为不需要认证")
                return False

        logger.debug(f"路径 {path} 需要认证")
        return True

    def authenticate(self, request):
        token = self.extract_token(request)
        if not token:
            logger.warning("请求缺少认证凭据")
            return JsonResponse({'detail': 'Missing credentials'}, status=401)

        session = requests.Session()
        retries = Retry(total=2, backoff_factor=0.1)
        session.mount('https://', HTTPAdapter(max_retries=retries))

        try:
            logger.debug(f"向认证服务发送请求: {self.auth_api_url}")
            response = session.get(
                self.auth_api_url,
                headers={'Authorization': token},
                timeout=3
            )
            response.raise_for_status()
            user_data = response.json().get('data', {})
            logger.debug(f"认证成功，用户ID: {user_data.get('id')}")
            return user_data
        except requests.HTTPError as e:
            logger.warning(f"认证服务返回错误: {e.response.status_code}")
            return JsonResponse(
                {'detail': 'Invalid token'},
                status=401 if e.response.status_code == 401 else 503
            )
        except requests.RequestException as e:
            logger.error(f"认证服务请求异常: {str(e)}")
            return JsonResponse({'detail': 'Auth service error'}, status=503)

    def extract_token(self, request):
        """从请求中提取Token"""
        raw_token = request.headers.get('Authorization', '')
        if raw_token:
            return raw_token.strip()
        return request.COOKIES.get(settings.TOKEN_COOKIE_NAME)

def auth_exempt(view_func):
    """标记视图函数为不需要认证"""
    view_func.auth_exempt = True
    return view_func