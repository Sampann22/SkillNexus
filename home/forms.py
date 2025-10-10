from django import forms
from home.models import Experience, Post, Project, Tag

class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = ['organization', 'role', 'years', 'details']

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content']

class ProjectForm(forms.ModelForm):
    required_skills = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2',
            'style': 'width: 100%;'
        }),
        required=False,
        label="Required Skills"
    )

    class Meta:
        model = Project
        fields = ['project_description', 'required_skills', 'terms_of_contract', 'status']
        widgets = {
            'project_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'terms_of_contract': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'collaborators': forms.SelectMultiple(attrs={'class': 'form-select select2'}),
        }
