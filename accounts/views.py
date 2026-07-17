from django.shortcuts import redirect, render

from .forms import LoginForm, RegisterForm
from .services import authenticate_user, logout_user, register_user


def home_view(request):
    return render(request, 'accounts/home.html')


def login_view(request):
    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = authenticate_user(request)
        if user is not None:
            return redirect('profile')

        form.add_error(None, 'Invalid username or password.')

    return render(request, 'accounts/login.html', {'form': form})


def register_view(request):
    form = RegisterForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        register_user(data)
        return redirect('login')

    return render(request, 'accounts/register.html', {'form': form})


def logout_view(request):
    logout_user(request)
    return redirect('login')


def profile_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    return render(request, 'accounts/profile.html', {'user': request.user})