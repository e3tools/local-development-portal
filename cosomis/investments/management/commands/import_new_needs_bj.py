"""
Pipeline stage 6 (FINAL) — the only command in this pipeline meant to run
in production. Reads the review Excel produced by build_review_file_bj
(after your manual arbitration) and creates the real new Investment rows.

Only rows whose `decision` column is CREATE_FUNDED or CREATE_UNFUNDED are
acted on — everything else (ALREADY_IN_DB, CHECK_DB_MATCH,
CHECK_EXCEL_MATCH, or any other value you set by hand) is skipped. Edit
`decision`, `final_title`, `sector_id`/`sector_name` or `estimated_cost`
directly in the spreadsheet before running this for real.

Idempotent: skips any row whose `no_sql_id` already exists on an
Investment, so re-running on an unchanged file (or a file with leftover
rows from a previous run) never duplicates.

Sets `no_sql_id` and `ranking` on every created Investment — this is what
lets the next run of extract_new_needs_bj (stage 1) recognize these as
"already synced" by stable position, instead of relying on `title` (which
gets renamed later during funding arbitration).

Also writes every row with a FINAL decision (anything except the pending
CHECK_* values) to config_data/resolved_needs_bj.json, keyed by
`no_sql_id` — this ledger is what lets extract_new_needs_bj skip these
besoins on the *next* synctasks run, even the ALREADY_IN_DB /
EXCLUDED_* ones that never got an Investment of their own, so this whole
arbitration pass is never redone for the same besoins. Only written on a
real (non-dry-run) run.

Usage:
    python manage.py import_new_needs_bj --review-file new_needs_review_bj.xlsx --dry-run
    python manage.py import_new_needs_bj --review-file new_needs_review_bj.xlsx
"""
import json
from datetime import date
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from administrativelevels.models import AdministrativeLevel, Sector, Project
from investments.models import Investment

PENDING_DECISIONS = {"CHECK_DB_MATCH", "CHECK_EXCEL_MATCH"}
LEDGER_PATH = Path(settings.BASE_DIR) / "config_data" / "resolved_needs_bj.json"


GROUP_FIELD_MAP = {
    "Jeunes":                   "endorsed_by_youth",
    "Groupe des jeunes":        "endorsed_by_youth",
    "Femmes":                   "endorsed_by_women",
    "Groupe des femmes":        "endorsed_by_women",
    "Éleveurs et Agriculteurs": "endorsed_by_agriculturist",
    "Groupe des éleveurs et agriculteurs": "endorsed_by_agriculturist",
    "Minorités ethniques":      "endorsed_by_pastoralist",
    "Notables & Chefferie":     "endorsed_by_chiefs",
    "Groupe des leaders/chefferie": "endorsed_by_chiefs",
}

ACTIONABLE_DECISIONS = {"CREATE_FUNDED", "CREATE_UNFUNDED"}


