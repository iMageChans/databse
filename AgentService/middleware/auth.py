import requests
import re
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.models import AnonymousUser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class TokenAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.auth_api_url = f"{settings.BASE_URL.rstrip('/')}/users/api/users/me/"
        self.exempt_patterns = [
            re.compile(r'^/users/api/auth/login/?$'),
            re.compile(r'^/admin/'),
            re.compile(r'^/openapi\.json$'),
            re.compile(r'^/static/'),
            re.compile(r'^/media/'),
            re.compile(r'^/swagger/'),
            re.compile(r'^/redoc/')
        ]
        self.retries = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504]
        )

    def __call__(self, request):
        if request.method == 'OPTIONS':
            return self.get_response(request)

        if self.should_authenticate(request):
            user_info = self.authenticate(request)
            if isinstance(user_info, JsonResponse):
                return user_info
            # 注入到 request.user
            request.remote_user = user_info if user_info else AnonymousUser()

        return self.get_response(request)

    def should_authenticate(self, request):
        path = request.path_info
        return not any(pattern.match(path) for pattern in self.exempt_patterns)

    def authenticate(self, request):
        token = self.extract_token(request)
        if not token:
            return JsonResponse({'detail': 'Missing credentials'}, status=401)

        session = requests.Session()
        session.mount('http://', HTTPAdapter(max_retries=self.retries))
        session.mount('https://', HTTPAdapter(max_retries=self.retries))

        try:
            response = session.get(
                self.auth_api_url,
                headers={'Authorization': f'{token}'},
                timeout=5
            )
            response.raise_for_status()
            return response.json().get('data', {})
        except requests.HTTPError as e:
            return JsonResponse(
                {'detail': 'Invalid token' if e.response.status_code == 401 else 'Auth service error'},
                status=e.response.status_code
            )
        except requests.RequestException as e:
            return JsonResponse({'detail': f'Auth service unreachable: {str(e)}'}, status=503)

    def extract_token(self, request):
        raw_token = request.headers.get('Authorization', '')
        if raw_token:
            return raw_token.strip()
        return request.COOKIES.get(settings.TOKEN_COOKIE_NAME)