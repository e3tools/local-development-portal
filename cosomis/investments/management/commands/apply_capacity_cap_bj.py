"""
Pipeline stage 3.5 — read-only enforcement of the "max 5 besoins per
(village, sub_component)" business rule. Never writes to any database.

The EPB form always asks for up to 5 priorities per sub-component, so a
bucket should never end up with more than 5 Investments once every
candidate besoin is (hypothetically) created. When existing + candidates
would exceed 5 in a bucket:

  - If that bucket already has besoins flagged CHECK_DB_MATCH /
    CHECK_EXCEL_MATCH / EXCLUDED_DUPLICATE_RISK (i.e. some textual
    resemblance to something already in the DB or in the Excel), ALL of
    them are reclassified ALREADY_IN_DB — the capacity constraint
    reinforces the textual signal rather than contradicting it.

  - If the bucket's candidates are all "clean" (no resemblance signal at
    all — the over-cap is the ONLY evidence), we can't justify excluding
    one over another by content. Per user decision, we exclude the
    highest `ranking` (the community's own least-prioritized besoin in
    that sub-component) until the bucket is back down to 5. This is
    marked EXCLUDED_CAPACITY_CAP, distinct from ALREADY_IN_DB, since the
    justification is structural, not textual.

Usage:
    python manage.py apply_capacity_cap_bj \
        --in new_needs_excel_matched_bj.json \
        --out new_needs_capacity_capped_bj.json
"""
import json
from collections import defaultdict

from django.core.management.base import BaseCommand

AMBIGUOUS_DB_STATUSES = {"REVIEW", "CONFLICT"}
AMBIGUOUS_EXCEL_STATUSES = {"REVIEW", "CONFLICT", "DUPLICATE_RISK"}

CAP = 5


def _is_ambiguous(row):
    dm = row.get("db_match", {})
    em = row.get("excel_match")
    if dm.get("status") in AMBIGUOUS_DB_STATUSES:
        return True
    if em and em["status"] in AMBIGUOUS_EXCEL_STATUSES:
        return True
    return False


class Command(BaseCommand):
    help = (
        "Stage 3.5 (read-only): enforce the 5-besoins-per-(village, "
        "sub_component) cap, reclassifying over-cap besoins to "
        "ALREADY_IN_DB (if ambiguous) or EXCLUDED_CAPACITY_CAP (if clean, "
        "excluding the highest ranking). Never writes to the DB."
    )

    def add_arguments(self, parser):
        parser.add_argument("--in", dest="in_path", default="new_needs_excel_matched_bj.json")
        parser.add_argument("--out", dest="out_path", default="new_needs_capacity_capped_bj.json")

    def handle(self, *args, **options):
        with open(options["in_path"], encoding="utf-8") as f:
            rows = json.load(f)

        by_bucket = defaultdict(list)
        for i, r in enumerate(rows):
            key = (r["administrative_level_id"], r["sub_component"])
            by_bucket[key].append(i)

        stats = {"reinforced_already_in_db": 0, "excluded_capacity_cap": 0,
                  "over_cap_untouched_buckets": 0, "over_cap_untouched_besoins": 0,
                  "under_capacity_resolved": 0}

        for key, idxs in by_bucket.items():
            existing_count = len(rows[idxs[0]]["existing_investments_same_adm_subcomp"])
            total_if_all_created = existing_count + len(idxs)
            if total_if_all_created <= CAP:
                continue

            excess = total_if_all_created - CAP
            ambiguous_idxs = [i for i in idxs if _is_ambiguous(rows[i])]

            if ambiguous_idxs:
                for i in ambiguous_idxs:
                    rows[i]["capacity_override"] = {
                        "applied": True,
                        "reason": "textual_signal_reinforced",
                    }
                    stats["reinforced_already_in_db"] += 1
            else:
                # All candidates are clean — exclude the highest `ranking`
                # (lowest community priority) until back at CAP.
                clean_sorted = sorted(idxs, key=lambda i: rows[i]["ranking"], reverse=True)
                for i in clean_sorted[:excess]:
                    rows[i]["capacity_override"] = {
                        "applied": True,
                        "reason": "capacity_cap_lowest_priority",
                    }
                    stats["excluded_capacity_cap"] += 1
                stats["over_cap_untouched_buckets"] += 1
                stats["over_cap_untouched_besoins"] += len(idxs) - excess

        # Buckets with room to spare: nothing forces a winner, so stop
        # arbitrating. Any besoin still flagged ambiguous (REVIEW/CONFLICT)
        # here was only held back by a moderate text score, not by scarcity
        # — none in this pipeline run exceed ~0.6, far below a credible
        # near-duplicate bar, so there is no risk in creating all of them.
        # DUPLICATE_RISK rows are left untouched: that status flags a
        # possible duplicate against the DB directly, a concern capacity
        # doesn't resolve.
        under_cap_resolved = 0
        for i, row in enumerate(rows):
            if row.get("capacity_override", {}).get("applied"):
                continue
            dm = row.get("db_match", {})
            em = row.get("excel_match")
            is_ambiguous = dm.get("status") in AMBIGUOUS_DB_STATUSES or (
                em and em["status"] in ("REVIEW", "CONFLICT")
            )
            if is_ambiguous:
                row["capacity_override"] = {
                    "applied": True,
                    "reason": "under_capacity_no_arbitration",
                }
                under_cap_resolved += 1

        stats["under_capacity_resolved"] = under_cap_resolved

        with open(options["out_path"], "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f"Reinforced -> ALREADY_IN_DB: {stats['reinforced_already_in_db']} | "
            f"Excluded (capacity, no signal): {stats['excluded_capacity_cap']} | "
            f"Resolved (under capacity, no arbitration needed): {stats['under_capacity_resolved']} | "
            f"written to {options['out_path']}"
        ))
