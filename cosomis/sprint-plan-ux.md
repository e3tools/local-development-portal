# Sprint Plan: UX Hardening

Companion to [design-improvements.md](design-improvements.md). Each work item
("session") is scoped to be completable in **a single Claude Code session** —
coherent, independently shippable, with a clear done-state and verification step.

**Capacity unit:** 1 session = one focused Claude Code working session ending in a
PR to `develop2`. Estimates are S / M / L by session-effort, not story points:

- **S** — one app/template area, mechanical change, low regression risk.
- **M** — multiple files or some new shared markup/JS, moderate testing.
- **L** — new shared component or cross-cutting refactor touching many templates.

**Sequencing principle:** the two "foundation" sessions (S6 empty-state component,
S7 toast/error layer) are deliberately scheduled early because later sessions reuse
them. Do them before the sessions that depend on them.

---

## Sprint Goal

> Close the high-severity feedback, silent-failure, and accessibility gaps, and
> establish the three shared conventions (loading skeletons, empty states, toast
> errors) that the rest of the backlog reuses.

---

## Capacity & load

Plan to ~75% — leave room for review churn and dataset-specific surprises
(Togo vs Benin). Suggested grouping into three sprints of ~6 sessions each.

| Sprint | Theme | Sessions | Load |
| --- | --- | --- | --- |
| Sprint 1 | High-severity feedback + foundations | S1–S6 | P0-heavy |
| Sprint 2 | Apply foundations + admin-levels gaps | S7–S12 | P1-heavy |
| Sprint 3 | Polish: a11y, mobile, i18n, cleanup | S13–S18 | P2-heavy |

---

## Sprint 1 — High-severity feedback + foundations

| ID | Session (chunk) | Covers | Est | Pri | Depends on |
| --- | --- | --- | --- | --- | --- |
| S1 | **Auth submit feedback + validation** — add disabled+spinner state to login & register submits; fix the `disableOnSubmit.js` ↔ missing `.submit-spin` markup mismatch; add HTML5 + inline validation (incl. `password2` mismatch). | §1.1–1.5, 1.9 | M | P0 | — |
| ✅ S2 | **Moderator approve/reject confirmation** — confirmation modal before approve/reject; badge overdue packages in the main approvals table. | §2.1, 2.4 | M | P0 | — |
| S3 | **Investments budget-overflow + cart totals** — make "Not enough funds" unmissable (block submit + visible error); make `total-funding-display` update live in `sum_subprojects()`. | §2.2, 2.5 | M | P0 | — |
| S4 | **Investments filter loading states** — extend the existing `beforeSend` skeleton pattern to filter-change AJAX so stat cards never show stale numbers. | §2.3 | S | P1 | — |
| S5 | **Admin-levels detail: carousels + GRM errors** — error fallback for failed carousel image loads; surface GRM API failure with a message instead of an empty section; add `role="status"` to spinners. | §3.1, 3.2 | M | P0 | — |
| S6 | **Shared empty-state component** *(foundation)* — build one reusable include (icon + message + optional CTA); apply to project list and one investments table as the reference implementation. | §7, §2.8, §3.7 | M | P0 | — |

---

## Sprint 2 — Apply foundations + admin-levels gaps

| ID | Session (chunk) | Covers | Est | Pri | Depends on |
| --- | --- | --- | --- | --- | --- |
| S7 | **Shared toast/error layer** *(foundation)* — one accessible toast/inline-error mechanism; replace raw `alert(statusCode)` calls; distinguish network / validation / CSRF-session-expired; switch non-danger Django messages from modal to toast; add `extra_tags` fallback. | §6.3, 6.4, 2.10, 1.8 | L | P0 | — |
| S8 | **Apply empty states across tables** — package/cart tables, dashboard subprojects & administrativelevels tables, commune/canton priorities, funnel-no-stages, gallery-no-results. | §2.6, 5.2, 4.1, §7 | M | P1 | S6 |
| S9 | **Gallery HTMX loading + errors** — skeleton on HTMX grid pagination; add `htmx:responseError` handling; fix invalid-page empty grid. | §3.3 | M | P1 | — |
| S10 | **Cascading-select loading feedback** — loading indicators between region→prefecture→commune→canton AJAX steps in admin-levels list and dashboard filters; `title`/`aria-label` on disabled selects. | §3.5, 5.5, 2.11 | M | P1 | — |
| S11 | **Project list search + pagination** — fix search `type="button"` → submit (Enter works); add pagination to `ProjectListView`. | §3.6, 3.7 | S | P1 | S6 |
| S12 | **Project detail + bulk-upload feedback** — spinner/toast on investment-update submit; clearer upload error causes; client-side file validation, progress indicator, and post-import summary for bulk upload. | §3.8, 3.9 | M | P1 | S7 |

