"""
Pipeline stage 5.5 — read-only. Locks in the arbitration recorded in the
review Excel into config_data/resolved_needs_bj.json, WITHOUT touching the
database.

Every row with a final decision (anything except the pending CHECK_*
values) is recorded under its `no_sql_id`. The next run of
extract_new_needs_bj will skip these besoins entirely — this is what lets
the arbitration survive even before (or without ever) running the
production import, and keeps a repeat synctasks sync from re-surfacing the
same besoins.

import_new_needs_bj also updates this same ledger on a real run, so once
that command has run for a given review file there's no need to run this
one again for it — this command exists for locking in arbitration ahead
of, or independently of, the production import.

Usage:
    python manage.py lock_in_resolved_needs_bj --review-file new_needs_review_bj.xlsx
"""
import json
from datetime import date
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand

PENDING_DECISIONS = {"CHECK_DB_MATCH", "CHECK_EXCEL_MATCH"}
LEDGER_PATH = Path(settings.BASE_DIR) / "config_data" / "resolved_needs_bj.json"


class Command(BaseCommand):
    help = (
        "Stage 5.5 (read-only): lock in the review Excel's arbitration "
        "into config_data/resolved_needs_bj.json. Never writes to the DB."
    )

    def add_arguments(self, parser):
        parser.add_argument("--review-file", required=True)

    def handle(self, *args, **options):
        df = pd.read_excel(options["review_file"])

        ledger = {}
        if LEDGER_PATH.exists():
            with open(LEDGER_PATH, encoding="utf-8") as f:
                ledger = json.load(f)

        today = date.today().isoformat()
        written, skipped_pending = 0, 0

        for _, row in df.iterrows():
            decision = str(row.get("decision", "")).strip()
            if decision in PENDING_DECISIONS:
                skipped_pending += 1
                continue

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

        self.stdout.write(self.style.SUCCESS(
            f"Ledger entries written/updated: {written} | "
            f"Still pending (not locked in): {skipped_pending} | "
            f"Ledger now has {len(ledger)} total entries at {LEDGER_PATH}"
        ))
