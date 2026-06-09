import json
from django.core.management.base import BaseCommand
import time
from no_sql_client import NoSQLClient
from investments.models import Investment
from administrativelevels.models import AdministrativeLevel, Sector, Category
from django.conf import settings

SUB_COMPONENT_FIELDS = {
    "priorisationSC11":  Investment.SUB_COMPONENT_11,
    "priorisationSC12A": Investment.SUB_COMPONENT_12A,
    "priorisationSC12B": Investment.SUB_COMPONENT_12B,
    "priorisationSC13":  Investment.SUB_COMPONENT_13,
}

class Command(BaseCommand):
    help = 'Import investment priorities from NoSQL into Django DB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List investments that would be created without touching the database',
        )

    def check_for_valid_facilitator(self, facilitator):
        db = self.nsc.get_db(facilitator).get_query_result({"type": "facilitator"})
        for document in db:
            try:
                if not document['develop_mode'] and not document["training_mode"]:
                    return True
            except:
                return False
        return False

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('*** DRY RUN — no data will be written ***\n'))

        # Create initial categories & sectors (skipped in dry-run)
        if not dry_run:
            try:
                config_data_file = open(settings.BASE_DIR / 'config_data/categories_sectors.json')
                categories = json.load(config_data_file)
                config_data_file.close()
                for category in categories:
                    update_or_create_category_with_sectors(category)
            except Exception as e:
                print(e, "Error creating initial (categories & sectors) config data")
                return

        # Load categories & sectors mapping
        mappings = None
        try:
            mapping_file = open(settings.BASE_DIR / 'config_data/priority_to_sector_mapping.json')
            mappings = json.load(mapping_file)
            mapping_file.close()
        except Exception as e:
            print(e, "Error loading priority_to_sector_mapping config data")
            return

        self.nsc = NoSQLClient()
        facilitator_dbs = self.nsc.list_all_databases('facilitator')

        total = 0
        for db_name in facilitator_dbs:
            db = self.nsc.get_db(db_name).get_query_result({
                "type": "task",
                "phase_name": "Diagnostic et planification participative",
                "name": "Quatrième Assemblée Générale Villageoise -Pratique de l’Évaluation Participative des Besoins (EPB) - Soutenir la communauté dans la sélection des priorités par sous-composante à soumettre à la discussion au niveau arrondissement"
            })

            for document in db:
                count = update_or_create_priorities_document(
                    document, mappings, dry_run=dry_run, stdout=self.stdout, style=self.style
                )
                total += count

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\nTotal investments that would be created: {total}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully imported {total} investments!'))


def update_or_create_priorities_document(priorities_document, priority_to_sector_mappings, dry_run=False, stdout=None, style=None):
    adm_id = priorities_document['administrative_level_id']
    count = 0

    try:
        administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=adm_id)
    except AdministrativeLevel.DoesNotExist:
        if stdout:
            stdout.write(style.ERROR(f'AdministrativeLevel not found for id: {adm_id}'))
        return 0

    if 'form_response' not in priorities_document or not priorities_document['form_response']:
        return 0

    form = priorities_document['form_response'][0]

    for sc_field, sub_component_value in SUB_COMPONENT_FIELDS.items():
        priorities = form.get(sc_field, [])

        for idx, priority in enumerate(priorities):
            try:
                if priority.get("besoin") is None:
                    continue

                # Clean the data
                priority_name = priority["besoin"].strip().strip("'").replace('\n', '').replace('\t', '')

                if dry_run:
                    stdout.write(
                        f'  [SC {sub_component_value}] #{idx+1} | {administrative_level} | '
                        f'{priority_name} | groupe: {priority.get("groupe", "—")}'
                    )
                    count += 1
                    continue

                exists = Investment.objects.filter(
                    title=priority_name,
                    administrative_level=administrative_level,
                    ranking=idx + 1,
                    description=priority["groupe"],
                    sub_component=sub_component_value,
                ).exists()

                if not exists:
                    sector_name = priority_to_sector_mappings.get(priority_name, 'Autre')
                    sector = Sector.objects.filter(name=sector_name).first()
                    Investment.objects.create(
                        ranking=idx + 1,
                        title=priority_name,
                        description=priority["groupe"],
                        estimated_cost=40000000,
                        sector=sector,
                        delays_consumed=0,
                        duration=0,
                        financial_implementation_rate=0,
                        physical_execution_rate=0,
                        administrative_level=administrative_level,
                        sub_component=sub_component_value,
                        climate_contribution=priority.get('adaptationClimatique') is not None,
                        climate_contribution_text=priority.get('adaptationClimatique') or '',
                    )
                    count += 1

            except Exception as e:
                if stdout:
                    stdout.write(style.ERROR(f'Error on "{priority.get("besoin")}" ({administrative_level}): {e}'))

    if not dry_run:
        time.sleep(1)

    return count


def update_or_create_category_with_sectors(category):
    category_row = Category.objects.get_or_create(name=category["name"], description=category["name"])
    for sector_name in category["sectors"]:
        Sector.objects.get_or_create(name=sector_name, description=sector_name, category=category_row[0])