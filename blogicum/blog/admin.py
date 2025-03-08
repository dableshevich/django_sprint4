from django.contrib import admin

from .models import Category, Location, Post, Comment


@admin.register(Post, Location, Category, Comment)
class CustomAdmin(admin.ModelAdmin):
    pass
