import csv
import json
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from investments.sector_aliases import SECTOR_ALIASES


def update_or_create_category_with_sectors(category):
    from administrativelevels.models import Category, Sector
    category_row = Category.objects.get_or_create(name=category["name"], description=category["name"])
    for sector_name in category["sectors"]:
        Sector.objects.get_or_create(name=sector_name, description=sector_name, category=category_row[0])


class Command(BaseCommand):
    help = "Sync categories/sectors from JSON, then update investment sectors using the classified CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Path to the classified CSV file",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the update without modifying the database",
        )
        parser.add_argument(
            "--skip-sync",
            action="store_true",
            help="Skip the categories/sectors sync step and go straight to investment updates",
        )
        parser.add_argument(
            "--sector-column",
            type=str,
            default="sector_name",
            choices=["sub_sector", "sector_name"],
            help="CSV column to use as the sector value (default: sector_name)",
        )

    def sync_categories_and_sectors(self):
        """
        Load categories_sectors.json and create or update all categories and
        their sectors in the database. Safe to run multiple times (idempotent).
        """
        self.stdout.write("\n--- Syncing categories & sectors from JSON ---")
        try:
            json_path = settings.BASE_DIR / "config_data/categories_sectors.json"
            with open(json_path, encoding="utf-8") as f:
                categories = json.load(f)
            for category in categories:
                update_or_create_category_with_sectors(category)
            self.stdout.write(self.style.SUCCESS(f"  Synced {len(categories)} categories.\n"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error syncing categories & sectors: {e}"))
            raise

    def resolve_sector(self, sector_name: str, sector_cache: dict):
        """
        Look up a sector by name in the cache.
        If not found, attempt to resolve it via SECTOR_ALIASES.
        Returns a tuple (Sector instance or None, alias_was_used: bool).
        """
        sector = sector_cache.get(sector_name)
        if sector is not None:
            return sector, False

        canonical_name = SECTOR_ALIASES.get(sector_name)
        if canonical_name:
            sector = sector_cache.get(canonical_name)
            if sector:
                return sector, True

        return None, False

    def handle(self, *args, **options):
        from investments.models import Investment
        from administrativelevels.models import Sector

        csv_file = options["csv_file"]
        dry_run = options["dry_run"]
        skip_sync = options["skip_sync"]
        sector_column = options["sector_column"]

        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN MODE - No changes will be saved ===\n"))

        # Step 1: Sync categories & sectors from JSON
        if skip_sync:
            self.stdout.write("Skipping categories/sectors sync (--skip-sync).\n")
        else:
            self.sync_categories_and_sectors()

        # Step 2: Load rows from the CSV file
        rows = []
        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for row in reader:
                rows.append(row)

        self.stdout.write(f"Rows loaded from CSV      : {len(rows)}")

        # Validate that the expected sector column exists
        if sector_column not in fieldnames:
            self.stdout.write(
                self.style.ERROR(
                    f"Column '{sector_column}' not found in CSV. "
                    f"Available columns: {fieldnames}"
                )
            )
            return

        # Only process rows that have been reclassified (i.e. sector is not 'Autre')
        to_update = [r for r in rows if r[sector_column] not in ("Autre", "")]
        self.stdout.write(f"Rows to update            : {len(to_update)}")
        self.stdout.write(f"Rows skipped ('Autre'/'') : {len(rows) - len(to_update)}\n")

        # Pre-load all sectors into memory to avoid N+1 queries
        sector_cache = {s.name: s for s in Sector.objects.all()}
        self.stdout.write(f"Sectors loaded from DB    : {len(sector_cache)}\n")

        stats = {
            "updated": 0,
            "skipped_not_found_investment": 0,
            "skipped_not_found_sector": 0,
            "skipped_already_correct": 0,
            "alias_resolved": 0,
            "errors": [],
        }

        with transaction.atomic():
            for row in to_update:
                investment_id = row["id"]
                sector_name = row[sector_column]

                # Look up the target sector, falling back to aliases if needed
                sector, alias_used = self.resolve_sector(sector_name, sector_cache)

                if alias_used:
                    stats["alias_resolved"] += 1
                    self.stdout.write(
                        f"  ALIAS resolved: '{sector_name}' -> '{sector.name}'"
                    )

                if not sector:
                    msg = f"Sector not found in database: '{sector_name}' (investment id={investment_id})"
                    self.stdout.write(self.style.WARNING(f"  WARN: {msg}"))
                    stats["skipped_not_found_sector"] += 1
                    stats["errors"].append(msg)
                    continue

                # Look up the investment
                try:
                    investment = Investment.objects.get(pk=investment_id)
                except Investment.DoesNotExist:
                    msg = f"Investment not found: id={investment_id}"
                    self.stdout.write(self.style.WARNING(f"  WARN: {msg}"))
                    stats["skipped_not_found_investment"] += 1
                    stats["errors"].append(msg)
                    continue

                # Skip if the sector is already correct
                if investment.sector_id == sector.pk:
                    stats["skipped_already_correct"] += 1
                    continue

                self.stdout.write(
                    f"  {'[DRY RUN] ' if dry_run else ''}"
                    f"Investment {investment_id}: "
                    f"'{investment.sector.name}' -> '{sector.name}'"
                )

                if not dry_run:
                    investment.sector = sector
                    investment.save(update_fields=["sector"])

                stats["updated"] += 1

            if dry_run:
                # Roll back all changes in dry run mode
                transaction.set_rollback(True)

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"Updated               : {stats['updated']}"))
        self.stdout.write(f"Already correct       : {stats['skipped_already_correct']}")
        self.stdout.write(f"Resolved via alias    : {stats['alias_resolved']}")
        self.stdout.write(self.style.WARNING(f"Sector not found      : {stats['skipped_not_found_sector']}"))
        self.stdout.write(self.style.WARNING(f"Investment not found  : {stats['skipped_not_found_investment']}"))

        if stats["errors"]:
            self.stdout.write(self.style.ERROR(f"\n{len(stats['errors'])} error(s) encountered."))
