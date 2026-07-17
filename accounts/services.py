"""
Business logic for the Accounts app.

All database operations related to authentication
should be placed here instead of views.py.
"""

from django.contrib.auth import authenticate, login, logout

from .models import CustomUser


def register_user(data):
    """
    Create a new user.
    """
    return CustomUser.objects.create_user(
        username=data['username'],
        email=data['email'],
        password=data['password1'],
    )


def authenticate_user(request):
    """
    Authenticate user.
    """
    username = request.POST.get('username')
    password = request.POST.get('password')

    if not username or not password:
        return None

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return user

    return None


def logout_user(request):
    """
    Logout user.
    """
    logout(request)


def update_profile(user, data):
    """
    Update profile.
    """
    return None