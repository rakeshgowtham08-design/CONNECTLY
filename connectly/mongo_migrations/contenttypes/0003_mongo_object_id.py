from django.conf import settings
from django.db import migrations
from django_mongodb_backend.fields import ObjectIdAutoField


class Migration(migrations.Migration):
    dependencies = [("contenttypes", "0002_remove_content_type_name")]

    operations = (
        [
            migrations.AlterField(
                model_name="contenttype",
                name="id",
                field=ObjectIdAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name="ID",
                ),
            )
        ]
        if getattr(settings, "MONGODB_ENABLED", False)
        else []
    )
