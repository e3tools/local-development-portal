from django.core.management.base import BaseCommand
from django.db import transaction

from investments.models import Investment
from investments.constants import (
    SECTOR_ESTIMATED_COSTS,
    DEFAULT_ESTIMATED_COST,
)


class Command(BaseCommand):
    help = "Update estimated_cost of investments based on their sector"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show changes without updating database",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        updated = 0
        missing = []

        invests = Investment.objects.select_related("sector")

        with transaction.atomic():
            for investment in invests:
                sector_name = investment.sector.name
                estimated_cost = SECTOR_ESTIMATED_COSTS.get(
                    sector_name, DEFAULT_ESTIMATED_COST
                )

                if sector_name not in SECTOR_ESTIMATED_COSTS:
                    missing.append(sector_name)

                if not dry_run:
                    investment.estimated_cost = estimated_cost
                    investment.save(update_fields=["estimated_cost"])

                updated += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"{updated} investments processed"
        ))

        if missing:
            self.stdout.write(self.style.WARNING(
                f"Sectors without explicit cost: {set(missing)}"
            ))
