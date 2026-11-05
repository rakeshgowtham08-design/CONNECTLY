import hashlib
import json
from pathlib import Path

from bson import ObjectId
from django.core.exceptions import ValidationError
from django.core import serializers
from django.core.serializers.base import DeserializationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError
from pymongo.errors import PyMongoError


def _stable_object_id(model_label, old_pk):
    digest = hashlib.sha256(f"{model_label}:{old_pk}".encode("utf-8")).hexdigest()
    return str(ObjectId(digest[:24]))


class Command(BaseCommand):
    help = (
        "Import a private dumpdata JSON fixture from SQLite, remapping integer "
        "primary and relationship keys to MongoDB ObjectIds."
    )

    def add_arguments(self, parser):
        parser.add_argument("fixture", type=Path)

    def handle(self, *args, **options):
        from django.apps import apps
        from django.db import connections

        if connections["default"].vendor != "mongodb":
            raise CommandError("The default database must be MongoDB.")

        fixture_path = options["fixture"]
        try:
            records = json.loads(fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CommandError("Could not read a valid JSON fixture file.") from exc
        if not isinstance(records, list):
            raise CommandError("The fixture must contain a JSON list of model records.")
        if any(
            not isinstance(record, dict)
            or not {"model", "pk", "fields"} <= record.keys()
            or not isinstance(record["model"], str)
            or not isinstance(record["fields"], dict)
            for record in records
        ):
            raise CommandError("The fixture contains an invalid model record.")

        models_by_label = {}
        object_id_map = {}
        content_type_map = {}
        log_entry_content_types = {}
        for record in records:
            if record["model"].lower() == "contenttypes.contenttype":
                fields = record["fields"]
                content_type_map[str(record["pk"])] = (
                    fields["app_label"],
                    fields["model"],
                )
            elif record["model"].lower() == "admin.logentry":
                log_entry_content_types[str(record["pk"])] = record["fields"].get(
                    "content_type"
                )

        for record in records:
            label = record["model"].lower()
            try:
                model = apps.get_model(label)
            except (LookupError, ValueError) as exc:
                raise CommandError(f"Unknown model label in fixture: {label}.") from exc
            models_by_label[label] = model
            if model._meta.pk.get_internal_type() == "ObjectIdAutoField":
                object_id_map[(label, str(record["pk"]))] = _stable_object_id(
                    label, record["pk"]
                )

        transformed = []
        for record in records:
            label = record["model"].lower()
            model = models_by_label[label]
            old_pk = record["pk"]
            if (label, str(old_pk)) in object_id_map:
                record["pk"] = object_id_map[(label, str(old_pk))]

            for field in model._meta.concrete_fields:
                if not field.is_relation:
                    continue
                field_name = field.name
                if field_name not in record["fields"] or record["fields"][field_name] is None:
                    continue
                related_label = field.remote_field.model._meta.label_lower
                mapped = object_id_map.get(
                    (related_label, str(record["fields"][field_name]))
                )
                if mapped is not None:
                    record["fields"][field_name] = mapped

            if label == "admin.logentry":
                content_type = content_type_map.get(
                    str(log_entry_content_types.get(str(old_pk), ""))
                )
                if content_type and record["fields"].get("object_id"):
                    related_label = ".".join(content_type)
                    mapped = object_id_map.get(
                        (related_label, str(record["fields"]["object_id"]))
                    )
                    if mapped is not None:
                        record["fields"]["object_id"] = mapped

            for field in model._meta.many_to_many:
                field_name = field.name
                if field_name not in record["fields"]:
                    continue
                related_label = field.remote_field.model._meta.label_lower
                record["fields"][field_name] = [
                    object_id_map.get((related_label, str(value)), value)
                    for value in record["fields"][field_name]
                ]
            transformed.append(record)

        objects = []
        try:
            for obj in serializers.deserialize(
                "json", json.dumps(transformed), ignorenonexistent=False
            ):
                objects.append(obj)
        except (DeserializationError, TypeError, ValueError, KeyError) as exc:
            raise CommandError(
                "The fixture could not be converted for this MongoDB schema. "
                "No records were imported."
            ) from exc

        created = 0
        skipped = 0
        for obj in objects:
            model = obj.object.__class__
            manager = model._base_manager.using("default")
            if manager.filter(pk=obj.object.pk).exists():
                skipped += 1
                continue
            try:
                obj.save(using="default", save_m2m=False, force_insert=True)
            except (DatabaseError, PyMongoError, ValidationError, ValueError) as exc:
                raise CommandError(
                    "Import stopped while writing a record. Existing source "
                    "SQLite backups remain unchanged; inspect the target database "
                    "before retrying."
                ) from exc
            created += 1

        for obj in objects:
            if not obj.m2m_data:
                continue
            try:
                for accessor_name, object_list in obj.m2m_data.items():
                    getattr(obj.object, accessor_name).set(object_list)
            except (DatabaseError, PyMongoError, ValidationError, ValueError) as exc:
                raise CommandError(
                    "Import stopped while restoring many-to-many relations. "
                    "The deterministic ID mapping allows a safe retry."
                ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Fixture import finished: {created} inserted, {skipped} already present."
            )
        )
