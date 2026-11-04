from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from social.forms import CommentForm, PostForm, ProfileForm, RegisterForm
from social.models import Comment, Follow, Like, Notification, Post

User = get_user_model()


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _safe_return_to(request, fallback="feed"):
    candidate = request.META.get("HTTP_REFERER", "")
    if url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(candidate)
    return redirect(fallback)


def _post_queryset():
    return (
        Post.objects.select_related("author", "author__profile")
        .annotate(
            likes_total=Count("likes", distinct=True),
            comments_total=Count("comments", distinct=True),
        )
        .prefetch_related("comments__author", "comments__author__profile")
    )


def _suggested_users(user):
    followed_ids = user.following.values_list("following_id", flat=True)
    return (
        User.objects.exclude(pk=user.pk)
        .exclude(pk__in=followed_ids)
        .select_related("profile")
        .order_by("-date_joined")[:5]
    )


def _render_posts(request, template, posts, **extra):
    liked_post_ids = set()
    if request.user.is_authenticated:
        liked_post_ids = set(
            Like.objects.filter(user=request.user, post__in=posts).values_list(
                "post_id", flat=True
            )
        )
    context = {
        "posts": posts,
        "liked_post_ids": liked_post_ids,
        "comment_form": CommentForm(),
        "suggested_users": (
            _suggested_users(request.user) if request.user.is_authenticated else []
        ),
    }
    context.update(extra)
    return render(request, template, context)


def register(request):
    if request.user.is_authenticated:
        return redirect("feed")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome to CONNECTLY. Your account is ready.")
        return redirect("feed")
    return render(request, "social/register.html", {"form": form})


@login_required
def logout_view(request):
    if request.method != "POST":
        return redirect("feed")
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("login")


@login_required
def feed(request):
    followed_ids = request.user.following.values_list("following_id", flat=True)
    posts = _post_queryset().filter(
        Q(author=request.user) | Q(author_id__in=followed_ids)
    )
    return _render_posts(request, "social/feed.html", posts, page_title="Your feed")


@login_required
def explore(request):
    posts = _post_queryset()
    return _render_posts(
        request, "social/feed.html", posts, page_title="Explore", is_explore=True
    )


@login_required
def create_post(request):
    form = PostForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        messages.success(request, "Your post is live.")
        return redirect("feed")
    return render(request, "social/post_form.html", {"form": form, "is_create": True})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id, author=request.user)
    form = PostForm(request.POST or None, request.FILES or None, instance=post)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your post has been updated.")
        return redirect("profile", username=request.user.username)
    return render(
        request,
        "social/post_form.html",
        {"form": form, "is_create": False, "post": post},
    )


@login_required
def delete_post(request, post_id):
    if request.method != "POST":
        return redirect("feed")
    post = get_object_or_404(Post, pk=post_id, author=request.user)
    post.delete()
    messages.success(request, "Your post has been deleted.")
    return redirect("profile", username=request.user.username)


@login_required
def toggle_like(request, post_id):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST to like a post."}, status=405)
    post = get_object_or_404(Post.objects.select_related("author"), pk=post_id)
    like, created = Like.objects.get_or_create(post=post, user=request.user)
    if created:
        if post.author_id != request.user.pk:
            Notification.objects.create(
                recipient=post.author,
                actor=request.user,
                post=post,
                notification_type=Notification.LIKE,
            )
        liked = True
    else:
        like.delete()
        liked = False
    if _is_ajax(request):
        return JsonResponse(
            {"liked": liked, "likes_count": post.likes.count(), "post_id": post.pk}
        )
    return _safe_return_to(request)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post.objects.select_related("author"), pk=post_id)
    if request.method != "POST":
        return JsonResponse({"error": "Use POST to add a comment."}, status=405)
    form = CommentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        if post.author_id != request.user.pk:
            Notification.objects.create(
                recipient=post.author,
                actor=request.user,
                post=post,
                notification_type=Notification.COMMENT,
            )
        if _is_ajax(request):
            return JsonResponse(
                {
                    "id": comment.pk,
                    "author": comment.author.profile.full_name
                    or comment.author.username,
                    "username": comment.author.username,
                    "body": comment.body,
                    "comments_count": post.comments.count(),
                },
                status=201,
            )
        messages.success(request, "Your comment has been added.")
        return _safe_return_to(request)
    if _is_ajax(request):
        return JsonResponse({"errors": form.errors.get("body", ["Enter a comment."])}, status=400)
    messages.error(request, "Please enter a comment of up to 500 characters.")
    return redirect(request.META.get("HTTP_REFERER", "feed"))


