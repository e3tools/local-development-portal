from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from investments.models import Investment


# Mapping: field name -> (exact values, keyword fallbacks)
# Exact match is tried first; if description doesn't match exactly,
# keyword search is used as a fallback to cover free-text descriptions.
ENDORSEMENT_RULES = [
    (
        'endorsed_by_youth',
        ['Jeunes'],
        ['jeunes', 'jeunesse', 'youth'],
    ),
    (
        'endorsed_by_women',
        ['Femmes'],
        ['femmes', 'femme', 'women'],
    ),
    (
        'endorsed_by_agriculturist',
        ['Éleveurs et Agriculteurs'],
        ['éleveurs', 'agriculteurs', 'farmers'],
    ),
    (
        'endorsed_by_pastoralist',
        ['Minorités ethniques'],
        ['minorités ethniques', 'minorité', 'pastoralist', 'peulh'],
    ),
    (
        'endorsed_by_chiefs',
        ['Notables & Chefferie'],
        ['chefferie', 'notables', 'chiefs'],
    ),
]


class Command(BaseCommand):
    help = (
        'Populate endorsed_by_* boolean fields from the description field. '
        'Tries exact match first, falls back to keyword search.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate without writing to the database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('*** DRY RUN — no changes will be saved ***'))

        stats = {field: 0 for field, _, _ in ENDORSEMENT_RULES}
        total_updated = 0

        with transaction.atomic():
            # Process all investments that have a non-empty description
            qs = Investment.objects.exclude(
                description__isnull=True
            ).exclude(description='')

            self.stdout.write(f'Processing {qs.count()} investments with description...')

            for field, exact_values, keywords in ENDORSEMENT_RULES:
                # Build exact match Q
                exact_q = Q()
                for val in exact_values:
                    exact_q |= Q(description__iexact=val)

                # Build keyword fallback Q
                keyword_q = Q()
                for kw in keywords:
                    keyword_q |= Q(description__icontains=kw)

                # Match either exact or keyword
                matched_qs = qs.filter(exact_q | keyword_q).exclude(
                    **{field: True}  # skip already-set
                )
                count = matched_qs.count()
                stats[field] = count

                if not dry_run:
                    matched_qs.update(**{field: True})

                self.stdout.write(
                    f'  {field}: {count} investments '
                    f'{"would be " if dry_run else ""}updated'
                )

            total_updated = sum(stats.values())

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(
            f'Done {"(DRY RUN) " if dry_run else ""}'
            f'— {total_updated} endorsement flags set across all fields'
        ))
