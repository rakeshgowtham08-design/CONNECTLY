from io import BytesIO
import os
import tempfile

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from social.models import Comment, Follow, Like, Notification, Post

User = get_user_model()


def image_upload(name="tiny.png"):
    image = Image.new("RGB", (4, 4), color="purple")
    content = BytesIO()
    image.save(content, format="PNG")
    return SimpleUploadedFile(name, content.getvalue(), content_type="image/png")


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
)
class ConnectlyFlowTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.alex = User.objects.create_user(username="alex", password="StrongPass123!")
        self.sam = User.objects.create_user(username="sam", password="StrongPass123!")

    def test_registration_login_and_profile_edit(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "jules",
                "full_name": "Jules Rivera",
                "email": "jules@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertRedirects(response, reverse("feed"))
        jules = User.objects.get(username="jules")
        self.assertTrue(jules.check_password("StrongPass123!"))
        self.assertEqual(jules.profile.full_name, "Jules Rivera")
        self.client.post(reverse("logout"))
        self.assertRedirects(
            self.client.post(
                reverse("login"),
                {"username": "jules", "password": "StrongPass123!"},
            ),
            reverse("feed"),
        )
        self.client.post(
            reverse("edit_profile"),
            {
                "full_name": "Jules R.",
                "bio": "Finding the good in every day.",
                "image": image_upload("avatar.png"),
            },
        )
        jules.profile.refresh_from_db()
        self.assertEqual(jules.profile.full_name, "Jules R.")
        self.assertEqual(jules.profile.bio, "Finding the good in every day.")
        self.assertTrue(jules.profile.image.name.startswith("profiles/"))

    def test_post_upload_edit_delete_and_owner_permissions(self):
        self.client.force_login(self.alex)
        response = self.client.post(
            reverse("create_post"),
            {"caption": "A little sunshine", "image": image_upload()},
        )
        self.assertRedirects(response, reverse("feed"))
        post = Post.objects.get(author=self.alex)
        self.assertTrue(post.image.name.startswith("posts/"))
        self.assertContains(self.client.get(reverse("feed")), "A little sunshine")
        self.assertContains(self.client.get(reverse("explore")), "A little sunshine")
        self.client.post(
            reverse("create_post"), {"caption": "", "image": image_upload("photo.png")}
        )
        self.assertEqual(Post.objects.filter(author=self.alex).count(), 2)
        self.assertEqual(
            self.client.get(reverse("edit_post", args=[post.pk])).status_code, 200
        )
        self.client.force_login(self.sam)
        self.assertEqual(
            self.client.get(reverse("edit_post", args=[post.pk])).status_code, 404
        )
        self.assertEqual(
            self.client.post(reverse("delete_post", args=[post.pk])).status_code, 404
        )
        self.client.force_login(self.alex)
        self.client.post(
            reverse("edit_post", args=[post.pk]), {"caption": "Updated sunshine"}
        )
        post.refresh_from_db()
        self.assertEqual(post.caption, "Updated sunshine")
        self.client.post(reverse("delete_post", args=[post.pk]))
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_comments_permissions_and_notifications(self):
        post = Post.objects.create(author=self.alex, caption="Hello world")
        self.client.force_login(self.sam)
        response = self.client.post(
            reverse("add_comment", args=[post.pk]),
            {"body": "This made my day"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["comments_count"], 1)
        comment = Comment.objects.get(post=post)
        self.assertEqual(
            Notification.objects.get(recipient=self.alex).notification_type,
            Notification.COMMENT,
        )
        self.client.force_login(self.alex)
        self.assertEqual(
            self.client.post(
                reverse("delete_comment", args=[comment.pk])
            ).status_code,
            404,
        )
        self.client.force_login(self.sam)
        self.client.post(reverse("delete_comment", args=[comment.pk]))
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())
        self.client.force_login(self.alex)
        self.assertContains(self.client.get(reverse("notifications")), "commented")
        self.client.post(reverse("mark_notifications_read"))
        self.assertEqual(self.alex.notifications.filter(is_read=False).count(), 0)

    def test_like_unlike_is_unique_and_notifies(self):
        post = Post.objects.create(author=self.alex, caption="Like this")
        self.client.force_login(self.sam)
        like_url = reverse("toggle_like", args=[post.pk])
        first = self.client.post(like_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        second = self.client.post(like_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTrue(first.json()["liked"])
        self.assertFalse(second.json()["liked"])
        self.assertEqual(Like.objects.filter(post=post, user=self.sam).count(), 0)
        self.client.post(like_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(Like.objects.filter(post=post, user=self.sam).count(), 1)
        self.assertEqual(
            self.alex.notifications.filter(notification_type=Notification.LIKE).count(),
            2,
        )

    def test_follow_profile_lists_search_and_feed(self):
        post = Post.objects.create(author=self.alex, caption="A bright new day")
        self.client.force_login(self.sam)
        follow_url = reverse("toggle_follow", args=[self.alex.username])
        followed = self.client.post(follow_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTrue(followed.json()["following"])
        self.assertEqual(Follow.objects.filter(follower=self.sam, following=self.alex).count(), 1)
        self.assertEqual(
            self.client.get(reverse("followers", args=[self.alex.username])).context["people"].get(),
            self.sam,
        )
        self.assertContains(self.client.get(reverse("following", args=[self.sam.username])), "alex")
        self.assertContains(self.client.get(reverse("search") + "?q=alex"), "@alex")
        self.assertContains(self.client.get(reverse("feed")), "A bright new day")
        self.assertContains(self.client.get(reverse("explore")), "A bright new day")
        self.assertEqual(
            self.client.post(
                reverse("toggle_follow", args=[self.sam.username]),
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            ).status_code,
            400,
        )
        self.client.post(follow_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertFalse(Follow.objects.filter(follower=self.sam, following=self.alex).exists())
        with self.assertRaises(ValidationError):
            Follow.objects.create(follower=self.sam, following=self.sam)

    def test_upload_size_validation_and_protected_pages(self):
        self.client.force_login(self.sam)
        image = Image.frombytes("RGB", (1400, 1400), os.urandom(1400 * 1400 * 3))
        content = BytesIO()
        image.save(content, format="PNG")
        self.assertGreater(len(content.getvalue()), 5 * 1024 * 1024)
        oversized = SimpleUploadedFile(
            "large.png", content.getvalue(), content_type="image/png"
        )
        response = self.client.post(
            reverse("create_post"), {"caption": "Too large", "image": oversized}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "5 MB or smaller")
        self.client.logout()
        self.assertRedirects(
            self.client.get(reverse("create_post")),
            f"{reverse('login')}?next={reverse('create_post')}",
        )
