# UX Review & Design Improvements

A code-level UX audit of the COSOMIS local-development portal, covering the
`administrativelevels`, `investments`, `cdd_funnel`, `dashboard`,
`authentication`/`usermanager` apps and the shared layout layer.

Findings are grouped by area. Each item lists the location, the observable
problem, and a severity (`high` / `medium` / `low`). Severity reflects user
impact × frequency, not implementation effort.

> **Scope note:** these are issues observable in the code (missing states,
> swallowed errors, absent affordances). They are not speculative redesigns.
> Project conventions (i18n via `{% translate %}`, dataset-agnostic level
> handling, HTMX for new fragment UX) are assumed and called out where violated.

---

## Executive summary

The app is functional and, in places, does the right thing (the investments
list paints skeleton loaders in `beforeSend` for its totals AJAX). The gaps are
consistent and fixable:

1. **Feedback is missing at the moments users most need it** — form submits with
   no loading state, AJAX filter updates that leave stale numbers, irreversible
   moderator actions with no confirmation.
2. **Failure is silent** — external API errors (GRM, Mapbox) and failed HTMX
   requests fail without telling the user anything.
3. **Empty states read as "broken"** — many tables render a header over an empty
   `<tbody>` with no message.
4. **Error UX is inconsistent** — a mix of Django messages, raw JS
   `alert(statusCode)`, and silent failures across the same app.
5. **Accessibility and mobile are afterthoughts** — icon-only controls without
   labels, box-shadow-only focus, and effectively one mobile breakpoint.

### Recommended order of work

| Priority | Work item | Why first |
| --- | --- | --- |
| 1 | Auth pages: submit spinners + inline validation | Self-contained, every user hits it, high visibility |
| 2 | Moderator approve/reject confirmation modal | Prevents real, irreversible mistakes |
| 3 | Extend skeleton pattern to investments filter path | Infrastructure already exists; just unwired |
| 4 | Empty-state component reused across tables | One component, many pages improved |
| 5 | Consistent error/toast layer | Removes raw `alert()` and silent failures app-wide |

---

## 1. Authentication & account flows

The first surface every user touches; currently the weakest on feedback.

| # | Location | Problem | Severity |
| --- | --- | --- | --- |
| 1.1 | `usermanager/templates/login.html:87` | Login button has no loading/disabled state — no spinner, no text change. Users can't tell the form is processing and may double-submit. | high |
| 1.2 | `usermanager/templates/register.html:63` | Sign-up button has no loading state; `disableOnSubmit.js` expects a `.submit-spin` element that the template doesn't render, so feedback never fires. | high |
| 1.3 | `static/js/disableOnSubmit.js:1` | Script hides `.submit-spin` on load; if the markup is absent (as above), the user gets *no* submit feedback at all. | high |
| 1.4 | `usermanager/templates/login.html:80` | No client-side / inline validation; email & password errors only surface after a server round-trip. No HTML5 `required`/`pattern` either. | high |
| 1.5 | `usermanager/templates/register.html:55` | Password-confirmation (`password2`) mismatch isn't shown inline — only on submit. | medium |
| 1.6 | `usermanager/templates/password_reset.html:70` | Error uses inline `style="color:red"` instead of a semantic alert; no ARIA. | medium |
| 1.7 | `usermanager/templates/password_reset_confirm.html:68` | Token-expiry errors and password-mismatch errors are visually indistinguishable. | medium |
| 1.8 | `usermanager/views_change_password.py:95` | Endpoint returns a generic `error` status; frontend can't distinguish "code expired" vs "code invalid" vs "password too weak". | medium |
| 1.9 | `usermanager/templates/login.html:94` & `:98` | "Forgot password" is a plain link; "Sign up" CTA sits below the fold — two-step discovery friction. | low |

---

## 2. Investments

The most operationally important app, with the highest-severity single finding.

