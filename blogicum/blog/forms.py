from django.forms import ModelForm
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from .models import Comment


User = get_user_model()


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']