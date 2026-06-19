# Sprint Plan: UX Hardening — Next Steps (Sprint 4+)

Follow-on to [sprint-plan-ux.md](sprint-plan-ux.md), which closed sessions
**S1–S19**. That sprint shipped the high-severity feedback fixes, silent-failure
recovery, accessibility/mobile baseline, and the four reusable foundations
(empty-state component, toast/error layer, loading-skeleton pattern, brand
tokens). This plan covers what remains: **finishing the long tail the foundations
enabled, shipping the branch, hardening against the recurring Togo/Benin
regression, and paying down adjacent debt.**

**Source of truth for findings:** [design-improvements.md](design-improvements.md)
(audit) and the S7 follow-up note in [sprint-plan-ux.md](sprint-plan-ux.md).
New findings discovered mid-sprint go into `design-improvements.md` first, then
into this plan as a new session — never smuggled into an unrelated session.

**Capacity unit & estimates** are unchanged from the prior plan: 1 session = one
focused Claude Code working session ending in a PR. **S** / **M** / **L** by
session-effort.

---

## Sprint Goal

> Ship the `ux-improvements` branch to `develop2`, retire the last raw
> `alert()` call sites onto the shared toast layer, lock in the UX gains with a
> minimal Togo+Benin regression-smoke suite, and clear the adjacent dead code
> and low-severity tail — leaving no half-migrated conventions behind.

---

## Sequencing principle

The **release session (S20) is the gate**: until the branch lands on
`develop2`, the long-tail sessions keep stacking on a long-lived integration
branch and drift from the rest of the team. Do S20 first (or in parallel with
S21 if you prefer to bundle the alert migration into the same release). The
regression-suite session (S24) should land **before or with** the release so the
gains are protected the moment they merge.

| Sprint | Theme | Sessions | Load |
| --- | --- | --- | --- |
| Sprint 4 | Ship + finish foundations' long tail | S20–S23 | release-heavy |
| Sprint 5 | Durability + debt paydown | S24–S27 | P2-heavy |

---

## Sprint 4 — Ship & finish the long tail

| ID | Session (chunk) | Covers | Est | Pri | Depends on |
| --- | --- | --- | --- | --- | --- |
| ☐ S20 | **Release: `ux-improvements` → `develop2`** — open the single integration PR summarizing closed findings by severity (20 high / 33 medium / 12 low); resolve conflicts against current `develop2`; run the full `manage.py check` + the S24 smoke suite on the merge result; verify on **both** Togo and Benin before merge. Move the three planning docs to `docs/` (or retire) per UX-SPRINT.md §"When the sprint is done". | Sprint close-out | M | P0 | — |
| ☐ S21 | **Toast migration: admin-levels long tail** — replace raw `alert(error_server_message + "Error " + data.status)` with `window.notifyAjaxError(jqXHR)` / `window.toast()` across `canton_detail.html`, `administrativelevel_village_list.html`, `administrative_level/list.html`, `administrative_level/create.html`, `geographical_unit_create.html`, `cvd_create.html`, `components/download.html`, and `static/js/dynamicRegionSelector.js`. | S7 follow-up (admin set) | M | P1 | S7 ✅ |
| ☐ S22 | **Toast migration: dashboard + shared JS** — same migration across `dashboard_subprojects.html`, `dashboard_administrativelevels.html`, `dashboard_summary.html`, `components/summary_table.html`, `layouts/head.html`, `static/js/notifications.js`, `static/js/formAjaxSubmit.js`. After S21+S22, grep should show **zero** app-code `alert(` outside vendored `static/AdminLTE/**`. | S7 follow-up (dashboard set) | M | P1 | S7 ✅ |
| ☐ S23 | **Low-severity audit tail** — work the remaining 12 `low`-severity items in `design-improvements.md` (e.g. §1.9 forgot-password/sign-up discovery friction, §1.6 inline-styled error → semantic alert, and the rest). One PR, item-by-item with `file:line` traceability back to the audit. | §1–6 `low` items | M | P2 | S6 ✅, S7 ✅ |

---

## Sprint 5 — Durability & debt paydown

