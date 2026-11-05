from django.conf import settings
from django.db import migrations
from django_mongodb_backend.fields import ObjectIdAutoField


class Migration(migrations.Migration):
    dependencies = [("admin", "0003_logentry_add_action_flag_choices")]

    operations = (
        [
            migrations.AlterField(
                model_name="logentry",
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
