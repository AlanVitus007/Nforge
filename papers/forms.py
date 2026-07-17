from django import forms

from projects.models import Project

from .models import Paper


class PaperForm(forms.ModelForm):
    project = forms.ModelChoiceField(queryset=Project.objects.none(), required=True)

    class Meta:
        model = Paper
        fields = ['title', 'authors', 'journal', 'publication_year', 'keywords', 'abstract', 'project', 'pdf_file']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user is not None:
            self.fields['project'].queryset = Project.objects.filter(owner=self.user)
        else:
            self.fields['project'].queryset = Project.objects.none()
