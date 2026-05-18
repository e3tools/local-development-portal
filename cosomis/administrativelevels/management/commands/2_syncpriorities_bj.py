import json
from django.core.management.base import BaseCommand
import time
from no_sql_client import NoSQLClient
from investments.models import Investment
from administrativelevels.models import AdministrativeLevel, Sector, Category
from django.conf import settings

class Command(BaseCommand):
    help = 'Description of your command'

    def check_for_valid_facilitator(self, facilitator):
        db = self.nsc.get_db(facilitator).get_query_result({
            "type": "facilitator"
        })
        for document in db:
            try:
                if not document['develop_mode'] and not document["training_mode"]:
                    # print("Facilitator is valid", document)
                    return True
            except:
                return False
        return False

    def handle(self, *args, **options):
        # Create initial categories & sectors
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
            print(e, "Error creating initial (categories & sectors) config data")
            return

        # Your command logic here
        self.nsc = NoSQLClient()
        facilitator_dbs = self.nsc.list_all_databases('facilitator')

        for db_name in facilitator_dbs:
            db = self.nsc.get_db(db_name).get_query_result({
                    "type": "task",
                    "phase_name": "Diagnostic et planification participative",
                    "name": "Quatrième Assemblée Générale Villageoise -Pratique de l’Évaluation Participative des Besoins (EPB) - Soutenir la communauté dans la sélection des priorités par sous-composante à soumettre à la discussion au niveau arrondissement"
                })

            for document in db:
                update_or_create_priorities_document(document, mappings)
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))



def update_or_create_priorities_document(priorities_document, priority_to_sector_mappings):
    # Extract the administrative_level_id from the priorities document
    adm_id = priorities_document['administrative_level_id']

    administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=adm_id)
    # TODO Complete Sector Allocation
    # Extract priorities from the priorities document
    if 'form_response' in priorities_document:
        if priorities_document.get('form_response') and 'priorisationSC11' in priorities_document['form_response'][0]:
            for idx, priority in enumerate(
                    priorities_document['form_response'][0]['priorisationSC11']):
                try:
                    if priority["besoin"] is None:
                        continue

                    # clean the data
                    priority_name = priority["besoin"].strip()
                    priority_name = priority_name.strip("'")
                    priority_name = priority_name.replace('\n', '')
                    priority_name = priority_name.replace('\t', '')

                    exist = Investment.objects.filter(
                        title=priority_name,
                        administrative_level=administrative_level,
                        ranking=idx + 1,
                        description=priority["groupe"]
                    ).exists()
                    if not exist:
                        sector_name = priority_to_sector_mappings.get(priority_name, 'Autre')
                        sector = Sector.objects.filter(name=sector_name).first()
                        Investment.objects.create(
                            ranking=idx + 1,
                            title=priority_name,
                            description=priority["groupe"],
                            estimated_cost=40000000,  #TODO: use priority.get("coutEstime", 0),
                            sector=sector,
                            delays_consumed=0,
                            duration=0,
                            financial_implementation_rate=0,
                            physical_execution_rate=0,
                            administrative_level=administrative_level,
                            climate_contribution=False if priority.get('adaptationClimatique') is None else True,
                            climate_contribution_text='' if priority.get('adaptationClimatique') is None else priority.get('adaptationClimatique')
                            # start_date=priorities_document['form_response'][0]['dateDeLaReunion']
                            # beneficiaries= priority.get("nombreEstimeDeBeneficiaires"),
                        )
                except Exception as e:
                    print(e, "Error creating investment", priority["besoin"], administrative_level)
    # Otherwise, create a new one
    time.sleep(1)

def update_or_create_category_with_sectors(category):
    category_row = Category.objects.get_or_create(name=category["name"], description=category["name"])
    for sector_name in category["sectors"]:
        Sector.objects.get_or_create(name=sector_name, description=sector_name, category=category_row[0])
