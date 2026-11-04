# CONNECTLY

A responsive mini social network built with Django, SQLite, server-rendered HTML templates, CSS, and vanilla JavaScript.

## Requirements

- Python 3.9 or newer
- pip

## Run locally

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. Django creates the SQLite database at `db.sqlite3` and serves uploaded media during local development.

To use environment variables, copy `.env.example` to `.env` and export its values in your shell before starting Django. The checked-in development key is for local use only; set a private `DJANGO_SECRET_KEY` and turn `DJANGO_DEBUG=0` for deployment.

## Features

- Username/password registration, login, logout, hashed passwords, and protected social pages
- Profiles with a photo, full name, bio, follower/following totals, and authored posts
- Text and image posts with preview, edit/delete ownership checks, and newest-first ordering
- Unique likes, comments, comment deletion, follow/unfollow, and activity notifications
- Personalized feed from followed accounts, public Explore feed, and user search by username/name
- Responsive desktop side rails and compact mobile navigation
- CSRF-protected forms and asynchronous like, follow, and comment interactions

## Test and checks

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The test suite covers registration and login, profile editing, uploads and size validation, post ownership, comments, likes, follows, search, feed visibility, notification state, and protected routes.
