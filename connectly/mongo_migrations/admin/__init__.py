from pathlib import Path

from django.contrib.admin import migrations as django_migrations

__path__.append(str(Path(django_migrations.__file__).parent))
