from django.contrib import admin

from social.models import Comment, Follow, Like, Notification, Post, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name")
    search_fields = ("user__username", "full_name")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("author", "created_at")
    list_filter = ("created_at",)
    search_fields = ("author__username", "caption")


admin.site.register((Comment, Follow, Like, Notification))
