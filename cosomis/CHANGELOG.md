# Changelog

All notable user-visible and developer-facing changes are tracked here. The
format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased] — 2026-10-29 (performance & security)

### Security

- **`/investments/ajax/datatable/` allowed anonymous writes.**
  `InvestmentModelViewSet` was a full `ModelViewSet` with DRF's default
  `AllowAny` (no `DEFAULT_PERMISSION_CLASSES`): anyone, logged in or not,
  could list, create, update and **delete** investments (verified: anonymous
  `DELETE` → 204). Now a `ReadOnlyModelViewSet` restricted to approved users
  (`usermanager.permissions.IsApprovedUser`, the DRF twin of
  `LoginRequiredApproveRequiredMixin`); the `adm-levels`/`sectors` cascade
  endpoints get the same permission.

### Changed

- **Mixpanel no longer blocks requests.** Each call took ~0.6s from the prod
  VM and `PageMixin.dispatch` made two per page view (four when applying a
  filter: POST + redirected GET). Calls now go through a background thread
  with a bounded queue, a 2s timeout and no retries (library default: no
  timeout, 4 retries); nothing is sent when `MIXPANEL_TOKEN` is empty or
  the `test` placeholder; the user profile (`people_set`) is sent once per
  session; `PageMixin` tracks GET page views only (explicit business events
  such as `PackageSubmitted` are unchanged).
- **`/investments/` DataTable query** uses `.only()` on the rendered columns
  (Postgres sorted ~5KB rows across 5 joined tables, now ~270 bytes) and
  `InvestmentSerializer` lists its fields instead of `'__all__'`. Local
  median for a 10-row page: 56ms → 30ms.
- **Totals** (`results` / `total-results`) are computed in one `aggregate()`
  instead of three queries; the `results` call is skipped client-side when
  nothing is selected (always the case on page load).
- **Admin-level dropdowns** are only rendered when their parent is selected
  (the AJAX cascade fills them otherwise): page HTML 240KB → 109KB, 993 →
  45 `<option>` elements on the Benin dataset.
- Tests: `cosomis/tests/test_mixpanel_tracking.py`,
  `investments/tests/test_ajax_permissions.py`,
  `investments/tests/test_list_performance.py` (query-count guards).

## [Unreleased] — 2026-10-29

### Added

- **Multi-select on every remaining `/investments/` filter**, completing the
  category/sector work below:
  - **Funding status** (`is-funded-filter`): several states OR-ed
    (`project_status__in`), via `InvestmentModelViewSet.FUNDED_FILTER_STATUSES`.
  - **Endorsed by** (`subpopulation-filter`): "endorsed by at least one of the
    selected groups" (OR of `Q(endorsed_by_x=True)`). Today a BJ need is
    endorsed by exactly one group, but the query stays correct if that changes.
  - **Administrative levels** (prefecture → village; the root/region select
    stays single, it is hidden on Benin): ids within a level are OR-ed,
    levels are AND-ed (picking a commune narrows the selected departments to
    it). `FillAdmLevelsSelectFilters` returns the children of every selected
    parent; the page's pre-loaded dropdowns do the same.
- `getlist` template filter (`custom_tags.py`) — string counterpart of
  `getlist_int`, used to pre-select string-valued multi-selects.
- `investments/tests/test_list_filters.py` — first tests for the
  `/investments/` filters (queryset, cascade endpoint, template
  pre-selection, badges, `IndexListView.post()` merge). Replaces the empty
  `investments/tests.py` stub.

### Fixed

- **Clearing a multi-select did not remove its filter.** A `<select multiple>`
  with nothing selected submits nothing, so `IndexListView.post()` kept the
  old value from the URL (affected category/sector since 2026-10-08). Each
  multi-select is now preceded by `<input type="hidden" name="…" value="">`.
- **`subpopulation-filter` was passed straight to `.filter(**{value: True})`.**
  Now restricted to `SUBPOPULATION_FILTER_FIELDS`. `IndexListView.get_queryset()`
  held a dead copy of every filter (it ended in `.none()`) that still raised
  `FieldError` (HTTP 500) on an unknown value — reduced to `.none()`.
- **Filter badges** showed only the last value of multi-valued keys, showed
  the raw field name for "Endorsed by", and never showed admin-level badges
  on Benin (hard-coded Togo `type` strings). They now list every selected
  value, use `type_filter_q`, add the missing canton badge, and hide the root
  badge on single-root datasets.
- Village dropdown pre-load read the misspelt `cantons-filter` key and so
  always listed every village.

## [Unreleased] — 2026-10-08

### Added

