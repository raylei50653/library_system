# users/permissions.py
from rest_framework.permissions import BasePermission

class IsAdminRole(BasePermission):
    """
    僅允許 role == 'admin' 的使用者存取（需已通過 JWT 驗證）。
    """
    def has_permission(self, request, view):
        u = getattr(request, "user", None)
        return bool(u and u.is_authenticated and getattr(u, "role", None) == "admin")
