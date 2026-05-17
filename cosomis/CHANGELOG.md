# Changelog

All notable user-visible and developer-facing changes are tracked here. The
format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
