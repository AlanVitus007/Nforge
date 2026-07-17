from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProjectForm
from .models import Project


@login_required
def project_list_view(request):
    projects = Project.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'projects/project_list.html', {'projects': projects})


@login_required
def project_create_view(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            return redirect('project_list')
    else:
        form = ProjectForm()

    return render(request, 'projects/project_form.html', {'form': form})
