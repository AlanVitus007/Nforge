from django.shortcuts import redirect, render

from papers.models import Paper
from projects.models import Project
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

    projects = Project.objects.filter(owner=request.user).order_by('-updated_at')[:3]
    papers = Paper.objects.filter(owner=request.user).order_by('-created_at')[:3]
    project_count = Project.objects.filter(owner=request.user).count()
    paper_count = Paper.objects.filter(owner=request.user).count()
    recent_activity = [
        {'label': 'Projects', 'value': str(project_count)},
        {'label': 'Papers', 'value': str(paper_count)},
        {'label': 'Last update', 'value': projects[0].updated_at.strftime('%b %d') if projects else '—'},
    ]
    ai_summaries = [
        {'title': paper.title, 'summary': f"AI summary ready for {paper.title}."} for paper in papers[:2]
    ]

    context = {
        'user': request.user,
        'projects': projects,
        'papers': papers,
        'recent_activity': recent_activity,
        'ai_summaries': ai_summaries,
    }
    return render(request, 'accounts/profile.html', context)