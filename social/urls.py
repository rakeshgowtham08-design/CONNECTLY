from django.contrib.auth import views as auth_views
from django.urls import path

from social import views

urlpatterns = [
    path("", views.feed, name="feed"),
    path("register/", views.register, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="social/login.html", redirect_authenticated_user=True
        ),
        name="login",
    ),
    path("logout/", views.logout_view, name="logout"),
    path("explore/", views.explore, name="explore"),
    path("search/", views.search, name="search"),
    path("create/", views.create_post, name="create_post"),
    path("post/<int:post_id>/edit/", views.edit_post, name="edit_post"),
    path("post/<int:post_id>/delete/", views.delete_post, name="delete_post"),
    path("post/<int:post_id>/like/", views.toggle_like, name="toggle_like"),
    path("post/<int:post_id>/comment/", views.add_comment, name="add_comment"),
    path(
        "comment/<int:comment_id>/delete/",
        views.delete_comment,
        name="delete_comment",
    ),
    path("u/<str:username>/", views.profile, name="profile"),
    path("u/<str:username>/followers/", views.followers, name="followers"),
    path("u/<str:username>/following/", views.following, name="following"),
    path("u/<str:username>/follow/", views.toggle_follow, name="toggle_follow"),
    path("settings/profile/", views.edit_profile, name="edit_profile"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/read/", views.mark_notifications_read, name="mark_notifications_read"),
]
