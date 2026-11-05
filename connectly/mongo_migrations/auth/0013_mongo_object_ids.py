from django.conf import settings
from django.db import migrations, models
from django_mongodb_backend.fields import ObjectIdAutoField


class Migration(migrations.Migration):
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]

    operations = (
        [
            migrations.AlterField(
                model_name="group",
                name="id",
                field=ObjectIdAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name="ID",
                ),
            ),
            migrations.AlterField(
                model_name="permission",
                name="id",
                field=ObjectIdAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name="ID",
                ),
            ),
            migrations.AlterField(
                model_name="user",
                name="id",
                field=ObjectIdAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name="ID",
                ),
            ),
        ]
        if getattr(settings, "MONGODB_ENABLED", False)
        else []
    )