| # | Location | Problem | Severity |
| --- | --- | --- | --- |
| 2.1 | `investments/views.py:709` (ModeratorPackageReviewView) | Approve/Reject process **immediately, with no confirmation modal and no undo**. Accidental, irreversible actions. | high |
| 2.2 | `investments/views.py:494` (CartView) | Budget-overflow ("Not enough funds") relies entirely on a Django-messages Bootstrap alert; if that alert is missed/clipped, the user believes the package submitted. | high |
| 2.3 | `investments/list.html` (stat cards) | Initial load paints skeletons correctly, but **filter changes refresh stats via AJAX with no loading state** — stale numbers stay on screen. Pattern already exists; just not extended to the filter path. | medium |
| 2.4 | `investments/views.py:709` / `moderator/approvals_list.html` | Overdue packages are in a separate collapsed section rather than badged in the main approvals table — easy to miss. | medium |
| 2.5 | `investments/cart.html:38` | `total-funding-display` is rendered once server-side; `sum_subprojects()` doesn't update it as rows are added/removed. | medium |
| 2.6 | `investments/views.py:351` + `list.html` | When no filters match, users see DataTables' raw "No matching records found" instead of a helpful empty-state card. | medium |
| 2.7 | `investments/list.html:1143` | "Add to cart" with no project selected fails silently — no validation message, no state change. | medium |
| 2.8 | `package.html:176` / `cart.html:176` | Empty `funded_investments` renders a header over an empty table with no "No investments added yet" message. | medium |
| 2.9 | `investments/profile.html:108` | Profile form (email/name/skills) has no visible submit button — appears editable but offers no save affordance. | medium |
| 2.10 | `investments/profile.html:447` | Change-password AJAX surfaces raw `alert(error_server_message + status)` — HTTP status codes shown to users; network vs validation errors not distinguished. | medium |
| 2.11 | `investments/views.py:62` (IndexListView) | Disabled Type-select (until a Sector is chosen) has no helper text/`title` explaining why it's disabled. | low |
| 2.12 | `investments/views.py:416` (PackageDetailView) | Cross-org access falls through to Django's terse default 404 instead of a "you don't have permission" message. | low |
| 2.13 | `investments/investor/approvals_list.html` | No bulk-acknowledge; packages must be actioned one at a time. | low |

---

## 3. Administrative levels

| # | Location | Problem | Severity |
| --- | --- | --- | --- |
| 3.1 | `administrativelevels/views.py:183` (DetailView) | Carousel images load async with a spinner but **no error fallback** — failed loads leave blank space. | high |
| 3.2 | `administrativelevels/views.py:404` (DetailView) | GRM API errors are swallowed (`print` + empty complaints list); the user sees an empty section with no explanation. | high |
| 3.3 | `administrativelevels/views.py:1480` (AttachmentListView) | HTMX grid pagination has **no skeleton and no `htmx:responseError` handler** — failed/slow page loads fail silently. | high |
| 3.4 | `administrative_level/detail/index.html:328`, `canton/canton_detail.html:37` | Carousel `alt` text defaults to empty/`{{ image.task }}`, producing meaningless or absent alt attributes. | high |
| 3.5 | `administrativelevels/views.py:48` (ListView) | Cascading region→prefecture→commune→canton selects show a disabled state with no loading indicator between AJAX calls. | high |
| 3.6 | `project/list.html:53` | Search "button" is `type="button"` (not submit) — pressing Enter doesn't search. | high |
| 3.7 | `administrativelevels/views.py:1251` (ProjectListView) | No pagination; large project lists render every row. Empty list shows no message. | high |
| 3.8 | `administrativelevels/views.py:1282` (ProjectDetailView) | Investment-update form posts with no spinner/toast; success only evident after full reload. File-upload errors show a generic message with no cause (size/format). | high |
| 3.9 | `project/create/bulk_upload_investments.html` | No client-side file-type/size validation; `ValidationError` messages ("Missing required headers…") are technical; no progress indicator and no post-import summary. | medium |
| 3.10 | `commune/commune_detail.html`, `canton/canton_detail.html` | Filter changes trigger un-debounced GET/POST redirects with no loading indicator; village/investment lists are unpaginated. | medium |
| 3.11 | `administrativelevels/views.py:85` (CreateView) | Validation errors render as a single blanket `alert-danger` rather than inline per-field; AJAX parent-fetch failure shows raw `alert()`. | medium |
| 3.12 | `priorities_table.html:85` | Dynamically generated POST buttons — verify CSRF token presence in each form. | high |
| 3.13 | `administrativelevels/views.py:503` | `print()` statements left in for village-infrastructure debugging; should use Django logging, and the strings aren't translatable. | low |

---

## 4. CDD funnel

| # | Location | Problem | Severity |
| --- | --- | --- | --- |
| 4.1 | `cdd_funnel/views.py:67` + `cdd_funnel.html:194` | Empty `summary.stages` still renders an empty funnel SVG with no "no stages configured" message. | medium |
| 4.2 | `cdd_funnel/views.py:109` (StageDrilldownView) | HTMX drilldown shows only a small indicator dot; pagination clicks have no full-panel loading overlay, inviting double-clicks. | medium |
| 4.3 | `cdd_funnel.html:11` | Clickable legend items (`cursor:pointer`, hover styles) have no hint they're interactive. | low |
| 4.4 | `cdd_funnel.html:135` | JS-populated `#hero-updated-at` has no fallback text if JS fails. | low |
| 4.5 | `cdd_funnel/views.py:109` | Invalid `stage_key` raises a raw Http404 rather than a friendly "stage no longer exists". | low |

---

## 5. Dashboard

