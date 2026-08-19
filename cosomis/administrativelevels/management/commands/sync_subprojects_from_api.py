import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q, Count
from administrativelevels.models import Project, AdministrativeLevel, Sector, Component
from investments.models import Investment
from cosomis.constants import STRUCTURE_COMPLETED_STATUS
# from thefuzz import fuzz
from fuzzywuzzy import fuzz
from django.conf import settings
import requests
from django.utils import timezone
from administrativelevels.utils.functions import normalize_text, safe_value, safe_float, strip_accents
from administrativelevels.management.commands.__init__ import TYPE_OF_STRUCTURES_TO_PRIORITY_CATEGORY_IGNORE_ACCENTS
from administrativelevels.management.commands.priorities_sync_helpers import find_or_create_group_investment, AdministrativeLevelIndex
from cosomis.constants import IGNORES, IGNORES_SPECIALS_CASE
    

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
        imported_project_ids_found = set()
        villages_not_found = set()
        print("Total Structures", len(all_results))
        for subproject in all_results:
            if any(p for p in subproject['projects'] if p['name'] == project.name):
                investment_id = f'{project.name}.{subproject["joint_subproject_number"]}.{subproject["number"]}' # PROJECT_NAME.SUBPROJECT_KIT_NUMBER.NUMBER_INFRASTRUCTURE
                _type_of_structure = subproject["priority"]['priorite'] if safe_value(subproject["priority"]) and safe_value(subproject["priority"]['priorite']) and subproject["priority"]['priorite'] != 'Autre' else subproject["type_of_subproject"]
                type_of_structure = normalize_text(_type_of_structure)
                print(investment_id)
                _suproject_component = subproject["component"]['name']
                _suproject_component_alias = [_suproject_component, f"Sous-{_suproject_component}"]
                name_queries = Q()
                for alias in _suproject_component_alias:
                    name_queries |= Q(name__iexact=alias)

                component = Component.objects.filter(
                    name_queries | Q(short_name__iexact=subproject["component"]['name'].split(' ')[-1]),
                    project=project
                ).first()

                villages = AdministrativeLevel.objects.filter(
                    name=subproject['location_subproject_realized']['name'],
                    parent__name=subproject['location_subproject_realized']['parent']['name'],
                    parent__parent__name=subproject['location_subproject_realized']['parent']['parent']['name'],
                )
                if villages.exists():
                    investments_linked = Investment.objects.filter(
                        Q(component__isnull=True) | Q(component=component),
                        administrative_level=villages.first(),
                        came_from__id=project_id,
                        imported_project_id=investment_id
                    )
                    if investments_linked.exists():
                        matched_investments = list(investments_linked)
                    else:
                        investments_linked = Investment.objects.filter(
                            Q(component__isnull=True) | Q(component=component),
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

                        sector_find = Sector.objects.filter(name=TYPE_OF_STRUCTURES_TO_PRIORITY_CATEGORY_IGNORE_ACCENTS.get(strip_accents(_type_of_structure))).first()
                        if sector_find and sector_find.name:
                            best_match.sector = sector_find

                        #Whose choice this subproject?
                        if subproject.get("women_s_group"):
                            best_match.endorsed_by_women = True
                        if subproject.get("youth_group"):
                            best_match.endorsed_by_youth = True
                        if subproject.get("breeders_farmers_group"):
                            best_match.endorsed_by_agriculturist = True
                        if subproject.get("ethnic_minority_group"):
                            best_match.endorsed_by_pastoralist = True
                        if subproject.get("refugee_and_internally_displaced_persons_group"):
                            best_match.endorsed_by_displaced = True

                        best_match.component = component
                        if not best_match.description:
                            best_match.description = subproject['full_title_of_approved_subproject'] if subproject['full_title_of_approved_subproject'] not in (IGNORES + IGNORES_SPECIALS_CASE) else None
                        
                        if component and str(component.short_name).lower() == "1.2a".lower():
                            adm_index = AdministrativeLevelIndex()
                            group_investment = find_or_create_group_investment(
                                adm_index, 
                                subproject["full_title_of_approved_subproject"], 
                                best_match.administrative_level.name, 
                                best_match.administrative_level, 
                                component, 
                                project,
                            )
                            if group_investment:
                                if not group_investment.administrative_level or not group_investment.lieu:
                                    if not group_investment.administrative_level:
                                        group_investment.administrative_level = best_match.administrative_level.parent
                                    if not group_investment.lieu:
                                        group_investment.lieu = best_match.administrative_level
                                    group_investment.save()
                                best_match.group_investment = group_investment

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
                            imported_project_ids_found.add(investment_id)

                            count += 1

                        elif best_match.imported_project_id == investment_id:
                            best_match.abandoned_in_the_meantime = True
                            abandonment_history = list(best_match.abandonment_history) if best_match.abandonment_history else []
                            abandonment_history.insert(0, {
                                'abandoned_date': subproject['updated_date'] if 'updated_date' in subproject else now.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                                'funded_by':  ", ".join([p['name'] if type(p) == dict and 'name' in p else p for p in subproject['projects']]),
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
                
                else:
                    print("Village not found:", subproject['location_subproject_realized']['name'], subproject['location_subproject_realized']['parent']['name'], investment_id, type_of_structure)
                    villages_not_found.add((subproject['location_subproject_realized']['name'], subproject['location_subproject_realized']['parent']['name'], investment_id, type_of_structure))
                


        for subproject in all_results:
            if subproject['infrastructure_deleted'] != True and any(p for p in subproject['projects'] if p['name'] == project.name):
                investment_id = f'{project.name}.{subproject["joint_subproject_number"]}.{subproject["number"]}' # PROJECT_NAME.SUBPROJECT_KIT_NUMBER.NUMBER_INFRASTRUCTURE
                _type_of_structure = subproject["priority"]['priorite'] if safe_value(subproject["priority"]) and safe_value(subproject["priority"]['priorite']) and subproject["priority"]['priorite'] != 'Autre' else subproject["type_of_subproject"]
                type_of_structure = normalize_text(_type_of_structure)
                print(investment_id)
                _suproject_component = subproject["component"]['name']
                _suproject_component_alias = [_suproject_component, f"Sous-{_suproject_component}"]
                name_queries = Q()
                for alias in _suproject_component_alias:
                    name_queries |= Q(name__iexact=alias)

                component = Component.objects.filter(
                    name_queries | Q(short_name__iexact=subproject["component"]['name'].split(' ')[-1]),
                    project=project
                ).first()
                
                villages = AdministrativeLevel.objects.filter(
                    name=subproject['location_subproject_realized']['name'],
                    parent__name=subproject['location_subproject_realized']['parent']['name'],
                    parent__parent__name=subproject['location_subproject_realized']['parent']['parent']['name'],
                )
                if villages.exists():

                    investment_already_exists_and_funded = Investment.objects.filter(
                        Q(component__isnull=True) | Q(component=component),
                        administrative_level=villages.first(),
                        came_from__id=project_id,
                        imported_project_id=investment_id
                    ).exists()

                    if not investment_already_exists_and_funded:
                        investments_linked = Investment.objects.filter(
                            Q(component__isnull=True) | Q(component=component),
                            administrative_level=villages.first(), funded_by=project
                        )
                        matched_investments = [
                            invest for invest in investments_linked
                            if fuzz.token_set_ratio(normalize_text(invest.title), type_of_structure) >= similarity_threshold and (
                            invest.imported_project_id==investment_id or not invest.imported_project_id
                            )
                        ]

                        if not investments_linked or not matched_investments:
                            creating += 1

                            sector_find = Sector.objects.filter(name=TYPE_OF_STRUCTURES_TO_PRIORITY_CATEGORY_IGNORE_ACCENTS.get(strip_accents(_type_of_structure))).first()
                            if sector_find and sector_find.name:
                                matched_sectors = [sector_find]
                            else:
                                sectors = Sector.objects.all()
                                other_sector = Sector.objects.get(name="Autre")
                                matched_sectors = [
                                    sec for sec in sectors
                                    if fuzz.token_set_ratio(normalize_text(sec.name), type_of_structure) >= similarity_threshold
                                ]
                                matched_sectors.sort(key=lambda s: fuzz.token_set_ratio(normalize_text(s.name), type_of_structure), reverse=True)

                            group_investment = None
                            if component and str(component.short_name).lower() == "1.2a".lower():
                                adm_index = AdministrativeLevelIndex()
                                group_investment = find_or_create_group_investment(
                                    adm_index, 
                                    subproject["full_title_of_approved_subproject"], 
                                    best_match.administrative_level.name, 
                                    best_match.administrative_level, 
                                    component, 
                                    project,
                                )
                                if group_investment:
                                    if not group_investment.administrative_level or not group_investment.lieu:
                                        if not group_investment.administrative_level:
                                            group_investment.administrative_level = best_match.administrative_level.parent
                                        if not group_investment.lieu:
                                            group_investment.lieu = best_match.administrative_level
                                        group_investment.save()

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
                                description=subproject['full_title_of_approved_subproject'] if subproject['full_title_of_approved_subproject'] not in (IGNORES + IGNORES_SPECIALS_CASE) else None,
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
                                component=component,
                                group_investment=group_investment,
                                # investment_status=Investment.SUBPROJECT
                                
                                #Whose choice this subproject?
                                endorsed_by_women = True if subproject.get("women_s_group") else False,
                                endorsed_by_youth = True if subproject.get("youth_group") else False,
                                endorsed_by_agriculturist = True if subproject.get("breeders_farmers_group") else False,
                                endorsed_by_pastoralist = True if subproject.get("ethnic_minority_group") else False,
                                endorsed_by_displaced = True if subproject.get("refugee_and_internally_displaced_persons_group") else False
                            )

                            if project:
                                investment_created.came_from.add(project)
                                investment_created.save()

                            imported_project_ids_found.add(investment_id)

                else:
                    print("Village not found:", subproject['location_subproject_realized']['name'], subproject['location_subproject_realized']['parent']['name'], investment_id, type_of_structure)
                    villages_not_found.add((subproject['location_subproject_realized']['name'], subproject['location_subproject_realized']['parent']['name'], investment_id, type_of_structure))

        print(f'Investment found {count}')
        print(f'created amount {creating}')
        print(f'Investment unfunded {count_unfunded}')
        print(f'Villages not found {len(villages_not_found)} : {villages_not_found}')
        self.stdout.write(self.style.SUCCESS('Successfully processed the Excel file for project ID "%s"' % project_id))

        print()
        self.stdout.write(self.style.WARNING('Checking duplicated "duplicated_imported_id"...'))
        duplicated_imported_ids = (
            Investment.objects.exclude(imported_project_id__isnull=True)
            .exclude(imported_project_id='')
            .values_list('imported_project_id', flat=True)
            .annotate(total=Count('id'))
            .filter(total__gt=1)
        )
        self.stdout.write(self.style.WARNING(f'{len(duplicated_imported_ids)} duplication found'))
        for investment_multiple_object in duplicated_imported_ids:
            investments_multiple_objects = Investment.objects.filter(
                imported_project_id=investment_multiple_object
            ).order_by('created_date')
            _last = investments_multiple_objects.last()
            # Delete Old/First Investment
            investments_multiple_objects.exclude(id=_last.id).delete()
        if duplicated_imported_ids:
            self.stdout.write(self.style.SUCCESS(f"Deleted { len(duplicated_imported_ids) } Investment with multiple objects"))

        print()
        self.stdout.write(self.style.WARNING(f'Checking phantom investments (imported_project_id not found in the API for the {project.name} project)...'))
        phantom_investments = (
            Investment.objects
                .filter(came_from__id=project_id)
                .exclude(Q(imported_project_id__isnull=True) | Q(imported_project_id__in=imported_project_ids_found))
        )
        self.stdout.write(self.style.WARNING(f'{phantom_investments.count()} phantom investments found'))
        if phantom_investments:
            phantom_investments.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {phantom_investments.count()} phantom investments Successfully!"))


        print()
        self.stdout.write(self.style.WARNING('Last once checking duplication Investments not funded...'))
        duplicated_list = (
            Investment.objects
            .filter(funded_by__isnull=True, component__isnull=False)
            .values_list('title', 'administrative_level__id', 'description', 'component__id')
            .annotate(total=Count('id'))
            .filter(total__gt=1)
        )
        self.stdout.write(self.style.WARNING(f'{len(duplicated_list)} duplication found'))
        for investment_multiple in duplicated_list:
            investments_multiple_objects = Investment.objects.filter(
                title=investment_multiple[0], 
                administrative_level__id=investment_multiple[1], 
                description=investment_multiple[2], 
                component__id=investment_multiple[3]
            ).order_by('created_date')
            _last = investments_multiple_objects.last()
            # Delete Old/First Investment
            investments_multiple_objects.exclude(id=_last.id).delete()
        if duplicated_list:
            self.stdout.write(self.style.SUCCESS(f"Deleted { len(duplicated_list) } Investments duplicated"))