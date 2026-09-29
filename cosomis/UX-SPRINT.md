# UX-SPRINT.md — how to work on the `ux-improvements` branch

**Read this before doing any UX-sprint work.** This branch is the long-lived
integration branch for the UX hardening sprint. It stays open until all sessions
in [sprint-plan-ux.md](sprint-plan-ux.md) are complete, then merges to
`develop2`.

## The three documents

- [design-improvements.md](design-improvements.md) — the audit. The "why": every
  finding with `file:line` and severity, grouped by area (§1–6) plus cross-cutting
  themes (§7).
- [sprint-plan-ux.md](sprint-plan-ux.md) — the plan. Findings organized into 18
  sessions (S1–S18) across 3 sprints, with dependencies and per-session
  Definition of Done.
- **UX-SPRINT.md** (this file) — the workflow. How to pick up and ship a session.

## Branch model

```
develop2  ──┬─────────────────────────────────────────────►  (sprint merges back here at the end)
            │
ux-improvements ──┬──────┬──────┬──────────────────────────►  (long-lived integration branch)
                  │      │      │
              claude/    claude/   claude/
              ux-s1-…   ux-s2-…   ux-s3-…   (one short-lived branch PER SESSION)
```

- `ux-improvements` is the **base branch for this sprint**. Do **not** commit
  session work directly to it.
- Each session (S1–S18) gets its own branch off `ux-improvements`, named
  `claude/ux-s<N>-<slug>` (e.g. `claude/ux-s1-auth-submit-feedback`).
- Open the session PR **against `ux-improvements`**, not `develop2`.
- When the whole sprint is done, `ux-improvements` → `develop2` in one PR.

## Working a session — the loop

1. **Pick the next session.** Honor the dependency column in
   `sprint-plan-ux.md`. Foundations **S6** (empty-state component) and **S7**
   (toast/error layer) must land before the sessions that depend on them
   (S8, S11, S12, S17). Don't start a session whose dependency is unmerged.
2. **Branch:** from up-to-date `ux-improvements`:
   ```
   git checkout ux-improvements && git pull
   git checkout -b claude/ux-s<N>-<slug>
   ```
3. **Scope discipline.** Do **only** the §-items listed for that session in the
   plan. No unrelated drive-by edits — if you spot something new, add it to
   `design-improvements.md` (and the plan) rather than fixing it inline.
4. **Build**, following the conventions below.
5. **Verify** per the Definition of Done (below). Verification is required, not
   optional — type-coupling bugs only surface against a real dataset.
6. **Update tracking** (below): tick the session in the plan, note anything
   deferred.
7. **Commit** with Conventional Commits, **PR into `ux-improvements`.**

## Definition of Done (every session)

Mirrors `sprint-plan-ux.md`; repeated here as the checklist to actually run:

- [ ] Change scoped to the session's items only.
- [ ] Branched `claude/ux-s<N>-…` from `ux-improvements`; PR targets `ux-improvements`.
- [ ] Verified via `Client().login(email=…)` + `c.get(…)` from `manage.py shell`,
      and the dev server for any visual/interaction change.
- [ ] Tested on **both Togo and Benin** when the change touches admin-level UI.
- [ ] All user-facing strings go through i18n; `make generate-translations` run.
- [ ] New interactive markup has label + visible focus + correct role/aria.
- [ ] Session row ticked in `sprint-plan-ux.md`.

## Conventions that bite (from CLAUDE.md — non-negotiable here)

- **Never hard-code admin-level `type` strings.** Use `matches_type`,
  `type_filter_q`, `is_village()`/`is_canton()`/…, `get_hierarchy_labels()`.
  Prefer position-in-hierarchy over type string. This sprint touches a lot of
  admin-level UI — this is the #1 way to ship a Benin-only regression.
- **i18n is mandatory.** `{% translate %}` / `gettext_lazy` / `blocktranslate`;
  no hardcoded strings in templates or JS. Run `make generate-translations`.
- **Prefer HTMX** for new fragment-swap UX over hand-rolled `$.ajax`.
- **No multi-line `{# … #}` comments** — use `{% comment %}…{% endcomment %}`.
- **Loading-state pattern** (the standard this sprint propagates): skeleton in
  `beforeSend`, real value on `success`, `—` on `error`.
- Custom user model is **email-keyed**: `Client().login(email=…, password=…)`.

## Tracking progress

Keep the plan honest as the single source of truth:

- When a session merges, change its row marker in `sprint-plan-ux.md` to `✅`
  (prefix the ID, e.g. `✅ S1`).
- If you defer or split an item, say so in the plan's Risks section and adjust
  the session list — don't silently drop scope.
- New findings discovered mid-sprint go into `design-improvements.md` first,
  then into the plan as a new `S19+` session — never smuggled into an unrelated
  session.

## When the sprint is done

All S1–S18 merged into `ux-improvements` → open one PR `ux-improvements` →
`develop2`, summarizing the closed findings by severity. Then this branch and
these three planning docs can be retired (or moved to `docs/`).
