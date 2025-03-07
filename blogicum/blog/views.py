from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseNotFound
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django import forms
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.db.models import Q

from .models import Post, Category, Comment
from .forms import CommentForm


User = get_user_model()


class CreatePost(LoginRequiredMixin, CreateView):
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

    def get_success_url(self, **kwargs):
        username = self.request.user.username

        return reverse_lazy('blog:profile', kwargs={'username': username})


class EditPost(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    fields = ['title', 'text', 'location', 'category', 'pub_date', 'image']
    template_name = 'blog/create.html'

    def get_login_url(self):
        login_url = reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        )
        return login_url

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author

    def handle_no_permission(self):
        return redirect(self.get_login_url())

    def form_valid(self, form):
        form.instance.author = self.request.user
        if form.instance.pub_date > timezone.now():
            form.instance.is_published = False
        else:
            form.instance.is_published = True
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['pub_date'].widget = forms.DateTimeInput(
            attrs={'type': 'datetime-local'}
        )
        return form

    def get_object(self, **kwargs):
        post_id = self.kwargs['post_id']
        post = get_object_or_404(Post, pk=post_id)

        return post

    def get_success_url(self, **kwargs):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        )


class DeletePost(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    success_url = reverse_lazy('blog:index')

    def get_login_url(self):
        login_url = reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        )
        return login_url

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author

    def handle_no_permission(self):
        return redirect(self.get_login_url())

    def get_object(self, **kwargs):
        post_id = self.kwargs['post_id']
        post = get_object_or_404(Post, pk=post_id)

        return post

    def get_success_url(self, **kwargs):
        username = self.request.user.username

        return reverse_lazy('blog:profile', kwargs={'username': username})


class CreateComment(LoginRequiredMixin, CreateView):
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
            return HttpResponseNotFound('Page not found.')

        comments = post.comments.all()

        context['post'] = post
        context['comments'] = comments
        return context

    def get_success_url(self, **kwargs):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        )


class EditComment(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Comment
    fields = ['text']
    template_name = 'blog/comment.html'

    def get_login_url(self):
        login_url = reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        )
        return login_url

    def handle_no_permission(self):
        return redirect(self.get_login_url())

    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.author

    def get_object(self, **kwargs):
        comment_id = self.kwargs['comment_id']
        comment = get_object_or_404(Comment, pk=comment_id)

        return comment

    def get_success_url(self, **kwargs):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        )


class DeleteComment(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'

    def get_login_url(self):
        login_url = reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        )
        return login_url

    def handle_no_permission(self):
        return redirect(self.get_login_url())

    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.author

    def get_object(self, **kwargs):
        comment_id = self.kwargs['comment_id']
        comment = get_object_or_404(Comment, pk=comment_id)

        return comment

    def get_context_data(self, **kwargs):
        context = {
            'comment': super().get_context_data(**kwargs)['comment']
        }
        return context

    def get_success_url(self, **kwargs):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        )


class EditProfile(LoginRequiredMixin, UpdateView):
    model = User

    fields = ['username', 'first_name', 'last_name', 'email']
    template_name = 'blog/user.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self, **kwargs):
        username = self.request.user.username

        return reverse_lazy('blog:profile', kwargs={'username': username})


class IndexPosts(TemplateView):
    template_name = 'blog/index.html'

    def get_context_data(self):
        context = super().get_context_data()
        page = self.request.GET.get('page')

        post_list = Post.objects.select_related('category').filter(
            pub_date__lte=timezone.now(),
            is_published__exact=True,
            category__is_published=True
        )

        paginator = Paginator(post_list, 10)
        page_obj = paginator.get_page(page)

        context['page_obj'] = page_obj

        return context


def post_detail(request, post_id):
    template = 'blog/detail.html'
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm()

    if (
        post.pub_date > timezone.now()
        or post.is_published is False
        or post.category.is_published is False
    ) and request.user != post.author:
        return HttpResponseNotFound('Page not found.')

    comments = post.comments.all()

    context = {
        'post': post,
        'comments': comments,
        'form': form
    }

    return render(request, template, context)


def user_profile(request, username):
    template = 'blog/profile.html'
    page = request.GET.get('page')

    profile = get_object_or_404(User, username=username)
    post_list = profile.posts.all()

    if request.user.username != username:
        post_list = post_list.filter(
            is_published__exact=True
        )

    paginator = Paginator(post_list, 10)
    page_obj = paginator.get_page(page)

    context = {
        'profile': profile,
        'page_obj': page_obj
    }

    return render(request, template, context)


def category_posts(request, category_slug):
    template = 'blog/category.html'
    page = request.GET.get('page')

    category = get_object_or_404(Category, slug=category_slug)

    if category.is_published is False:
        return HttpResponseNotFound('Page not found.')

    posts_list = category.posts.all().exclude(
        Q(is_published=False) | Q(pub_date__gt=timezone.now())
    )

    paginator = Paginator(posts_list, 10)
    page_obj = paginator.get_page(page)

    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, template, context)
