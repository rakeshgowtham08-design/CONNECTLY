from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from pymongo.errors import PyMongoError


def check_mongodb_connection():
    connection = connections["default"]
    if connection.vendor != "mongodb":
        raise ImproperlyConfigured(
            "MongoDB is not configured. Set MONGODB_URI to use the Atlas backend."
        )
    try:
        connection.ensure_connection()
        connection.database.command("ping")
    except PyMongoError as exc:
        raise ConnectionError(
            "MongoDB Atlas could not be reached or rejected authentication. "
            "Check the MONGODB_URI credentials and Atlas network access list."
        ) from exc

