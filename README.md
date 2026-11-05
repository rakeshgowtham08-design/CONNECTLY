# CONNECTLY

CONNECTLY is a Django social app with a server-rendered HTML frontend, CSS and vanilla JavaScript. It uses MongoDB Atlas through MongoDB's official Django MongoDB Backend when `MONGODB_URI` is set. Without that setting, local development and the test suite continue to use SQLite.

## Database support and feature compatibility

- Django 5.2 is paired with the official `django-mongodb-backend` 5.2 series and PyMongo.
- MongoDB uses ObjectId primary keys. Social model foreign keys, Django authentication, sessions, and admin remain Django ORM models.
- MongoDB enforces supported unique indexes such as unique usernames, likes, and follows. The backend does not enforce Django check constraints, so self-following is also rejected by the Follow model and view.
- Django aggregation and cross-collection `$lookup` queries are supported with limitations and may be slower than SQL. Check feed/profile/count queries on the Atlas deployment with representative data.
- The app uses Django's built-in authentication and session models; run the full smoke tests against Atlas before switching production traffic.

## MongoDB Atlas setup

1. Create an Atlas database user with a strong password and access limited to the required database.
2. In Atlas Network Access, allow the IPs that need access. For local testing, add your current public IP. For Render, use Render's documented outbound IP ranges where available. `0.0.0.0/0` allows access from any IP and should only be a temporary troubleshooting measure.
3. Copy the Atlas `mongodb+srv://` URI, replace its username/password placeholders, and URL-encode any reserved characters in credentials.
4. Put the URI in the ignored local `.env` file as `MONGODB_URI=...`. Never commit `.env` or paste a credential into source code.
5. Set `MONGODB_DATABASE=connectly`.
6. Confirm access without printing the URI:

   ```bash
   .venv-mongo/bin/python manage.py check
   .venv-mongo/bin/python manage.py check_mongodb
   ```

`check_mongodb` issues a ping and reports errors without printing the connection string. A connection error usually means the Atlas username/password or network access list needs attention.

## Local development

Use the existing Python 3.12 virtual environment:

```bash
cd "social media platform"
source .venv-mongo/bin/activate
python -m pip install -r requirements.txt
python manage.py runserver
```

For SQLite-only local tests or fallback development, explicitly unset the Mongo setting for that process:

```bash
MONGODB_URI= .venv-mongo/bin/python manage.py test
```

To run tests against Atlas, configure a dedicated test database/cluster. Django's MongoDB backend creates and drops a test database during test runs; do not point this at a production database.

## Existing SQLite data migration

The migration does not delete or modify the SQLite database. Keep `db.sqlite3`, `db.sqlite3.backup`, `db_before_mongodb.sqlite3`, and the local `media/` directory until the Mongo import and verification are complete.

1. Back up the source database and media files to a private, access-controlled location. The existing ignored backups are additional rollback copies, not a substitute for an off-machine backup.
2. With the source SQLite database active, export all Django records to a private fixture:

   ```bash
   MONGODB_URI= .venv-mongo/bin/python manage.py dumpdata --all --indent 2 --output connectly-sqlite.fixture.json
   chmod 600 connectly-sqlite.fixture.json
   ```

   The export contains password hashes and user data. It is git-ignored; do not upload it to a public repository or share it.
3. Configure a valid Atlas URI and `MONGODB_DATABASE=connectly`. Confirm `check_mongodb` succeeds, then create MongoDB collections and indexes:

   ```bash
   .venv-mongo/bin/python manage.py migrate
   ```
4. Import without deleting existing Atlas records:

   ```bash
   .venv-mongo/bin/python manage.py import_sqlite_fixture connectly-sqlite.fixture.json
   ```

   The importer makes stable ObjectId values from each source model/primary-key pair, rewrites Django foreign-key and many-to-many references, skips already-imported IDs, and leaves passwords hashed. It is safe to resume after a partial run. Import into a new/empty `connectly` database: existing records with conflicting unique usernames/emails can stop the import and must be reconciled before retry.
5. Verify user/profile/post/comment/like/follow/notification counts and representative account login in a private staging deployment. Check image paths and media separately.
6. Only after verification, remove the private fixture securely. Keep the SQLite and media backups until rollback is no longer needed.

To roll back the application, switch `MONGODB_URI` off and restore the preserved SQL `DATABASE_URL` (or SQLite database) and matching media backup. The MongoDB import does not modify the source SQL files.

## Image storage

Render's local filesystem is ephemeral. For durable uploads, configure an S3-compatible bucket (AWS S3 or another compatible service) and these private environment values:

- `AWS_STORAGE_BUCKET_NAME`
- `AWS_S3_REGION_NAME`
- AWS credentials (`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`) or an appropriate role/identity provider
- Optionally `AWS_S3_ENDPOINT_URL` for an S3-compatible provider

When a bucket name is configured, Django stores new uploads in S3. Copy existing `media/` contents to the bucket before deployment, preserving paths such as `profiles/...`. Without a bucket configuration, uploads stay on the local filesystem and are not durable on Render.

## Render deployment

Build command:

```bash
./build.sh
```

Start command:

```bash
gunicorn connectly.wsgi
```

Set these in the Render service's Environment dashboard, not in `render.yaml` or Git:

```text
DJANGO_SECRET_KEY=<long-random-private-value>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<your-service>.onrender.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://<your-service>.onrender.com
MONGODB_URI=<Atlas mongodb+srv connection string>
MONGODB_DATABASE=connectly
```

Render's external hostname is also added to `ALLOWED_HOSTS` and CSRF trusted origins automatically. The Atlas user must have appropriate database permissions and Atlas network access must permit Render's outbound traffic. Do not enable public access broadly for routine deployment.

For durable media, also set the S3 variables above. `build.sh` installs dependencies, collects static files, and runs migrations. Verify the Render build logs and then run `check_mongodb` from a one-off shell or deploy check; verify registration, login, CRUD, and media on the deployed URL.

## Checks and tests

```bash
.venv-mongo/bin/python manage.py check
MONGODB_URI= .venv-mongo/bin/python manage.py test
node --check js/app.js
```

Run `check_mongodb` and the feature smoke tests against a dedicated Atlas test database before considering the Mongo migration verified. Do not use a production Atlas database as a test database.

## Git safety

The ignore rules exclude local `.env` files, virtual environments, SQLite databases/backups, uploaded media, and the temporary export fixture. Review `git status --short` before committing. Never commit database dumps, media, or credentials.