---

## Sprint 3 — Polish: accessibility, mobile, i18n, cleanup

| ID | Session (chunk) | Covers | Est | Pri | Depends on |
| --- | --- | --- | --- | --- | --- |
| S13 | **Accessibility baseline sweep** — `aria-label` on icon-only logout & back-chevron; visible focus outlines (not box-shadow only); non-empty descriptive `alt` on carousel images; `aria-live` on spinners. | §6.2, 6.5, 6.10, 3.4 | M | P1 | — |
| S14 | **Mobile / responsive nav + sidebar** — real mobile collapse pattern for navbar/sidebar; add breakpoints beyond the single `575.98px` query; hamburger expanded/collapsed feedback. | §6.1, 6.12 | L | P1 | — |
| S15 | **i18n cleanup** — route hardcoded JS strings (`foot.html` push notification, `notifications.js`) through `{% translate %}`/`gettext`; replace `print()` debug strings; run `make generate-translations`. | §6.8, 6.9, 3.13 | M | P2 | — |
| S16 | **Navigation context** — breadcrumbs on deep pages; fix sidebar active-link detection (query params / partial matches). | §6.7, 6.6 | M | P2 | — |
| S17 | **Commune/canton filter UX** — debounce filter redirects + loading indicator; paginate village/investment lists; inline per-field validation on the create view. | §3.10, 3.11 | M | P2 | S6, S7 |
| S18 | **Security & cleanup pass** — audit CSRF tokens in dynamically generated POST forms; remove commented-out `get_queryset()` dead code; fix `email_confirmed_successfully.html` button outside `<body>`; minor funnel polish (legend hint, updated-at fallback, friendly stage-404). | §3.12, 5.6, 6.11, 4.3–4.5 | M | P2 | — |

---

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Foundation sessions (S6, S7) slip | Blocks S8, S11, S12, S17 | Front-load them in Sprint 1/early Sprint 2; keep their scope minimal (component + one reference use). |
| Dataset-specific breakage (Togo vs Benin vocab) | UI fixes pass on one dataset, break on the other | Verify against both datasets per CLAUDE.md; never hard-code level `type` strings — use the model helpers. |
| Toast/error refactor (S7) touches many call sites | Wide regression surface | Ship the mechanism + migrate the noisiest call sites; migrate the long tail opportunistically in later sessions. |
| Mobile refactor (S14) larger than one session | Sprint 3 overrun | If it exceeds a session, split: navbar in one, sidebar in a follow-up; it's the most likely L-to-split candidate. |
| i18n catalog drift | Untranslated strings ship | Always run `make generate-translations` and confirm both `en`/`fr` catalogs in S15. |

---

## Definition of Done (per session)

- [ ] Change scoped to the session's items; no unrelated drive-by edits.
- [ ] Branched from `develop2`, `claude/` prefix, Conventional Commit messages.
- [ ] Verified against a real dataset via `Client().login(email=…)` + `c.get(…)`
      (and the dev server for visual/interaction changes).
- [ ] Tested on **both** Togo and Benin where the change touches admin-level UI.
- [ ] All user-facing strings run through i18n; `make generate-translations` run.
- [ ] Accessibility check for any new interactive markup (label, focus, role).
- [ ] PR opened back to `develop2`.

---

## Suggested first session

**S1 — Auth submit feedback + validation.** Self-contained, every user hits it,
high visibility, no dependencies, and it fixes the `disableOnSubmit.js` /
`.submit-spin` mismatch that currently makes the spinner infrastructure inert.
