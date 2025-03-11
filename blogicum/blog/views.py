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
from django.db.models import Q, Count

from .models import Post, Category, Comment
from .forms import CommentForm, PostForm


User = get_user_model()


class PaginateMixin:
    paginate_by = 10


class PostFormMixin:
    model = Post
    form_class = PostForm
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


class RedirectToProfileMixin:
    def get_success_url(self, **kwargs):
        username = self.request.user.username
        return reverse_lazy('blog:profile', kwargs={'username': username})


class GetPostByPostIdMixin:
    def get_object(self, **kwargs):
        post_id = self.kwargs['post_id']
        post = get_object_or_404(Post, pk=post_id)
        return post


class GetCommentByCommentIdMixin:
    def get_object(self, **kwargs):
        comment_id = self.kwargs['comment_id']
        comment = get_object_or_404(Comment, pk=comment_id)
        return comment


class CheckingUserRightsMixin:
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
                 RedirectToProfileMixin, CreateView):
    pass


class EditPost(LoginRequiredMixin, CheckingUserRightsMixin,
               UserPassesTestMixin, PostFormMixin, RedirectToPostMixin,
               GetPostByPostIdMixin, UpdateView):
    pass


class DeletePost(LoginRequiredMixin, CheckingUserRightsMixin,
                 UserPassesTestMixin, RedirectToProfileMixin,
                 GetPostByPostIdMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    success_url = reverse_lazy('blog:index')

    def get_context_data(self, **kwargs):
        post = super().get_context_data(**kwargs)['post']

        form = PostForm(instance=post or None)
        context = {
            'form': form
        }
        return context


class CreateComment(LoginRequiredMixin, RedirectToPostMixin, CreateView):
    model = Comment
    form_class = CommentForm
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


class EditComment(LoginRequiredMixin, RedirectToPostMixin,
                  CheckingUserRightsMixin, UserPassesTestMixin,
                  GetCommentByCommentIdMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'


class DeleteComment(LoginRequiredMixin, RedirectToPostMixin,
                    CheckingUserRightsMixin, UserPassesTestMixin,
                    GetCommentByCommentIdMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'

    def get_context_data(self, **kwargs):
        context = {
            'comment': super().get_context_data(**kwargs)['comment']
        }
        return context


class EditProfile(LoginRequiredMixin, RedirectToProfileMixin, UpdateView):
    model = User

    fields = ['username', 'first_name', 'last_name', 'email']
    template_name = 'blog/user.html'

    def get_object(self, queryset=None):
        return self.request.user


class IndexPosts(PaginateMixin, ListView):
    model = Post
    template_name = 'blog/index.html'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('category')
        queryset = queryset.filter(
            pub_date__lte=timezone.now(),
            is_published__exact=True,
            category__is_published=True
        ).annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')
        return queryset


class UserProfile(PaginateMixin, ListView):
    model = Post
    template_name = 'blog/profile.html'

    def get_queryset(self):
        username = self.kwargs['username']
        self.profile = get_object_or_404(User, username=username)

        queryset = super().get_queryset().filter(
            author=self.profile
        ).annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')

        if self.request.user != self.profile:
            queryset = queryset.filter(
                is_published=True
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.profile

        return context


class CategoryProfile(PaginateMixin, ListView):
    model = Post
    template_name = 'blog/category.html'

    def get_queryset(self):
        category_slug = self.kwargs['category_slug']
        self.category = get_object_or_404(Category, slug=category_slug)

        if not self.category.is_published:
            raise Http404('Page not found')

        queryset = super().get_queryset().filter(
            category=self.category
        ).annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')

        queryset = queryset.exclude(
            Q(is_published=False) | Q(pub_date__gt=timezone.now())
        )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category

        return context


class PostDetail(GetPostByPostIdMixin, DetailView):
    model = Post
    template_name = 'blog/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = CommentForm()
        post = self.get_object()

        if (
            post.pub_date > timezone.now()
            or not post.is_published
            or not post.category.is_published
        ) and self.request.user != post.author:
            raise Http404('Page not found')

        comments = post.comments.all()

        context['post'] = post
        context['comments'] = comments
        context['form'] = form

        return context