- **New-needs sync pipeline (BJ).** Seven read-only management commands
  under `investments/management/commands/` (`extract_new_needs_bj` →
  `match_candidates_against_db_bj` → `match_candidates_against_excel_bj` →
  `apply_capacity_cap_bj` → `categorize_candidates_bj` → `build_review_file_bj`
  → `lock_in_resolved_needs_bj`) take a `synctasks` CouchDB sync and turn it
  into a single arbitrated Excel (`new_needs_review_bj.xlsx`) listing exactly
  which besoins are genuinely new vs. already in the DB under a renamed
  title. Only the eighth command, `import_new_needs_bj`, writes to the
  database — it is the only one meant to run in production, and only
  against the already-arbitrated review file. Full protocol, decision
  thresholds, and known limitations documented in
  `NEW_NEEDS_SYNC_PROTOCOL.md`.
- **`config_data/resolved_needs_bj.json` ledger.** Every besoin arbitrated by
  the pipeline above (whether created, already-in-DB, or excluded) is keyed
  by a stable `no_sql_id` (`<couchdb_doc_id>:<sub_component>:<ranking>`).
  `extract_new_needs_bj` consults it and skips anything already resolved, so
  a repeat `synctasks` sync never re-surfaces the same besoins for
  arbitration — this was the main point of building the ledger.
- **Multi-select on `/investments/`'s Sector/Category filter.** The
  `category-filter` and `sector-filter` `<select>` elements are now
  `multiple` (select2 already auto-initializes every `<select>` on the page
  via `base.html`, so no new JS library work was needed). Picking several
  categories unions their sectors in the cascading dropdown and filters the
  DataTable/totals on `sector__id__in=`/`sector__category__id__in=` instead
  of an exact match.
  **Admin-level filters (région → village) are NOT yet multi-select** — this
  was deliberately scoped to category/sector first. To extend: the pattern
  to replicate is `getlist_int` (new filter in
  `administrativelevels/templatetags/custom_tags.py`) for template
  pre-selection, `__in` filtering in `InvestmentModelViewSet.get_queryset()`
  (investments/ajax_views.py), a union-by-multiple-parents rewrite of
  `FillAdmLevelsSelectFilters` (ajax_views.py:20-47, mirrors the
  `FillSectorsSelectFilters` fix), and reading `select_input.val()` (not
  `.find(":selected").val()`) plus `traditional: true` on the `$.ajax` call
  in `change_adm_levels_selects` (investments/templates/investments/list.html)
  the same way `change_sectors_selects` was fixed. `IndexListView.post()`'s
  querystring merge (views.py) and the `selected_investments_data_querystring`
  build (views.py) already handle multi-valued keys generically — no further
  change needed there for the admin-level extension.

### Changed

- **`IndexListView.post()` (investments/views.py) rewritten.** The old
  GET/POST querystring-merge logic iterated `QueryDict.items()`, which only
  ever returns the *last* value for a multi-valued key — any multi-select
  filter would have been silently collapsed to one value on every filter
  submission. Rewritten to `setlist()` each submitted key's full value list
  against a copy of the existing GET querystring, correctly preserving
  filters from the page's *other* independent filter forms untouched.
- **`selected_investments_data_querystring`** (views.py) now built with
  `QueryDict.urlencode()` instead of a manual `.items()` join — same
  multi-value fix, needed so the DataTable's own ajax URL and the totals
  endpoints' URLs carry every selected category/sector id.
- **Gunicorn (`run.sh`)**: `--workers 4` alone → `--workers 4 --worker-class
  gthread --threads 4 --timeout 60`. The default 30s sync-worker timeout was
  the likely cause of the intermittent "DataTables warning: Ajax error" on
  `/investments/` reported in prod (see Fixed).
- **`DATABASES['default']['CONN_MAX_AGE'] = 60`** (cosomis/settings.py),
  hardcoded (not an env var, per team preference) — `/investments/` alone
  fires 3 near-simultaneous queries per page load, each previously opening a
  fresh DB connection.
- **`/investments/` DataTable no longer double-fetches on page load.**
  `list.html` used to let DataTables auto-fetch on init, then immediately
  mutate the ajax URL and call `table.ajax.reload()` to inject `project_id`
  — firing the heaviest query twice every time. `project_id` is now injected
  via an `ajax.data` callback instead, so the one automatic initial fetch
  already carries it.
- Reviewed `update_investment_estimated_costs_by_sector_bj` — it
  unconditionally overwrites `estimated_cost` for every `Investment`
  regardless of funded status. Confirmed with the user this is intentional
  (team wants costs uniformized by sector across funded and unfunded
  investments alike) — left as-is, not a bug.

### Fixed

