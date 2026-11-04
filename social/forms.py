from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from social.models import Comment, Post, Profile

User = get_user_model()


class RegisterForm(UserCreationForm):
    email = forms.EmailField()
    full_name = forms.CharField(max_length=100, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "full_name", "email")

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.profile.full_name = self.cleaned_data["full_name"].strip()
            user.profile.save()
        return user


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("caption", "image")
        widgets = {
            "caption": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "What would you like to share?",
                    "maxlength": 2000,
                }
            )
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Images must be 5 MB or smaller.")
        return image

    def clean_caption(self):
        return (self.cleaned_data.get("caption") or "").strip()

    def clean(self):
        cleaned_data = super().clean()
        if (
            not cleaned_data.get("caption")
            and not cleaned_data.get("image")
            and not self.instance.image
        ):
            raise forms.ValidationError("Add some text or choose an image.")
        return cleaned_data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        widgets = {
            "body": forms.TextInput(
                attrs={"placeholder": "Add a thoughtful comment…", "maxlength": 500}
            )
        }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("full_name", "bio", "image")
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Your full name"}),
            "bio": forms.Textarea(
                attrs={
                    "rows": 4,
                    "maxlength": 240,
                    "placeholder": "A little about you…",
                }
            ),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Profile photos must be 5 MB or smaller.")
        return image
