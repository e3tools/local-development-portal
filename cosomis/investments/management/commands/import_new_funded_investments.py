# investments/management/commands/import_new_funded_investments.py
"""
Import new funded subprojects from the complete COSO dashboard file.

Reads:
  - new_final_matching.xlsx  : MATCHED rows (update existing investments)
  - new_to_create_arbitrage.json : TO_CREATE rows (create new investments)

All investments get project_status=FUNDED_NOT_STARTED.

Usage:
    python manage.py import_new_funded_investments --dry-run
    python manage.py import_new_funded_investments
"""
import json
import os

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from investments.models import Investment
from administrativelevels.models import AdministrativeLevel
from administrativelevels.models import Sector, Category, Project


FUNDED_NOT_STARTED = Investment.FUNDED_NOT_STARTED
SUBPROJECT         = Investment.SUBPROJECT
PRIORITY           = Investment.PRIORITY

# Group name → endorsed_by_* field
GROUP_FIELD_MAP = {
    "Jeunes":                  "endorsed_by_youth",
    "Femmes":                  "endorsed_by_women",
    "Éleveurs et Agriculteurs":"endorsed_by_agriculturist",
    "Minorités ethniques":     "endorsed_by_pastoralist",
    "Notables & Chefferie":    "endorsed_by_chiefs",
}