- **`/investments/` DataTable column `administrative_level__type_with_...` (index 2) could 500.**
  It's wired as orderable but maps to a `SerializerMethodField`, not a real
  model field/relation — sorting by it raised an uncaught `FieldError`.
  Marked `'orderable': 'false'` in `investments/views.py`.
- Root-caused the intermittent prod "DataTables warning: Ajax error" on
  `/investments/` to gunicorn's default 30s timeout + 4 sync workers + no DB
  connection reuse, under the load of 3 near-simultaneous AJAX calls per
  page load (DataTable list + two totals POSTs). Addressed via the Gunicorn/
  `CONN_MAX_AGE`/double-fetch changes above; nginx-side `proxy_read_timeout`
  still to be confirmed against real VM logs (nginx config lives outside
  this repo, directly on the VM — the `.ebextensions/` folder here is
  Elastic Beanstalk leftovers and does not reflect the actual manual
  Docker-on-VM deployment).

## [Unreleased] — 2026-05-17

### Added

- **Live summary card on `/administrative-levels/search/`.** Selecting any level
  in the cascading filter (or a leaf radio) now fades in a sticky card on the
  right with the entity's name, type badge, ancestor breadcrumb, direct-child
  count using the dataset's own next-level vocabulary (e.g. "10 Arrondissements"
  on Benin, "10 Cantons" on Togo), total descendant villages, **total
  population** rolled up across the subtree, **total priorities**
  (`investment_status = PRIORITY`), **projects funded**
  (`project_status != NOT_FUNDED`), identified-priority date, coordinates and
  code where available, and an "Open *<type>* profile" CTA that links to the
  correct detail page (`AdministrativeLevelSummaryAjaxView` at
  `administrativelevels:utils:administrative_level_summary`).
- **`AdministrativeLevel.get_hierarchy_labels()`** classmethod that walks one
  branch root → leaf and returns the dataset's actual level names. Drives the
  search-page form labels, select2 placeholders, and "Choice the X in Y" /
  "Open X profile" copy.
- **Skeleton-shimmer loading affordances on `/investments/`.** The six metric
  cards (available + selected totals) render animated placeholders instead of
  static `0` / `0 FCFA` until the AJAX totals resolve, and refreshes (filter
  change, select-all, checkbox toggles) re-paint skeletons in `beforeSend`.
- **Centered DataTable overlay on `/investments/`.** Replaces DataTables'
  built-in corner "Processing…" badge with a 44 px spinner + "Loading
  investments…" copy, wired to the `processing.dt` event.

### Changed

- **Breadcrumb tag (`adm_breadcrumb`) is name-agnostic.** Was looking up the
  detail URL by `item.type` against the Togo English constants — every
  ancestor link broke on the Benin dataset. Now maps each ancestor to one of
  five fixed routes (`region_detail` → `village_detail`) by position in the
  parent chain. Works for any dataset whose hierarchy uses different
  terminology and survives shorter chains (e.g. canton-rooted pages).
- **Search page (`/administrative-levels/search/`) revamp.** Two-column layout
  with cascading filters and village radios on the left, sticky summary card
  on the right; the search box moved into the left card body; per-row "Check"
  buttons removed (the card's CTA replaces them). The "Choice the village in
  canton" heading and "See village" button now use `blocktranslate with` so
  they reflect the dataset's leaf and parent-of-leaf labels.
- **`VillageSearchForm`.** `region` queryset is now `parent__isnull=True`
  (top-level entities, name-agnostic) instead of `type="Region"` (the original
  matched 0 rows on Benin). `prefecture`/`commune`/`canton` start as
  `objects.none()` since the cascading AJAX populates them at runtime. Added
  `hierarchy_labels=` constructor kwarg so the view can override the four
  field labels with the dataset's actual names.
- **`AdministrativeLevelSearchListView` & `AdministrativeLevelsListView`
  queryset.** Both `get_queryset()` methods now filter `type__iexact=` instead
  of `type=`, and added `order_by("name")` to silence
  `UnorderedObjectListWarning` and stabilise pagination.

### Fixed

- **Search page returned empty results on the Benin dataset.** The view
  filtered `type="Village"` while the data stores `"village"` (lowercase) — 0
  matches. Fixed by switching to `type__iexact` in both list views.
- **Cascading region dropdown was empty on Benin.** Same root cause in the
  `VillageSearchForm.region` queryset; switched to `parent__isnull=True`.
- **Redundant "Villages" row on arrondissement-level summary cards.** Hidden
  when the direct-children row already represents villages
  (`next_level_label == "Village"`).

### Developer

- Added `venv/` to `cosomis/.gitignore`.
