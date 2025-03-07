from django.contrib import admin

from .models import Category, Location, Post


@admin.register(Post, Location, Category)
class CustomAdmin(admin.ModelAdmin):
    pass