class Command(BaseCommand):
    help = (
        "Import new funded subprojects (FUNDED_NOT_STARTED) from "
        "new_final_matching.xlsx and new_to_create_arbitrage.json."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--matching-file",
            default="new_final_matching.xlsx",
            help="Path to new_final_matching.xlsx (default: ./new_final_matching.xlsx)",
        )
        parser.add_argument(
            "--to-create-file",
            default="new_to_create_arbitrage.json",
            help="Path to new_to_create_arbitrage.json (default: ./new_to_create_arbitrage.json)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate without writing to the database.",
        )

    def handle(self, *args, **options):
        matching_file  = options["matching_file"]
        to_create_file = options["to_create_file"]
        dry_run        = options["dry_run"]

        for path in [matching_file, to_create_file]:
            if not os.path.exists(path):
                raise CommandError(f"File not found: {path}")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "*** DRY RUN — no changes will be written to the database ***"
            ))

        # ------------------------------------------------------------------ #
        # Load data
        # ------------------------------------------------------------------ #
        df = pd.read_excel(matching_file, dtype=str)
        df = df.fillna("")

        with open(to_create_file, encoding="utf-8") as f:
            to_create_data = json.load(f)

        matched_rows  = df[df["final_status"] == "MATCHED"]
        to_create_rows = df[df["final_status"] == "TO_CREATE"]

        self.stdout.write(
            f"\nMatching file  : {len(df)} rows total — "
            f"{len(matched_rows)} MATCHED, {len(to_create_rows)} TO_CREATE"
        )
        self.stdout.write(
            f"To-create JSON : {len(to_create_data)} rows"
        )

        # ------------------------------------------------------------------ #
        # Pre-load lookups
        # ------------------------------------------------------------------ #
        # Import sector aliases to handle apostrophe variants and name mismatches
        try:
            from investments.sectors_aliases import SECTOR_ALIASES
        except ImportError:
            SECTOR_ALIASES = {}

        def _norm_apos(s):
            """Normalize all apostrophe variants to straight apostrophe U+0027."""
            return s.replace("’", "'").replace("ʼ", "'").replace("‘", "'")

        sectors_by_name = {s.name: s for s in Sector.objects.select_related("category").all()}

        # Build a resolved sectors dict using normalized keys
        # so both U+0027 and U+2019 variants match the same Sector object.
        sectors = {}
        for name, obj in sectors_by_name.items():
            sectors[name] = obj                    # original key
            sectors[_norm_apos(name)] = obj        # normalized key

        # Also add explicit aliases from SECTOR_ALIASES
        for alias, canonical in SECTOR_ALIASES.items():
            canonical_norm = _norm_apos(canonical)
            obj = sectors.get(canonical) or sectors.get(canonical_norm)
            if obj:
                sectors[alias] = obj
                sectors[_norm_apos(alias)] = obj

        categories = {c.name: c for c in Category.objects.all()}

        # Load COSO project (funded_by FK)
        try:
            coso_project = Project.objects.get(name="COSO")
        except Project.DoesNotExist:
            raise CommandError("Project 'COSO' not found in DB. Cannot set funded_by.")
        villages   = {str(v.id): v for v in AdministrativeLevel.objects.filter(type="village")}

        # ------------------------------------------------------------------ #
        # Step 1 — Update MATCHED investments
        # ------------------------------------------------------------------ #
        self.stdout.write(self.style.HTTP_INFO("\n--- Step 1: Update MATCHED investments ---"))

        updated      = 0
        skipped      = 0
        not_found    = 0
        already_done = 0

        for _, row in matched_rows.iterrows():
            db_id = str(row.get("db_id", "")).strip()
            if not db_id:
                skipped += 1
                continue

            try:
                inv = Investment.objects.get(id=db_id)
            except Investment.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f"  [NOT FOUND] investment id={db_id}"
                ))
                not_found += 1
                continue

            # Skip if already processed
            if inv.investment_status == SUBPROJECT and \
               inv.project_status == FUNDED_NOT_STARTED:
                already_done += 1
                continue

            title = str(row.get("import_intitule", "")).strip()
            cout  = str(row.get("cout", "")).strip()
            try:
                cost = float(cout) if cout else None
            except ValueError:
                cost = None

            if dry_run:
                self.stdout.write(
                    f"  [DRY] UPDATE id={db_id} → "
                    f"status=SUBPROJECT/FNS title='{title[:60]}'"
                )
                updated += 1
                continue

            inv.investment_status = SUBPROJECT
            inv.project_status    = FUNDED_NOT_STARTED
            if title:
                inv.title = title
            if cost is not None:
                inv.estimated_cost = cost
            inv.funded_by = coso_project
            inv.save()
            updated += 1

        self.stdout.write(
            f"  Updated: {updated} | Already done: {already_done} | "
            f"Not found: {not_found} | Skipped: {skipped}"
        )

        # ------------------------------------------------------------------ #
        # Step 2 — Create new investments from JSON
        # ------------------------------------------------------------------ #
        self.stdout.write(self.style.HTTP_INFO("\n--- Step 2: Create new investments ---"))

        created      = 0
        already_exists = 0
        errors       = 0

        with transaction.atomic():
            for row in to_create_data:
                village_id = str(row.get("db_village_id", "")).strip()
                sub        = str(row.get("sub_component", "")).strip()
                intitule   = str(row.get("intitule", "")).strip()
                sector_name  = str(row.get("sector", "")).strip()
                category_name = str(row.get("category", "")).strip()
                groupe       = str(row.get("groupe", "")).strip()
                cout         = str(row.get("cout", "")).strip()

                if not village_id:
                    self.stdout.write(self.style.WARNING(
                        f"  [SKIP] No village_id for '{intitule[:60]}'"
                    ))
                    errors += 1
                    continue

                village = villages.get(village_id)
                if not village:
                    self.stdout.write(self.style.ERROR(
                        f"  [NOT FOUND] village id={village_id} for '{intitule[:60]}'"
                    ))
                    errors += 1
                    continue

                # Check duplicate (idempotence)
                existing = Investment.objects.filter(
                    administrative_level=village,
                    sub_component=sub,
                    title__iexact=intitule,
                ).first()
                if existing:
                    already_exists += 1
                    continue

                sector = sectors.get(sector_name) or sectors.get(_norm_apos(sector_name))
                if not sector:
                    self.stdout.write(self.style.WARNING(
                        f"  [SECTOR NOT FOUND] '{sector_name}' for '{intitule[:50]}'"
                    ))

                category = categories.get(category_name)

                try:
                    cost = float(cout) if cout else None
                except ValueError:
                    cost = None

                endorsed_field = GROUP_FIELD_MAP.get(groupe)

                if dry_run:
                    self.stdout.write(
                        f"  [DRY] CREATE village={village.name} sub={sub} "
                        f"sector='{sector_name}' groupe='{groupe}' "
                        f"title='{intitule[:50]}'"
                    )
                    created += 1
                    continue

                kwargs = dict(
                    administrative_level           = village,
                    sub_component                  = sub,
                    title                          = intitule,
                    investment_status              = PRIORITY,
                    project_status                 = FUNDED_NOT_STARTED,
                    funded_by                      = coso_project,
                    estimated_cost                 = cost or 0,
                    sector                         = sector,
                    duration                       = 0,   # NOT NULL, not meaningful for import
                    delays_consumed                = 0,   # NOT NULL, not meaningful for import
                    physical_execution_rate        = 0,   # NOT NULL, not meaningful for import
                    financial_implementation_rate  = 0,   # NOT NULL, not meaningful for import
                    no_sql_id                      = "",  # NOT NULL, not meaningful for import
                )
                if endorsed_field:
                    kwargs[endorsed_field] = True

                inv = Investment.objects.create(**kwargs)
                created += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            f"  Created: {created} | Already exists: {already_exists} | "
            f"Errors: {errors}"
        )

        # ------------------------------------------------------------------ #
        # Summary
        # ------------------------------------------------------------------ #
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(
            f"{'[DRY RUN] ' if dry_run else ''}Done.\n"
            f"  MATCHED updated : {updated}\n"
            f"  TO_CREATE       : {created}\n"
            f"  Already done    : {already_done + already_exists}\n"
            f"  Errors          : {not_found + errors}"
        ))
