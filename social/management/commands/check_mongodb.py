from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from pymongo.errors import PyMongoError

from connectly.database import check_mongodb_connection


class Command(BaseCommand):
    help = "Check that the configured MongoDB database is reachable."

    def handle(self, *args, **options):
        connection = connections["default"]
        self.stdout.write(f"MONGODB_ENABLED: {settings.MONGODB_ENABLED}")
        self.stdout.write(f"DATABASE ENGINE: {connection.settings_dict['ENGINE']}")
        self.stdout.write(f"DATABASE NAME: {connection.settings_dict['NAME']}")
        self.stdout.write(f"MONGODB_URI configured: {bool(settings.MONGODB_URI)}")
        try:
            check_mongodb_connection()
        except ImproperlyConfigured as exc:
            raise CommandError(str(exc)) from exc
        except ConnectionError as exc:
            raise CommandError(str(exc)) from exc
        except PyMongoError as exc:
            raise CommandError(
                "MongoDB Atlas could not be reached. Check the MONGODB_URI and Atlas network access list."
            ) from exc
        self.stdout.write(self.style.SUCCESS("DATABASE CONNECTION SUCCESS: mongodb"))
