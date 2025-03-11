from django.forms import ModelForm
from django.contrib.auth import get_user_model
from .models import Comment, Post


User = get_user_model()


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']


class PostForm(ModelForm):
    class Meta:
        model = Post
        exclude = ['author', 'is_published']