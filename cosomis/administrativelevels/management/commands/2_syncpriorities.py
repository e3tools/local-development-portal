from django.core.management.base import BaseCommand, CommandError
import time
from dateutil import parser
from fuzzywuzzy import fuzz
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from investments.models import Investment, Project
from administrativelevels.models import AdministrativeLevel, Category, Sector
from administrativelevels.libraries.functions import safe_parse_date
from administrativelevels.utils.functions import normalize_text, safe_value

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
        # Your command logic here

        task_name_contain_meeting_date = "Présenter les activités de la journée" # To get the meeting date
        village_priorities_tasks_name = [
            "Soutenir la communauté dans la sélection des priorités par sous-composante (1.1, 1.2 et 1.3) à soumettre à la discussion du CCD lors de la réunion cantonale d'arbitrage", # COSO, FA-COSO
            "Soutenir la communauté dans la sélection des priorités par composante (1, 2 et 3) à soumettre à la discussion du CCD." # PURS
        ]

        self.nsc = NoSQLClient()
        facilitator_dbs = self.nsc.list_all_databases('facilitator')
        for db_name in facilitator_dbs:
            if self.check_for_valid_facilitator(db_name):
                # Getting only priorities tasks validated
                db = self.nsc.get_db(db_name).get_query_result({
                    "type": "task",
                    "phase_name": "PLANIFICATION",
                    "validated": True, # Get only tasks validated
                    "name": {
                        "$in": [task_name_contain_meeting_date] + village_priorities_tasks_name
                    }
                })

                ranking_priority = {
                    "coso": 0,
                    "fa-coso": 1,
                    "purs": 2
                }
                priorities_document = sorted([document for document in db if document.get('name') in village_priorities_tasks_name], key=lambda x: ranking_priority.get(x.get("project_name", "").lower(), 99))
                meeting_dates = {f"{document['administrative_level_id']}_{document['project_name']}": (document['form_response'][0]['dateDeLaReunion'] if document['form_response'] else None) for document in db if document.get('name') == task_name_contain_meeting_date}
                
                print(db_name, len(priorities_document))
                
                for document in priorities_document:
                    update_or_create_priorities_document(document, meeting_dates.get(f"{document['administrative_level_id']}_{document['project_name']}"))
                    
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))



def update_or_create_priorities_document(priorities_document, meeting_date):
    # Extract the administrative_level_id from the priorities document
    adm_id = priorities_document['administrative_level_id']
    similarity_threshold = 60

    administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=adm_id)
    # TODO Complete Sector Allocation
    # Extract priorities from the priorities document
    if 'form_response' in priorities_document:

        if priorities_document.get('form_response'):

            prioritesDuVillage = None
            if 'sousComposante11' in priorities_document['form_response'][0]: # COSO, FA-COSO
                prioritesDuVillage = priorities_document['form_response'][0]['sousComposante11']['prioritesDuVillage']
            elif 'Composante1' in priorities_document['form_response'][0]: # PURS
                prioritesDuVillage = priorities_document['form_response'][0]['Composante1']['prioritesDuVillage']

            if prioritesDuVillage:
                for idx, priority in enumerate(prioritesDuVillage):
                    """
                        Ex. priority
                        priority = {
                            "contributionClimatique": "Réduction de l'abattage anarchique des arbres ", 
                            "coutEstime": 50000000, 
                            "nombreEstimeDeBeneficiaires": 1800, 
                            "priorite": "Autre", 
                            "proposePar": "Hommes et Femmes", 
                            "siAutreVeuillezDecrire": "Clôture de l'EPP Gando centre "
                        }
                    """

                    start_date = None
                    title = priority["priorite"]
                    description = priority["siAutreVeuillezDecrire"]

                    try:
                        start_date = safe_parse_date(meeting_date)
                    except Exception as e:
                        print(e, "Error [date] creating investment", meeting_date, administrative_level, priorities_document['project_name'])
                    
                    try:
                        sector = Sector.objects.get(name=title)
                    except Sector.MultipleObjectsReturned:
                        sector = Sector.objects.filter(name=title).first()
                    except Exception as e:
                        sector = Sector.objects.get(name="Autre")
                        if title != "Autre":
                                description = f"{title} ({description})" if description and str(description).strip() else title
                    
                    try:
                        if title == "Autre":
                            investment = Investment.objects.filter(
                                title=title,
                                administrative_level=administrative_level,
                                # ranking=idx + 1,
                                description=description
                            ).first()
                        else:
                            investment = Investment.objects.filter(
                                title=title,
                                administrative_level=administrative_level,
                                # ranking=idx + 1,
                            ).first()

                        # Handling cases where the infrastructure is already registered without its priority from couchdb CDD | Gestion des cas où l'infrastructure déjà enregistrée sans sa priorité provenant de couchdb CDD
                        if not investment and title != "Autre":
                            adl_investments = Investment.objects.filter(
                                administrative_level=administrative_level,
                                imported_project_id__isnull=False
                            )
                            matched_adl_investments = [
                                adl_investment for adl_investment in adl_investments
                                if fuzz.token_set_ratio(normalize_text(adl_investment.title), normalize_text(title)) >= similarity_threshold
                            ]
                            matched_adl_investments.sort(key=lambda inv: fuzz.token_set_ratio(normalize_text(inv.title), normalize_text(title)), reverse=True)

                            if matched_adl_investments:
                                investment = matched_adl_investments[0]
                                investment.title = title
                                investment.description = description
                                investment.sector = sector
                                if start_date:
                                    investment.start_date = start_date
                                investment.climate_contribution = True if priority.get("contributionClimatique") else False
                                investment.climate_contribution_text = priority.get("contributionClimatique")

                        if not investment:
                            investment = Investment.objects.create(
                                ranking=idx + 1,
                                title=title,
                                description=description,
                                estimated_cost=priority.get("coutEstime"),
                                sector=sector,
                                delays_consumed=0,
                                duration=0,
                                financial_implementation_rate=0,
                                physical_execution_rate=0,
                                administrative_level=administrative_level,
                                start_date=start_date, #priorities_document['form_response'][0]['dateDeLaReunion']
                                # beneficiaries= priority.get("nombreEstimeDeBeneficiaires"),
                                climate_contribution = True if priority.get("contributionClimatique") else False,
                                climate_contribution_text = priority.get("contributionClimatique"),
                            )
                        else:
                            investment.estimated_cost = priority.get("coutEstime")
                            investment.ranking = idx + 1 # Take the rank of the last recorded priority of the recent project
                        
                        project = Project.objects.filter(name=priorities_document['project_name']).first()
                        if project:
                            investment.came_from.add(project)

                            investment.save()

                    except Exception as e:
                        print(e, "Error creating investment", title, administrative_level, priorities_document['project_name'])
    # Otherwise, create a new one
    time.sleep(1)
