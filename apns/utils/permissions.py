# permissions.py
from rest_framework import permissions

class IsAuthenticatedExternal(permissions.BasePermission):
    def has_permission(self, request, view):
        # 添加日志，帮助调试
        print(f"Remote user: {request.remote_user}")
        return bool(request.remote_user)