| # | Location | Problem | Severity |
| --- | --- | --- | --- |
| 5.1 | `dashboard/views_summary.py:10` + `dashboard_summary.html` | Mapbox token injected with no failure handling; an invalid token / network error leaves a silently blank map. | medium |
| 5.2 | `dashboard/templates/dashboard_subprojects.html`, `dashboard_administrativelevels.html` | Tables render a header over empty results with no "no data" message — indistinguishable from loading. | medium |
| 5.3 | `dashboard/templates/components/summary_table.html` | AJAX-loaded summary cells have no skeleton; blank cells until response. | medium |
| 5.4 | `dashboard/views_administrativelevels.py:45` | Cascading filter logic has no breadcrumb/affordance showing the selected level; clearing-on-change feels arbitrary. | medium |
| 5.5 | `dashboard_summary.html:75` | Disabled prefecture dropdown (until region chosen) has no `aria-label`/`title`. | low |
| 5.6 | `dashboard/views_subprojects.py:28` | Large commented-out `get_queryset()` block — code smell suggesting an unfinished/untested view. | low |

---

## 6. Shared layout, navigation & global UX

| # | Location | Problem | Severity |
| --- | --- | --- | --- |
| 6.1 | `cosomis/templates/layouts/head.html:15` + `static/css/custom.css` | Effectively one mobile breakpoint (`max-width: 575.98px`); navbar/sidebar lack a real mobile collapse pattern. | high |
| 6.2 | `cosomis/templates/layouts/navbar.html:116` | Icon-only logout link (`role="button"`, no text, no `aria-label`) — screen readers skip it. | high |
| 6.3 | `cosomis/templates/common/messages.html:24` | Non-danger messages render as **modals** (interrupt + require dismissal) instead of inline/toast — poor for success/info. | medium |
| 6.4 | `cosomis/templates/common/messages.html:6` | Alert class built from `alert-{{ message.extra_tags }}` with no fallback; missing tag yields a broken CSS class. | medium |
| 6.5 | `static/css/custom.css:67` | Button focus uses `box-shadow` only, no visible outline — keyboard users can't see focus. | medium |
| 6.6 | `cosomis/templates/layouts/sidebar.html:32` | Active-link detection compares `url_name` only; breaks with query params / partial matches. | medium |
| 6.7 | `cosomis/templates/layouts/navbar.html` | No breadcrumbs on deep pages — users lose hierarchy context. | medium |
| 6.8 | `cosomis/templates/layouts/foot.html:73` | Hardcoded French push-notification string ("Veuillez aller changer votre mot de passe…") not run through i18n. | medium |
| 6.9 | `static/js/notifications.js:1` | Toasts are bottom-right only, visual-only (no screen-reader announcement), and use hardcoded strings instead of `{% trans %}`/`gettext`. | medium |
| 6.10 | `cosomis/templates/layouts/navbar.html:9` | Back-chevron link has `role="button"` but no `aria-label`. | medium |
| 6.11 | `usermanager/templates/email_confirmed_successfully.html:34` | Button placed in a `.structure_name` div outside `<body>`; CSS cascade may render it incorrectly. | medium |
| 6.12 | `cosomis/templates/layouts/navbar.html:50` | Hamburger toggle gives no visual expanded/collapsed feedback. | low |

---

## 7. Cross-cutting themes (fix once, benefit everywhere)

These recur across apps and are best solved with a shared component rather than
per-page patches.

- **Empty-state component** — a small reusable include (icon + message + optional
  CTA) for: project list, package/cart tables, dashboard tables, commune/canton
  priorities, funnel-with-no-stages, gallery-no-results.
- **Consistent error/toast layer** — replace raw `alert()` and silent failures
  with one accessible toast/inline-error mechanism; distinguish network vs
  validation vs auth (CSRF/session-expired) errors.
- **Loading-state convention** — the investments-list `beforeSend` skeleton
  pattern (per `CLAUDE.md`) should be the standard for *all* AJAX/HTMX swaps:
  skeleton on `beforeSend`, real value on `success`, `—` on `error`. Apply to
  filter updates, HTMX grids, dashboard summary cells, carousels.
- **Form-submit convention** — every submit button gets a disabled+spinner state
  (fix `disableOnSubmit.js` ↔ `.submit-spin` markup mismatch and reuse it).
- **Accessibility baseline** — visible focus outlines, `aria-label` on icon-only
  controls, non-empty descriptive `alt`, `role="status"`/`aria-live` on spinners.
- **i18n compliance** — no hardcoded strings in JS/templates; route everything
  through `{% translate %}` / `gettext`, then `make generate-translations`.

---

## Appendix: counts by severity

| Severity | Count |
| --- | --- |
| High | 17 |
| Medium | 30+ |
| Low | 13 |

The high-severity cluster is dominated by **missing submit/AJAX feedback**,
**silent failures**, and **accessibility/mobile** gaps — exactly the
cross-cutting themes in §7, which is why a handful of shared components resolve a
disproportionate share of the list.
