from django.apps import AppConfig
from django.conf import settings


class SocialConfig(AppConfig):
    default_auto_field = (
        "django_mongodb_backend.fields.ObjectIdAutoField"
        if getattr(settings, "MONGODB_ENABLED", False)
        else "django.db.models.BigAutoField"
    )
    name = "social"

    def ready(self):
        import social.signals  # noqa: F401
