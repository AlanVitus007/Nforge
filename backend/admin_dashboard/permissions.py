from rest_framework.permissions import BasePermission


class IsNForgeAdmin(BasePermission):
    """
    Permission class that grants access only to Django staff or superusers.
    Authenticated non-admin users (including project owners, editors, and viewers)
    are denied access with HTTP 403 Forbidden.
    Unauthenticated users are denied with HTTP 401 Unauthorized when combined with
    standard DRF authentication (e.g. IsAuthenticated).
    """

    message = "Admin access required. Only staff or superusers may access this resource."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return bool(user.is_staff or user.is_superuser)
