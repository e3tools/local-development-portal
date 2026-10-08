"""
Pipeline stage 5 — read-only consolidation into a single Excel file for
manual review/arbitration. Never writes to any database.

Flattens the stage-4 JSON into one row per besoin with a `decision` column
pre-filled with a suggested action. Edit `decision`, `final_title`,
`sector_name` or `estimated_cost` directly in the spreadsheet; the final
import command (import_new_needs_bj, the only one that writes to the DB
and the only one meant to run in production) only acts on rows whose
`decision` is CREATE_FUNDED or CREATE_UNFUNDED.

Suggested decisions:
  - ALREADY_IN_DB:     db_match is MATCH — this besoin already has an
                        Investment (by position or by DB fuzzy match).
                        Skipped by the final import.
  - CHECK_DB_MATCH:     db_match is REVIEW or CONFLICT — plausibly already
                        in DB under a different title; verify by hand.
  - CREATE_FUNDED:      excel_match is MATCH — funded subproject found in
                        the COSO tracking Excel under a different title;
                        final_title/sector/cost prefilled from that row.
  - CHECK_EXCEL_MATCH:  excel_match is REVIEW or CONFLICT — plausibly a
                        funded subproject; verify by hand.
  - CREATE_UNFUNDED:    no match anywhere — genuinely new, unfunded need;
                        sector is a best guess (see `confidence`).

`possible_duplicate_of` flags besoins sharing the same
(administrative_level, sub_component, normalized title) as another row in
this same file — a belt-and-suspenders check; none were found as of this
writing, but it costs nothing to keep watching for it on future runs.

Usage:
    python manage.py build_review_file_bj \
        --in new_needs_categorized_bj.json \
        --out new_needs_review_bj.xlsx
"""
import json
import re
import unicodedata
from collections import defaultdict

import pandas as pd
from django.core.management.base import BaseCommand


def nk(s):
    s = str(s or "").replace("’", "'").replace("ʼ", "'").replace("‘", "'").strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


class Command(BaseCommand):
    help = (
        "Stage 5 (read-only): consolidate the pipeline's JSON into a single "
        "Excel file for manual review/arbitration. Never writes to the DB."
    )

    def add_arguments(self, parser):
        parser.add_argument("--in", dest="in_path", default="new_needs_categorized_bj.json")
        parser.add_argument("--out", dest="out_path", default="new_needs_review_bj.xlsx")

    def handle(self, *args, **options):
        with open(options["in_path"], encoding="utf-8") as f:
            data = json.load(f)

        dup_groups = defaultdict(list)
        for i, r in enumerate(data):
            key = (r["administrative_level_id"], r["sub_component"], nk(r["title_raw"]))
            dup_groups[key].append(i)

        rows = []
        for i, r in enumerate(data):
            dm = r.get("db_match", {})
            em = r.get("excel_match")
            cat = r.get("categorization")

            cap_override = r.get("capacity_override", {})
            if cap_override.get("reason") == "textual_signal_reinforced":
                decision = "ALREADY_IN_DB"
            elif cap_override.get("reason") == "capacity_cap_lowest_priority":
                decision = "EXCLUDED_CAPACITY_CAP"
            elif cap_override.get("reason") == "under_capacity_no_arbitration":
                decision = "CREATE_UNFUNDED"
            elif dm.get("status") in ("MATCH", "ALREADY_IN_DB"):
                decision = "ALREADY_IN_DB"
            elif dm.get("status") in ("REVIEW", "CONFLICT"):
                decision = "CHECK_DB_MATCH"
            elif em and em["status"] == "ALREADY_IN_DB":
                decision = "ALREADY_IN_DB"
            elif em and em["status"] == "DUPLICATE_RISK":
                decision = "EXCLUDED_DUPLICATE_RISK"
            elif em and em["status"] == "MATCH":
                decision = "CREATE_FUNDED"
            elif em and em["status"] in ("REVIEW", "CONFLICT"):
                decision = "CHECK_EXCEL_MATCH"
            else:
                decision = "CREATE_UNFUNDED"

            final_title = r["title_raw"]
            if em and em["status"] == "MATCH" and em.get("title"):
                final_title = em["title"]

            dup_key = (r["administrative_level_id"], r["sub_component"], nk(r["title_raw"]))
            dup_siblings = [j for j in dup_groups[dup_key] if j != i]

            rows.append({
                "decision": decision,
                "capacity_override_reason": cap_override.get("reason"),
                "facilitator_db": r["facilitator_db"],
                "nosql_document_id": r.get("nosql_document_id"),
                "no_sql_id": f"{r.get('nosql_document_id')}:{r['sub_component']}:{r['ranking']}",
                "administrative_level_id": r["administrative_level_id"],
                "administrative_level_name": r["administrative_level_name"],
                "sub_component": r["sub_component"],
                "ranking": r["ranking"],
                "groupe": r.get("groupe", ""),
                "adaptation_climatique": r.get("adaptation_climatique"),
                "title_raw": r["title_raw"],
                "final_title": final_title,
                "sector_id": cat["sector_id"] if cat else None,
                "sector_name": cat["sector_name"] if cat else None,
                "category_name": cat["category_name"] if cat else None,
                "categorization_confidence": cat["confidence"] if cat else None,
                "estimated_cost": cat["estimated_cost"] if cat else None,
                "db_match_status": dm.get("status"),
                "db_match_score": dm.get("score"),
                "db_match_investment_id": dm.get("investment_id"),
                "db_match_investment_title": dm.get("investment_title"),
                "excel_match_status": em["status"] if em else None,
                "excel_match_score": em["score"] if em else None,
                "excel_match_source": em["source"] if em else None,
                "excel_match_line": em["line"] if em else None,
                "excel_match_title": em["title"] if em else None,
                "excel_match_cost": em["cost"] if em else None,
                "excel_match_phase": em.get("phase") if em else None,
                "excel_match_confirmed_funded": em.get("confirmed_funded") if em else None,
                "possible_duplicate_of_row": ",".join(str(j + 2) for j in dup_siblings) or "",
            })

        df = pd.DataFrame(rows)
        df.to_excel(options["out_path"], index=False, sheet_name="Review")

        counts = df["decision"].value_counts().to_dict()
        self.stdout.write(self.style.SUCCESS(
            f"Review file written to {options['out_path']} ({len(df)} rows) — " +
            " | ".join(f"{k}: {v}" for k, v in counts.items())
        ))
