from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ImproperlyConfigured
from pymongo.errors import PyMongoError

from connectly.database import check_mongodb_connection


class Command(BaseCommand):
    help = "Check that the configured MongoDB database is reachable."

    def handle(self, *args, **options):
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
        self.stdout.write(self.style.SUCCESS("MongoDB connection and ping succeeded."))
