from django.conf import settings
from django.db import migrations
from django_mongodb_backend.fields import ObjectIdAutoField


class Migration(migrations.Migration):
    dependencies = [("social", "0002_alter_post_caption")]

    operations = (
        [
            migrations.AlterField(
                model_name=model_name,
                name="id",
                field=ObjectIdAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name="ID",
                ),
            )
            for model_name in (
                "comment",
                "follow",
                "like",
                "notification",
                "post",
                "profile",
            )
        ]
        if getattr(settings, "MONGODB_ENABLED", False)
        else []
    )
