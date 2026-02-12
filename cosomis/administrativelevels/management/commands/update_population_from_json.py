import json
from django.core.management.base import BaseCommand
from administrativelevels.models import AdministrativeLevel


class Command(BaseCommand):
    help = 'Update population fields (population_men, population_women, population_young, population_elder) from village_profile_tasks.json'

    def add_arguments(self, parser):
        parser.add_argument(
            '--json-file',
            type=str,
            default='village_profile_tasks.json',
            help='Path to the JSON file containing village profile tasks (default: village_profile_tasks.json)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes to the database'
        )

    def handle(self, *args, **options):
        json_file = options['json_file']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('Running in dry-run mode. No changes will be made.'))

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {json_file}'))
            return
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Invalid JSON file: {e}'))
            return

        updated_count = 0
        not_found_count = 0
        skipped_count = 0

        for record in data:
            adm_id = record.get('Administrative Level ID')
            adm_name = record.get('Administrative Level Name', 'Unknown')

            if not adm_id:
                self.stdout.write(self.style.WARNING(f'Skipping record without Administrative Level ID'))
                skipped_count += 1
                continue

            # Get population values from the JSON, default to 0 if not present
            total_hommes_moins_35 = record.get('totalHommesMoins35', 0) or 0
            total_hommes_plus_35 = record.get('totalHommesPlus35', 0) or 0
            total_femmes_moins_35 = record.get('totalFemmesMoins35', 0) or 0
            total_femmes_plus_35 = record.get('totalFemmesPlus35', 0) or 0

            # Calculate population fields
            population_men = total_hommes_moins_35 + total_hommes_plus_35
            population_women = total_femmes_moins_35 + total_femmes_plus_35
            # population_young = total_hommes_moins_35 + total_femmes_moins_35
            # population_elder = total_hommes_plus_35 + total_femmes_plus_35
            population_young = 0
            population_elder = 0
            total_population = population_men + population_women

            try:
                adm_object = AdministrativeLevel.objects.get(no_sql_db_id=adm_id)

                if not dry_run:
                    adm_object.total_population = total_population
                    adm_object.population_men = population_men
                    adm_object.population_women = population_women
                    adm_object.population_young = population_young
                    adm_object.population_elder = population_elder
                    adm_object.save()

                self.stdout.write(
                    f'{"[DRY-RUN] " if dry_run else ""}Updated {adm_name} (ID: {adm_id}): '
                    f'men={population_men}, women={population_women}, '
                    f'young={population_young}, elder={population_elder}, total={total_population}'
                )
                updated_count += 1

            except AdministrativeLevel.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'Administrative level not found: {adm_name} (ID: {adm_id})'
                ))
                not_found_count += 1
            except AdministrativeLevel.MultipleObjectsReturned:
                self.stdout.write(self.style.WARNING(
                    f'Multiple administrative levels found for ID: {adm_id}'
                ))
                skipped_count += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Summary:'))
        self.stdout.write(f'  Updated: {updated_count}')
        self.stdout.write(f'  Not found: {not_found_count}')
        self.stdout.write(f'  Skipped: {skipped_count}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a dry run. Run without --dry-run to apply changes.'))
        else:
            self.stdout.write(self.style.SUCCESS('\nPopulation update completed successfully!'))