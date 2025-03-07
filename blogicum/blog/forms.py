from django.forms import ModelForm
from django.contrib.auth import get_user_model
from .models import Comment


User = get_user_model()


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
