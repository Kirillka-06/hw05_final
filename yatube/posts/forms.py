from django.contrib.auth.forms import UserCreationForm
from django import forms

from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta(UserCreationForm.Meta):
        model = Post
        fields = ('text', 'group', 'image')


class CommentForm(forms.ModelForm):
    class Meta(UserCreationForm.Meta):
        model = Comment
        fields = ('text',)
