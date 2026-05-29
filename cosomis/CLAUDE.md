# CLAUDE.md — guidance for AI sessions in this repo

This file orients Claude (and humans) before touching the code. Skim it before
proposing changes. For local setup, see [README.md](./README.md). For change
history, see [CHANGELOG.md](./CHANGELOG.md).

## What this project is

A Django 4.1 web app for managing community-driven development data:
administrative hierarchies (country → … → village), investment proposals
("priorities"), funding packages, planning cycles, and per-canton/commune
profiles. Deployed against multiple country datasets — currently Togo and
Benin — that share schema but **not** vocabulary.

## Workspace layout

You'll usually be in `cosomis/` (the Django project root, where `manage.py`
lives). Anything above that is a thin GitLab-template shell.

```
cosomis/
├── administrativelevels/   # Hierarchy, search, profiles, maps
├── authentication/         # Login flows
├── cdd_funnel/             # CDD funnel views
├── cosomis/                # settings, root URLs, shared mixins/services
├── dashboard/
├── investments/            # Investments, packages, cart, moderator/investor
├── usermanager/            # Custom User + Organization
├── utils/
├── static/AdminLTE/        # Theme + plugins (Bootstrap 4 era)
├── locale/{en,fr}/         # i18n catalogs
├── templates/layouts/      # base/head/navbar/sidebar
└── requirements.txt
```

## Stack quick reference

- **Django 4.1.1** — pinned for the rest of the stack; do not bump casually.
- **Python 3.11** — the only interpreter the pinned `numpy==1.23.3` /
  `pandas==1.5.0` build for. 3.12/3.13 fail.
- **PostgreSQL 16** in production; SQLite locally if `env=dev`. The dev dump
  is custom-format and restores via `pg_restore` (see README).
- **Custom user model** `usermanager.User` (`AbstractUser` subclass) with
  `USERNAME_FIELD = "email"` — `createsuperuser` and `Client.login()` both
  take `email=...`, not `username=...`.
- **Frontend** is jQuery + Bootstrap 4 + AdminLTE + select2 + DataTables.
  Newer code mixes in **HTMX** (`django_htmx` in `INSTALLED_APPS`,
  `HtmxMiddleware` in `MIDDLEWARE`) — prefer it for new fragment-swap UX over
  hand-rolled jQuery `$.ajax`.
- **i18n** is mandatory: every user-facing string goes through `{% translate %}`
  / `gettext_lazy` / `blocktranslate`. URLs are language-prefixed (`/en/…`,
  `/fr/…`). Run `make generate-translations` after adding strings.

## Conventions that bite if you ignore them

### 1. Administrative-level `type` strings are dataset-specific

`AdministrativeLevel.type` is **not** a fixed vocabulary. Each country dump
labels the same logical level differently:

| Depth | Togo seed | Benin dump |
| --- | --- | --- |
| Root (0) | `Region` | `country` |
| 1 | `Prefecture` | `département` |
| 2 | `Commune` | `commune` |
| 3 | `Canton` | `arrondissement` |
| Leaf (4) | `Village` | `village` |

Casing differs too (`Village` vs `village`). The model exposes the right
primitives — **use them, never hard-code a literal**:

- `AdministrativeLevel.matches_type(stored, canonical)` — case-insensitive,
  alias-aware boolean test.
- `AdministrativeLevel.type_filter_q(canonical, field="type")` — `Q()`
  expression for ORM filters that matches every alias.
- `AdministrativeLevel.aliases_for(canonical)` — raw alias tuple.
- `is_village()`, `is_canton()`, `is_commune()`, `is_prefecture()`,
  `is_region()` — instance helpers.
- `AdministrativeLevel.get_hierarchy_labels()` — returns the dataset's own
  level names root-first, for UI labels.
- `TYPE_ALIASES` (on the model) — the canonical alias map; extend here when
  onboarding a new country.

