from pathlib import Path

from django.contrib.contenttypes import migrations as django_migrations

__path__.append(str(Path(django_migrations.__file__).parent))
