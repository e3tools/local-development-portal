import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from administrativelevels.models import Project, AdministrativeLevel, Sector
from investments.models import Investment
from cosomis.constants import STRUCTURE_COMPLETED_STATUS
# from thefuzz import fuzz
from fuzzywuzzy import fuzz
from django.conf import settings
import requests
from django.utils import timezone
from administrativelevels.utils.functions import normalize_text, safe_value, safe_float


    

class Command(BaseCommand):
    help = 'Reads an Excel file and processes it with a given project ID.'

    def add_arguments(self, parser):
        parser.add_argument('project_id', type=int, help='The ID of the project.')
        parser.add_argument('url_default', type=str, help='The default URL of the MIS API.', default=None, nargs='?')

    def handle(self, *args, **kwargs):
        project_id = kwargs['project_id']
        url_default = kwargs.get('url_default', None)
        now = timezone.now()

        try:
            project = Project.objects.get(pk=project_id)
            print(f"Processing project: {project.name}")
        except Project.DoesNotExist:
            raise CommandError(f'Project with ID {project_id} does not exist.')
        
        MIS_API_KEY = settings.MIS_API_KEY
        MIS_URL = settings.MIS_URL

        url = f"{url_default}" if url_default else f"{MIS_URL}/api/subprojects/get-subprojects-simple-by-user/?page_size=1000"

        payload = {
            "token": MIS_API_KEY,
            "infrastructures_status": '__all__',
            'include_inactif': True,
            'project_name': project.name
        }

        headers = {
            "Content-Type": "application/json"
        }

        all_results = []
        links_error = []

        while url:
            response = requests.post(
                url, 
                json=payload, 
                headers=headers
            )
            # response.raise_for_status()
            if response.status_code != 200:
                links_error.append(url)
                self.stdout.write(self.style.ERROR(f"Error fetching data from {url}: {response.status_code} - {response.text}"))
                url = None  # Stop the loop if there's an error
            else:
                data = response.json()
                all_results.extend(data["results"])
                url = data["next"]

        similarity_threshold = 60
        creating = 0
        count = 0
        count_unfunded = 0
        print("Total Structures", len(all_results))
        for subproject in all_results:
            if any(p for p in subproject['projects'] if p['name'] == project.name):
                investment_id = f'{project.name}.{subproject["joint_subproject_number"]}.{subproject["number"]}' # PROJECT_NAME.SUBPROJECT_KIT_NUMBER.NUMBER_INFRASTRUCTURE
                _type_of_structure = subproject["priority"]['priorite'] if safe_value(subproject["priority"]) and safe_value(subproject["priority"]['priorite']) and subproject["priority"]['priorite'] != 'Autre' else subproject["type_of_subproject"]
                type_of_structure = normalize_text(_type_of_structure)
                print(investment_id)

                villages = AdministrativeLevel.objects.filter(
                    name=subproject['location_subproject_realized']['name'],
                    parent__name=subproject['location_subproject_realized']['parent']['name'],
                    parent__parent__name=subproject['location_subproject_realized']['parent']['parent']['name'],
                )
                if villages.exists():
                    investments_linked = Investment.objects.filter(
                        administrative_level=villages.first(),
                        came_from__id=project_id,
                        imported_project_id=investment_id
                    )
                    if investments_linked.exists():
                        matched_investments = list(investments_linked)
                    else:
                        investments_linked = Investment.objects.filter(
                            # imported_project_id__isnull=True, 
                            administrative_level=villages.first(), 
                            came_from__id=project_id,
                        )
                        
                        matched_investments = [
                            invest for invest in investments_linked
                            if fuzz.token_set_ratio(normalize_text(invest.title), type_of_structure) >= similarity_threshold  and (
                                (invest.funded_by and invest.funded_by_id==project_id) or not invest.funded_by
                            )
                        ]
                        
                    matched_investments.sort(key=lambda inv: fuzz.token_set_ratio(normalize_text(inv.title), type_of_structure), reverse=True)
                    
                    if matched_investments:
                        best_match = matched_investments[0]  # The best match based on similarity
                        if subproject['infrastructure_deleted'] != True:
                            if best_match.funded_by:
                                print('Ya esta financiado')
                            best_match.funded_by = project
                            best_match.longitude = subproject['longitude']
                            best_match.latitude = subproject['latitude']
                            best_match.imported_project_id = investment_id
                            
                            physical_execution_rate = subproject.get("current_level_of_physical_realization_of_the_work_percent", 0)
                            if physical_execution_rate:
                                best_match.physical_execution_rate = int(float(physical_execution_rate))
                            else:
                                best_match.physical_execution_rate = 0

                            if subproject["current_status_of_the_site"] == "Identifié":
                                best_match.project_status = "F"
                            elif subproject["current_status_of_the_site"] == "En cours":
                                best_match.project_status = "P"
                            elif not subproject["current_status_of_the_site"]:
                                best_match.project_status = "F"
                            elif subproject["current_status_of_the_site"] == "Arrêt":
                                best_match.project_status = "PA"
                            elif subproject["current_status_of_the_site"] in STRUCTURE_COMPLETED_STATUS:
                                best_match.project_status = "C"
                            else:
                                best_match.project_status = "P"

                            if project:
                                best_match.came_from.add(project)
                            
                            cost = safe_float(subproject["estimated_cost"])
                            if cost:
                                best_match.estimated_cost = cost

                            # best_match.investment_status = Investment.SUBPROJECT
                            best_match.abandoned_in_the_meantime = False
                            best_match.save()

                            count += 1

                        elif best_match.imported_project_id == investment_id:
                            best_match.abandoned_in_the_meantime = True
                            abandonment_history = list(best_match.abandonment_history) if best_match.abandonment_history else []
                            abandonment_history.insert(0, {
                                'abandoned_date': subproject['updated_date'] if 'updated_date' in subproject else now.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                                'funded_by':  ", ".join([p for p in subproject['projects']]),
                                'project_status': str(best_match.project_status),
                                'physical_execution_rate': int(float(best_match.physical_execution_rate)),
                                'imported_project_id': investment_id
                            })
                            best_match.abandonment_history = abandonment_history
                            
                            best_match.funded_by = None
                            best_match.imported_project_id = None
                            best_match.physical_execution_rate = 0
                            best_match.project_status = "N"
                            # best_match.investment_status = Investment.PRIORITY

                            best_match.save()
                            
                            count_unfunded += 1


        for subproject in all_results:
            if subproject['infrastructure_deleted'] != True and any(p for p in subproject['projects'] if p['name'] == project.name):
                investment_id = f'{project.name}.{subproject["joint_subproject_number"]}.{subproject["number"]}' # PROJECT_NAME.SUBPROJECT_KIT_NUMBER.NUMBER_INFRASTRUCTURE
                _type_of_structure = subproject["priority"]['priorite'] if safe_value(subproject["priority"]) and safe_value(subproject["priority"]['priorite']) and subproject["priority"]['priorite'] != 'Autre' else subproject["type_of_subproject"]
                type_of_structure = normalize_text(_type_of_structure)
                print(investment_id)
                
                villages = AdministrativeLevel.objects.filter(
                    name=subproject['location_subproject_realized']['name'],
                    parent__name=subproject['location_subproject_realized']['parent']['name'],
                    parent__parent__name=subproject['location_subproject_realized']['parent']['parent']['name'],
                )
                if villages.exists():

                    investment_already_exists_and_funded = Investment.objects.filter(
                        administrative_level=villages.first(),
                        came_from__id=project_id,
                        imported_project_id=investment_id
                    ).exists()

                    if not investment_already_exists_and_funded:
                        investments_linked = Investment.objects.filter(administrative_level=villages.first(), funded_by=project)
                        matched_investments = [
                            invest for invest in investments_linked
                            if fuzz.token_set_ratio(normalize_text(invest.title), type_of_structure) >= similarity_threshold and (
                            invest.imported_project_id==investment_id or not invest.imported_project_id
                            )
                        ]

                        if not investments_linked or not matched_investments:
                            creating += 1
                            sectors = Sector.objects.all()
                            other_sector = Sector.objects.get(name="Autre")
                            matched_sectors = [
                                sec for sec in sectors
                                if fuzz.token_set_ratio(normalize_text(sec.name), type_of_structure) >= similarity_threshold
                            ]
                            matched_sectors.sort(key=lambda s: fuzz.token_set_ratio(normalize_text(s.name), type_of_structure), reverse=True)
                            
                            cost = safe_float(subproject["estimated_cost"])

                            physical_execution_rate = subproject.get("current_level_of_physical_realization_of_the_work_percent", 0)
                            if physical_execution_rate:
                                physical_execution_rate = int(float(physical_execution_rate))

                            project_status = "P"
                            if subproject["current_status_of_the_site"] == "Identifié":
                                project_status = "F"
                            elif subproject["current_status_of_the_site"] == "En cours":
                                project_status = "P"
                            elif not subproject["current_status_of_the_site"]:
                                project_status = "F"
                            elif subproject["current_status_of_the_site"] == "Arrêt":
                                project_status = "PA"
                            elif subproject["current_status_of_the_site"] in STRUCTURE_COMPLETED_STATUS:
                                project_status = "C"

                            investment_created = Investment.objects.create(
                                title=_type_of_structure,
                                administrative_level=villages.first(),
                                funded_by=project,
                                longitude=subproject['longitude'],
                                latitude=subproject['latitude'],
                                project_status=project_status,
                                sector=matched_sectors[0] if matched_sectors else other_sector,
                                estimated_cost=cost,
                                duration=0,
                                delays_consumed=0,
                                physical_execution_rate=physical_execution_rate if physical_execution_rate else 0,
                                financial_implementation_rate=0,
                                imported_project_id=investment_id,
                                # investment_status=Investment.SUBPROJECT
                            )

                            if project:
                                investment_created.came_from.add(project)
                                investment_created.save()
                else:
                    print("Village not found:", subproject['location_subproject_realized']['name'], subproject['location_subproject_realized']['parent']['name'], investment_id, type_of_structure)


        print(f'Investment found {count}')
        print(f'created amount {creating}')
        print(f'Investment unfunded {count_unfunded}')
        self.stdout.write(self.style.SUCCESS('Successfully processed the Excel file for project ID "%s"' % project_id))