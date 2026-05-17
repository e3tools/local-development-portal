# COSOMIS — Local Development Portal

Django application for managing community-driven development data (administrative levels, investments, planning cycles) across multiple country datasets (Togo, Benin, …).

## Quick start

### 1. Install dependencies

The pinned versions (`Django 4.1.1`, `numpy==1.23.3`, `pandas==1.5.0`, etc.) only have wheels for **Python 3.11**. Newer interpreters fail to build numpy from source.

```bash
/opt/homebrew/opt/python@3.11/bin/python3.11 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

### 2. Configure environment

Create `cosomis/.env` (lives next to `settings.py`; `django-environ` looks there) — start from [`env.example`](./env.example) and set at minimum:

```
env=local
SECRET_KEY=local-dev-secret
DEBUG=True
ALLOWED_HOSTS=*
DATABASE_URL=postgres://admin:admin@localhost:5434/ldpdb
LEGACY_DATABASE_URL=postgres://admin:admin@localhost:5434/ldpdb
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
FRONTEND_URL_ROOT=http://127.0.0.1:8000
```

(Set `env=dev` to fall back to the bundled SQLite file instead of Postgres.)

### 3. Bring up Postgres + restore a dump

The project targets PostgreSQL 16. An isolated Docker container keeps it out of the way of any other Postgres you have running locally.

```bash
docker run -d \
  --name ldp-postgres \
  -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=admin -e POSTGRES_DB=ldpdb \
  -p 5434:5432 \
  -v ldp-postgres-data:/var/lib/postgresql/data \
  postgres:16

# Restore a custom-format dump (e.g. ldpdb11052026.dump)
docker exec -i ldp-postgres pg_restore \
  -U admin -d ldpdb \
  --no-owner --no-privileges --clean --if-exists \
  < ~/Downloads/ldpdb11052026.dump
```

### 4. Apply pending migrations and run the server

```bash
./venv/bin/python manage.py migrate
./venv/bin/python manage.py runserver
# or equivalently:
make server
```

Open <http://127.0.0.1:8000/>. The site uses `django-modeltranslation`-style URLs prefixed with `/en/` or `/fr/`.

### 5. Create a local superuser

The custom user model uses `email` as `USERNAME_FIELD`:

```bash
./venv/bin/python manage.py shell -c "
from usermanager.models import User
u = User.objects.create_superuser(email='you@local.dev', username='you', password='change-me')
print(u)
"
```

## Common commands

| Task | Command |
| --- | --- |
| Run the dev server (migrate first) | `make server` |
| Update Python deps | `make pip-install` |
| Regenerate `.po`/`.mo` files | `make generate-translations` |
| Format Python with Black | `make black` |

## Project layout

```
cosomis/                  # Django project root (manage.py lives here)
├── administrativelevels/ # Country/region/village hierarchy, search, profiles, maps
├── authentication/       # Auth flows
├── cdd_funnel/           # Community-Driven Development funnel views
├── cosomis/              # Project settings, root URLs, shared mixins/services
├── dashboard/            # Dashboard views
├── investments/          # Investments, packages, cart, moderator/investor flows
├── usermanager/          # Custom User + Organization
├── utils/                # Cross-app utilities
├── static/               # AdminLTE + project static assets
├── locale/               # i18n catalogs (en/fr)
└── requirements.txt
```

## Notes

- Administrative-level type strings are **dataset-specific** (`Village/Canton/Commune/Prefecture/Region` on the Togo seed; `village/arrondissement/commune/département/country` on the Benin dump). Code must go through `AdministrativeLevel.matches_type()`, `type_filter_q()`, or position-based logic (depth in the hierarchy) — never hard-code a type literal. See [`CLAUDE.md`](./CLAUDE.md) for the full guidance.
- See [`CHANGELOG.md`](./CHANGELOG.md) for the change history.