| ID | Session (chunk) | Covers | Est | Pri | Depends on |
| --- | --- | --- | --- | --- | --- |
| ☐ S24 | **Togo+Benin regression-smoke suite** *(foundation)* — close the "no headless E2E suite" gap that lets type-coupling bugs ship. Add a lightweight `Client()`-based test module that logs in and asserts `200` + key fragments on the sprint's touched pages (login, register, investments list+cart, moderator approvals, admin-level detail for canton/commune/village, dashboard summary, funnel) **parametrized over both a Togo-shaped and a Benin-shaped fixture**. Wire it into `manage.py test`. This is the durability backstop for every future UX change. | CLAUDE.md "Testing the UI" gap | L | P0 | — |
| ☐ S25 | **Service-layer hardening: replace bare `assert`** — `canton_summary_service.py:17`, `canton_map_service.py:84`, `canton_planning_service.py:199` guard with bare `assert canton.is_canton()`, which is **stripped under `python -O`** and raises an unfriendly `AssertionError` otherwise. Replace with an explicit guard that raises a typed error (or returns an empty summary + logs) so a mis-typed level degrades gracefully instead of 500-ing. Add a regression test per service for the non-canton input path. | CLAUDE.md §1 follow-up (now alias-aware, still `assert`) | S | P1 | — |
| ☐ S26 | **Dead-code & duplicate-file cleanup** — delete `administrativelevels/templates/canton_detail copy.html` (stray duplicate) and any other `* copy.*`; resolve the 4 remaining `TODO`/`FIXME` markers (fix or convert to tracked issues); remove commented-out dead blocks surfaced during S21/S22. Confirm no template `{% include %}` / view references the deleted files first. | §5.6, repo hygiene | S | P2 | S21, S22 |
| ☐ S27 | **Stakeholder walkthrough & demo script** — short scripted demo on **both** datasets showcasing the brand unification, confirmation flows, loading/empty/error states, and mobile nav; capture before/after screenshots; fold any feedback into `design-improvements.md` as new findings. Pairs with the delivered `UX-Hardening-Sprint-Report.pdf`. | Report next-step #3 | S | P2 | S20 |

---

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| `develop2` drifted while `ux-improvements` was long-lived | S20 merge conflicts, esp. in `custom.css` brand tokens & shared layouts | Rebase/merge `develop2` in early; resolve token conflicts toward the new `--brand-*` values; re-run S24 suite post-merge. |
| Toast migration (S21/S22) misses an error path | A silent failure regresses to a raw `alert` or nothing | Grep-gate: CI/PR check that `alert(` is absent outside `static/AdminLTE/**`; manually trigger each migrated AJAX failure. |
| Smoke suite (S24) over-asserts on dataset-specific strings | Tests pass on Togo, fail on Benin (the exact bug class it's meant to catch) | Assert on structural/role markers and i18n keys, never on a literal level `type` string; parametrize the fixture, not the assertion. |
| Deleting `* copy.html` breaks a stale reference | 500 on an admin-levels page | S26 depends on S21/S22 having touched those templates; grep all `include`/`render`/`TemplateView` references before `git rm`. |

---

## Definition of Done (per session)

Unchanged from [UX-SPRINT.md](UX-SPRINT.md) — repeated as the checklist to run:

- [ ] Change scoped to the session's items; no unrelated drive-by edits.
- [ ] Branched `claude/ux-s<N>-<slug>` from the integration base; Conventional Commit messages.
- [ ] Verified via `Client().login(email=…)` + `c.get(…)` and the dev server for visual/interaction changes.
- [ ] Tested on **both** Togo and Benin where the change touches admin-level UI.
- [ ] All user-facing strings run through i18n; `make generate-translations` run.
- [ ] New interactive markup has label + visible focus + correct role/aria.
- [ ] Session row ticked here; anything deferred noted in Risks.

---

## Suggested first session

**S20 — Release `ux-improvements` → `develop2`.** Everything else compounds value
only once the sprint's work is in the shared integration branch. If you'd rather
not merge mid-stream, run **S24** first so the regression suite lands with the
release and protects the gains from day one.
