from django.urls import path
from .views import RegisterView, LoginView, LogoutView, CurrentUserView, TestProtectedView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('test/', TestProtectedView.as_view(), name='test_protected'),
]