For things that aren't a "which type is this" question but a "which level
is this in the hierarchy", **prefer position-based logic** (walk parents to
get depth, then map to one of the five fixed routes). The breadcrumb tag
and the summary-card detail-URL resolver both do this.

**Past incidents** caused by hard-coded type strings, all fixed:

- `adm_breadcrumb` rendered every ancestor as plain text on Benin because
  `url_map.get(item.type)` missed (`'Village'` vs `'village'`,
  `'Canton'` vs `'arrondissement'`).
- `AdministrativeLevelSearchListView.get_queryset` filtered `type='Village'`
  and returned zero rows on Benin.
- `VillageSearchForm.region` queryset was empty for the same reason.
- `CantonSummaryService.__init__` still asserts
  `canton.type == AdministrativeLevel.CANTON`. There is a follow-up task
  open for this — see git log around `claude/eager-kare-0ed0de`.

### 2. `.env` lives at `cosomis/cosomis/.env`

`settings.py` calls `env.read_env()` with no args; `django-environ` resolves
the path relative to the file calling it, so the `.env` must sit **next to
`settings.py`**, not at the project root. The repo `.gitignore` covers both
locations.

### 3. The investments page uses server-side DataTables

`/investments/` builds a DataTable in JS using `datatable_config` from the
view, with `serverSide: true` and AJAX-loaded totals. Two totals AJAX calls
fire on load (`init_total_values`, `sum_subprojects`); both now paint
skeleton placeholders in `beforeSend` rather than leaving stale `0`s on
screen. If you add metrics, follow the same pattern (skeleton in
`beforeSend`, real value in `success`, `—` in `error`).

### 4. Don't write multi-line `{# ... #}` template comments

Django only supports single-line `{# ... #}`. Use `{% comment %}…{% endcomment %}`
for anything longer. (Multi-line `{# ... #}` renders as literal text in the
output, which already shipped to a user once.)

### 5. Custom user model is email-keyed

```python
User.objects.create_superuser(email="x@y.com", username="x", password="…")
# In tests: Client().login(email="x@y.com", password="…")
```

## How work usually ships

- `develop2` is the shared integration branch — most feature PRs merge there.
- Branch from `develop2`, prefix with `claude/` (Claude work) or `feature/`
  (human work), open the PR back to `develop2`.
- Commits use Conventional Commits style: `feat(scope): …`, `fix(scope): …`,
  `i18n: …`, etc. See `git log` for examples.

## External integrations to know about (mostly stubbed locally)

`settings.py` reads many env vars with no defaults — locally these point at
`example.invalid` / placeholders and the calling code swallows the resulting
exceptions:

- **Mapbox** (`MAPBOX_ACCESS_TOKEN`) — maps fall back gracefully if blank.
- **CouchDB** (`NO_SQL_*`) — only hit by some NoSQL views.
- **S3** (`S3_*`) — `DEFAULT_FILE_STORAGE` is S3-backed; locally uploads
  will fail. Most flows don't touch uploads.
- **Mixpanel** (`MIXPANEL_*`) — `Error tracking event: Mixpanel error: $token,
  missing or empty` in logs is benign.
- **GRM** (`GRM_*`) — the administrative-level detail view tries to fetch
  complaints; expect `Error fetching data from GRM API: …` in the log.
- **MIS** (`MIS_*`) — similar.

These shouldn't block local development; if your task needs one of them, set
the corresponding env var.

## Testing the UI

There is no headless E2E suite wired up for this app. After a change, hit the
affected page with `Client().login(email=…)` + `c.get(…)` from
`manage.py shell` to confirm status codes and rendered fragments. For browser
verification, use the dev server and check the actual page — type-coupling
bugs surface only against a real dataset.

## When you're unsure

- Read the model first — many methods (`is_village()`, `get_villages_coordinates()`,
  `get_all_descendants()`, `type_filter_q()`) already exist.
- Check `administrativelevels/templatetags/custom_tags.py` for existing
  template-tag patterns before adding a new one.
- Default to **position in hierarchy** over **type string** for any logic
  that conceptually means "what level is this".