@login_required
def delete_comment(request, comment_id):
    if request.method != "POST":
        return redirect("feed")
    comment = get_object_or_404(Comment, pk=comment_id, author=request.user)
    comment.delete()
    messages.success(request, "Your comment has been deleted.")
    return _safe_return_to(request)


@login_required
def profile(request, username):
    person = get_object_or_404(User.objects.select_related("profile"), username=username)
    posts = _post_queryset().filter(author=person)
    return _render_posts(
        request,
        "social/profile.html",
        posts,
        person=person,
        is_following=Follow.objects.filter(follower=request.user, following=person).exists(),
    )


@login_required
def _follow_list(request, username, relation):
    person = get_object_or_404(User.objects.select_related("profile"), username=username)
    if relation == "followers":
        people = User.objects.filter(following__following=person).select_related("profile")
    else:
        people = User.objects.filter(followers__follower=person).select_related("profile")
    return render(
        request,
        "social/user_list.html",
        {
            "person": person,
            "people": people,
            "list_type": relation,
            "followed_ids": set(
                request.user.following.values_list("following_id", flat=True)
            ),
        },
    )


def followers(request, username):
    return _follow_list(request, username, "followers")


def following(request, username):
    return _follow_list(request, username, "following")


@login_required
def toggle_follow(request, username):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST to follow a user."}, status=405)
    person = get_object_or_404(User, username=username)
    if person.pk == request.user.pk:
        return JsonResponse({"error": "You cannot follow yourself."}, status=400)
    follow = Follow.objects.filter(follower=request.user, following=person)
    if follow.exists():
        follow.delete()
        is_following = False
    else:
        Follow.objects.create(follower=request.user, following=person)
        is_following = True
        Notification.objects.create(
            recipient=person,
            actor=request.user,
            notification_type=Notification.FOLLOW,
        )
    followers_count = person.followers.count()
    if _is_ajax(request):
        return JsonResponse(
            {
                "following": is_following,
                "followers_count": followers_count,
                "username": person.username,
            }
        )
    return redirect("profile", username=person.username)


@login_required
def edit_profile(request):
    form = ProfileForm(
        request.POST or None, request.FILES or None, instance=request.user.profile
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("profile", username=request.user.username)
    return render(request, "social/edit_profile.html", {"form": form})


@login_required
def search(request):
    query = request.GET.get("q", "").strip()
    people = User.objects.none()
    if query:
        people = (
            User.objects.filter(
                Q(username__icontains=query) | Q(profile__full_name__icontains=query)
            )
            .exclude(pk=request.user.pk)
            .select_related("profile")
            .distinct()[:30]
        )
    followed_ids = set(request.user.following.values_list("following_id", flat=True))
    return render(
        request,
        "social/search.html",
        {"query": query, "people": people, "followed_ids": followed_ids},
    )


@login_required
def notifications(request):
    items = request.user.notifications.select_related("actor", "actor__profile", "post")
    unread_count = request.user.notifications.filter(is_read=False).count()
    return render(
        request,
        "social/notifications.html",
        {"notifications": items[:50], "unread_count": unread_count},
    )


@login_required
def mark_notifications_read(request):
    if request.method == "POST":
        request.user.notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, "Notifications marked as read.")
    return redirect("notifications")
