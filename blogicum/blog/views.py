from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
    ListView,
    DetailView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django import forms
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.db.models import Q

from .models import Post, Category, Comment
from .forms import CommentForm


User = get_user_model()


class PostFormMixin:
    model = Post
    fields = ['title', 'text', 'location', 'category', 'pub_date', 'image']
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['pub_date'].widget = forms.DateTimeInput(
            attrs={'type': 'datetime-local'}
        )
        return form


class RedirectToPostMixin:
    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        )


class RedirectToProfile:
    def get_success_url(self, **kwargs):
        username = self.request.user.username

        return reverse_lazy('blog:profile', kwargs={'username': username})


class CheckingUserRights(UserPassesTestMixin):
    def test_func(self):
        object = self.get_object()
        return self.request.user == object.author

    def handle_no_permission(self):
        return redirect(self.get_login_url())
    
    def get_login_url(self):
        login_url = reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        )
        return login_url


class CreatePost(LoginRequiredMixin, PostFormMixin,
                 RedirectToProfile, CreateView):
    pass


class EditPost(LoginRequiredMixin, CheckingUserRights,
               PostFormMixin, RedirectToPostMixin, UpdateView):

    def get_object(self):
        post_id = self.kwargs['post_id']
        post = get_object_or_404(Post, pk=post_id)

        return post


class DeletePost(LoginRequiredMixin, CheckingUserRights,
                 RedirectToProfile, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    success_url = reverse_lazy('blog:index')

    def get_object(self, **kwargs):
        post_id = self.kwargs['post_id']
        post = get_object_or_404(Post, pk=post_id)

        return post


class CreateComment(LoginRequiredMixin, RedirectToPostMixin, CreateView):
    model = Comment
    fields = ['text']
    template_name = 'blog/detail.html'

    def form_valid(self, form):
        username = self.request.user
        text = form.cleaned_data['text']

        form.instance.author = username
        form.instance.post = get_object_or_404(Post, pk=self.kwargs['post_id'])

        send_mail(
            subject='New comment',
            message=(
                f'{username} пытался опубликовать запись!\n'
                f'Текст комментария:{text}'
            ),
            from_email='blogicum@ya.ru',
            recipient_list=User.objects.values('email').exclude(
                email=None
            ),
            fail_silently=True,
        )

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = get_object_or_404(Post, pk=self.kwargs['post_id'])

        if (
            post.pub_date > timezone.now()
            or post.is_published is False
            or post.category.is_published is False
        ) and self.request.user != post.author:
            raise Http404('Page not found')

        comments = post.comments.all()

        context['post'] = post
        context['comments'] = comments
        return context


class EditComment(LoginRequiredMixin, RedirectToPostMixin, CheckingUserRights,
                  UpdateView):
    model = Comment
    fields = ['text']
    template_name = 'blog/comment.html'

    def get_object(self, **kwargs):
        comment_id = self.kwargs['comment_id']
        comment = get_object_or_404(Comment, pk=comment_id)

        return comment


class DeleteComment(LoginRequiredMixin, RedirectToPostMixin,
                    CheckingUserRights, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'

    def get_object(self, **kwargs):
        comment_id = self.kwargs['comment_id']
        comment = get_object_or_404(Comment, pk=comment_id)

        return comment

    def get_context_data(self, **kwargs):
        context = {
            'comment': super().get_context_data(**kwargs)['comment']
        }
        return context


class EditProfile(LoginRequiredMixin, RedirectToProfile, UpdateView):
    model = User

    fields = ['username', 'first_name', 'last_name', 'email']
    template_name = 'blog/user.html'

    def get_object(self, queryset=None):
        return self.request.user


class IndexPosts(ListView):
    model = Post
    template_name = 'blog/index.html'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('category')
        queryset = queryset.filter(
            pub_date__lte=timezone.now(),
            is_published__exact=True,
            category__is_published=True
        )
        return queryset


class UserProfile(ListView):
    model = Post
    template_name = 'blog/profile.html'
    paginate_by = 10

    def get_queryset(self):
        username = self.kwargs['username']
        self.profile = get_object_or_404(User, username=username)

        queryset = super().get_queryset().filter(author=self.profile)

        if self.request.user != self.profile:
            queryset = queryset.filter(
                is_published=True
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.profile

        return context


class CategoryProfile(ListView):
    model = Post
    template_name = 'blog/category.html'
    paginate_by = 10

    def get_queryset(self):
        category_slug = self.kwargs['category_slug']
        self.category = get_object_or_404(Category, slug=category_slug)

        if self.category.is_published is False:
            raise Http404('Page not found')

        queryset = super().get_queryset().filter(category=self.category)

        queryset = queryset.exclude(
            Q(is_published=False) | Q(pub_date__gt=timezone.now())
        )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category

        return context


class PostDetail(DetailView):
    model = Post
    template_name = 'blog/detail.html'

    def get_object(self):
        post_id = self.kwargs['post_id']

        return get_object_or_404(Post, pk=post_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = CommentForm()
        post = self.get_object()

        if (
            post.pub_date > timezone.now()
            or post.is_published is False
            or post.category.is_published is False
        ) and self.request.user != post.author:
            raise Http404('Page not found')

        comments = post.comments.all()

        context['post'] = post
        context['comments'] = comments
        context['form'] = form

        return context
