from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PaperForm
from .models import Paper


@login_required
def paper_list_view(request):
    papers = Paper.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'papers/paper_list.html', {'papers': papers})


@login_required
def paper_create_view(request):
    if request.method == 'POST':
        form = PaperForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            paper = form.save(commit=False)
            paper.owner = request.user
            paper.save()
            return redirect('paper_list')
    else:
        form = PaperForm(user=request.user)
    return render(request, 'papers/paper_form.html', {'form': form})


@login_required
def paper_detail_view(request, pk):
    paper = get_object_or_404(Paper, pk=pk, owner=request.user)
    return render(request, 'papers/paper_detail.html', {'paper': paper})


@login_required
def paper_edit_view(request, pk):
    paper = get_object_or_404(Paper, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = PaperForm(request.POST, request.FILES, instance=paper, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('paper_detail', pk=paper.pk)
    else:
        form = PaperForm(instance=paper, user=request.user)
    return render(request, 'papers/paper_form.html', {'form': form, 'paper': paper})


@login_required
def paper_delete_view(request, pk):
    paper = get_object_or_404(Paper, pk=pk, owner=request.user)
    if request.method == 'POST':
        paper.delete()
        return redirect('paper_list')
    return render(request, 'papers/paper_confirm_delete.html', {'paper': paper})