class Command(BaseCommand):
    help = (
        "FINAL stage, prod-only: create the real Investment rows from the "
        "arbitrated review Excel. Only CREATE_FUNDED/CREATE_UNFUNDED rows "
        "are acted on. Idempotent via no_sql_id."
    )

    def add_arguments(self, parser):
        parser.add_argument("--review-file", required=True)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        review_path = options["review_file"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("*** DRY RUN — no changes will be saved ***"))

        df = pd.read_excel(review_path)

        try:
            coso_project = Project.objects.get(name="COSO")
        except Project.DoesNotExist:
            raise CommandError("Project 'COSO' not found in DB. Cannot set funded_by.")

        stats = {"created_funded": 0, "created_unfunded": 0, "already_exists": 0,
                  "skipped_decision": 0, "errors": 0}

        with transaction.atomic():
            for _, row in df.iterrows():
                decision = str(row.get("decision", "")).strip()
                if decision not in ACTIONABLE_DECISIONS:
                    stats["skipped_decision"] += 1
                    continue

                no_sql_id = str(row.get("no_sql_id", "")).strip()

                if Investment.objects.filter(no_sql_id=no_sql_id).exists():
                    stats["already_exists"] += 1
                    continue

                try:
                    adm = AdministrativeLevel.objects.get(id=int(row["administrative_level_id"]))
                except AdministrativeLevel.DoesNotExist:
                    self.stdout.write(self.style.ERROR(
                        f"  [ERROR] AdministrativeLevel id={row['administrative_level_id']} not found"
                    ))
                    stats["errors"] += 1
                    continue

                sector = None
                if pd.notna(row.get("sector_id")):
                    sector = Sector.objects.filter(id=int(row["sector_id"])).first()
                if sector is None:
                    sector = Sector.objects.filter(name="Autre").first()

                is_funded = decision == "CREATE_FUNDED"
                groupe = str(row.get("groupe", "") or "").strip()
                endorsed_field = GROUP_FIELD_MAP.get(groupe)
                adaptation = row.get("adaptation_climatique")
                has_climate = bool(adaptation) and str(adaptation).strip().lower() not in ("", "nan", "none")

                title = str(row.get("final_title", "") or "").strip()
                try:
                    ranking = int(row["ranking"]) if pd.notna(row.get("ranking")) else None
                except (ValueError, TypeError):
                    ranking = None
                try:
                    estimated_cost = int(float(row["estimated_cost"])) if pd.notna(row.get("estimated_cost")) else 0
                except (ValueError, TypeError):
                    estimated_cost = 0

                if dry_run:
                    self.stdout.write(
                        f"  [DRY] CREATE {'FUNDED' if is_funded else 'UNFUNDED'} "
                        f"adm={adm.name} sub={row['sub_component']} sector={sector.name if sector else '?'} "
                        f"title='{title[:60]}' cost={estimated_cost}"
                    )
                else:
                    kwargs = dict(
                        title=title,
                        description=groupe,
                        administrative_level=adm,
                        sector=sector,
                        sub_component=row["sub_component"],
                        ranking=ranking,
                        estimated_cost=estimated_cost,
                        investment_status=Investment.SUBPROJECT if is_funded else Investment.PRIORITY,
                        project_status=Investment.FUNDED_NOT_STARTED if is_funded else Investment.NOT_FUNDED,
                        funded_by=coso_project if is_funded else None,
                        climate_contribution=has_climate,
                        climate_contribution_text=str(adaptation) if has_climate else "",
                        duration=0,
                        delays_consumed=0,
                        physical_execution_rate=0,
                        financial_implementation_rate=0,
                        no_sql_id=no_sql_id,
                    )
                    if endorsed_field:
                        kwargs[endorsed_field] = True
                    Investment.objects.create(**kwargs)

                if is_funded:
                    stats["created_funded"] += 1
                else:
                    stats["created_unfunded"] += 1

            if dry_run:
                transaction.set_rollback(True)

        ledger_written = 0
        if not dry_run:
            ledger_written = self._update_ledger(df)

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(
            f"Done {'(DRY RUN) ' if dry_run else ''}— "
            f"created_funded={stats['created_funded']}, "
            f"created_unfunded={stats['created_unfunded']}, "
            f"already_exists={stats['already_exists']}, "
            f"skipped_decision={stats['skipped_decision']}, "
            f"errors={stats['errors']}, "
            f"ledger_entries_written={ledger_written}"
        ))

    def _update_ledger(self, df):
        ledger = {}
        if LEDGER_PATH.exists():
            with open(LEDGER_PATH, encoding="utf-8") as f:
                ledger = json.load(f)

        today = date.today().isoformat()
        written = 0
        for _, row in df.iterrows():
            decision = str(row.get("decision", "")).strip()
            if decision in PENDING_DECISIONS:
                continue  # still awaiting arbitration — may resurface next sync

            no_sql_id = str(row.get("no_sql_id", "")).strip()
            if not no_sql_id or no_sql_id in ("nan", "None:None:None"):
                continue

            ledger[no_sql_id] = {
                "decision": decision,
                "title_raw": str(row.get("title_raw", "")),
                "administrative_level_name": str(row.get("administrative_level_name", "")),
                "sub_component": str(row.get("sub_component", "")),
                "resolved_at": today,
            }
            written += 1

        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER_PATH, "w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=2, sort_keys=True)

        return written
