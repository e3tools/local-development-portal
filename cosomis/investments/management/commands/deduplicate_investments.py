from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from investments.models import Investment


class Command(BaseCommand):
    help = 'Remove duplicate investments created by import command'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without touching the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('*** DRY RUN — no data will be deleted ***\n'))

        duplicate_groups = (
            Investment.objects
            .values('title', 'administrative_level', 'ranking', 'description')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        total_groups = duplicate_groups.count()
        self.stdout.write(f'Found {total_groups} duplicate groups\n')

        total_deleted = 0
        anomaly_count = 0

        for group in duplicate_groups:
            instances = Investment.objects.filter(
                title=group['title'],
                administrative_level=group['administrative_level'],
                ranking=group['ranking'],
                description=group['description'],
            ).order_by('id')

            with_sub = instances.exclude(Q(sub_component__isnull=True) | Q(sub_component=''))
            without_sub = instances.filter(Q(sub_component__isnull=True) | Q(sub_component=''))

            # Normal case: one with sub_component, one without → delete the NULL one
            if with_sub.count() == 1 and without_sub.count() >= 1:
                to_delete = without_sub
                if dry_run:
                    self.stdout.write(
                        f'  Would delete {to_delete.count()} duplicate(s) for: "{group["title"]}" '
                        f'(keeping id={with_sub.first().id})'
                    )
                    total_deleted += to_delete.count()
                else:
                    count = to_delete.count()
                    to_delete.delete()
                    total_deleted += count
                    self.stdout.write(f'  Deleted {count} duplicate(s) for: "{group["title"]}"')

            # Both NULL → keep oldest (smallest id), delete the rest
            elif with_sub.count() == 0:
                to_delete = instances.exclude(id=instances.first().id)
                if dry_run:
                    self.stdout.write(
                        f'  Would delete {to_delete.count()} duplicate(s) for: "{group["title"]}" '
                        f'(keeping id={instances.first().id})'
                    )
                    total_deleted += to_delete.count()
                else:
                    count = to_delete.count()
                    to_delete.delete()
                    total_deleted += count
                    self.stdout.write(f'  Deleted {count} duplicate(s) for: "{group["title"]}"')

            # Anomaly: multiple with sub_component filled → apply refined logic
            else:
                anomaly_count += 1
                self.stdout.write(self.style.WARNING(
                    f'\n  [ANOMALY] "{group["title"]}" → {list(instances.values("id", "sub_component"))}'
                ))

                to_delete_ids = []

                # Step 1: delete NULL sub_component instances
                if without_sub.exists():
                    to_delete_ids.extend(without_sub.values_list('id', flat=True))

                # Step 2: among filled, find duplicate sub_component values → keep oldest
                filled_instances = with_sub.order_by('id')
                seen_sub_components = {}
                for instance in filled_instances:
                    if instance.sub_component in seen_sub_components:
                        to_delete_ids.append(instance.id)
                        self.stdout.write(self.style.WARNING(
                            f'    Duplicate sub_component "{instance.sub_component}" → '
                            f'keeping id={seen_sub_components[instance.sub_component]}, deleting id={instance.id}'
                        ))
                    else:
                        seen_sub_components[instance.sub_component] = instance.id

                if not to_delete_ids:
                    self.stdout.write(f'    Nothing to delete, all sub_components are distinct')
                    continue

                to_delete = instances.filter(id__in=to_delete_ids)

                if dry_run:
                    keeping = instances.exclude(id__in=to_delete_ids)
                    self.stdout.write(
                        f'    Would delete {to_delete.count()} instance(s), '
                        f'keeping ids={list(keeping.values_list("id", flat=True))}'
                    )
                    total_deleted += to_delete.count()
                else:
                    count = to_delete.count()
                    to_delete.delete()
                    total_deleted += count
                    self.stdout.write(f'    Deleted {count} instance(s)')

        # Summary
        self.stdout.write('')
        if anomaly_count:
            self.stdout.write(self.style.WARNING(f'{anomaly_count} anomaly group(s) were logged above'))
        summary_style = self.style.WARNING if dry_run else self.style.SUCCESS
        action = 'would be' if dry_run else 'were'
        self.stdout.write(summary_style(f'Total duplicates that {action} deleted: {total_deleted}'))
        if not dry_run:
            self.stdout.write(self.style.SUCCESS('Done.'))