import time

from django.core.management.base import BaseCommand
from django.db.models import Count
from no_sql_client import NoSQLClient
from investments.models import Investment, Project
from administrativelevels.models import AdministrativeLevel
from administrativelevels.libraries.functions import safe_parse_date
from administrativelevels.management.commands.priorities_sync_helpers import (
    AdministrativeLevelIndex,
    apply_endorsements,
    ensure_predefined_groupes_socioeconomiques,
    find_cdd_imported_investment,
    find_existing_flat_investment,
    find_matching_groupes_socioeconomiques,
    find_or_create_group_investment,
    find_or_create_group_investment_item,
    get_or_create_component,
    mark_synced,
    parse_document_date,
    resolve_sector,
    should_skip_for_sync_date,
    PRIORITE_11_TO_CATEGORY,
    PRIORITE_13_TO_CATEGORY,
    PRIORITE_PURS_C1_TO_CATEGORY,
    PRIORITE_PURS_C2_TO_CATEGORY,
    PRIORITE_PURS_C3_TO_CATEGORY,
)
from cosomis.constants import IGNORES, IGNORES_SPECIALS_CASE


class Command(BaseCommand):
    help = 'Sync village priorities (sous-composantes 1.1/1.2a/1.2b/1.3 - COSO/FA-COSO, Composante1/2/3 - PURS)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ignore-sync-date', action='store_true', default=False,
            help=(
                "Force la mise à jour d'un Investment même si le document traité "
                "est plus ancien que la dernière synchronisation déjà appliquée "
                "(last_sync). Par défaut, ces documents plus anciens sont ignorés."
            ),
        )

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
        is_considerate_sync_date = not options.get('ignore_sync_date', False)

        task_name_contain_meeting_date = "Présenter les activités de la journée" # To get the meeting date
        village_priorities_tasks_name = [
            "Soutenir la communauté dans la sélection des priorités par sous-composante (1.1, 1.2 et 1.3) à soumettre à la discussion du CCD lors de la réunion cantonale d'arbitrage", # COSO, FA-COSO
            "Soutenir la communauté dans la sélection des priorités par composante (1, 2 et 3) à soumettre à la discussion du CCD." # PURS
        ]

        ensure_predefined_groupes_socioeconomiques()
        adm_index = AdministrativeLevelIndex()

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
                    # try:
                        sync_priorities_document(
                            document,
                            meeting_dates.get(f"{document['administrative_level_id']}_{document['project_name']}"),
                            adm_index,
                            is_considerate_sync_date,
                        )
                    # except Exception as e:
                    #     print(e, "Error syncing priorities document", document.get('project_name'), document.get('administrative_level_name'), document.get('administrative_level_id'))

        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))

        print()
        self.stdout.write(self.style.WARNING('Checking duplicated by project...'))
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


# Libellé + place dans la hiérarchie (Composante 1 > Sous-composante) de chaque
# clé du form_response. Les composantes PURS sont déjà "top-level".
COMPONENT_LABELS = {
    'sousComposante11': 'Sous-composante 1.1',
    'sousComposante12a': 'Sous-composante 1.2a',
    'sousComposante12b': 'Sous-composante 1.2b',
    'sousComposante13': 'Sous-composante 1.3',
    'Composante1': 'Composante 1',
    'Composante2': 'Composante 2',
    'Composante3': 'Composante 3',
}
SOUS_COMPOSANTE_KEYS = {'sousComposante11', 'sousComposante12a', 'sousComposante12b', 'sousComposante13'}

# Sous-composantes/composantes qui listent des priorités "à plat" (un array
# d'objets {priorite, proposePar, coutEstime, nombreEstimeDeBeneficiaires, ...})
# et deviennent chacune un Investment classique, comme le fait déjà 1.1 aujourd'hui.
FLAT_COMPONENT_CONFIG = {
    'sousComposante11': {
        'sector_map': PRIORITE_11_TO_CATEGORY,
        'default_category': 'Autre',
        'contribution_field': 'contributionClimatique',
        'is_climate': True,
    },
    'sousComposante13': {
        'sector_map': PRIORITE_13_TO_CATEGORY,
        'default_category': 'Jeunesse',
        'contribution_field': 'contributionClimatique',
        'is_climate': True,
        'force_youth': True,
    },
    'Composante1': {
        'sector_map': PRIORITE_PURS_C1_TO_CATEGORY,
        'default_category': 'Autre',
        'contribution_field': 'contributionClimatique',
        'is_climate': True,
    },
    'Composante2': {
        'sector_map': PRIORITE_PURS_C2_TO_CATEGORY,
        'default_category': 'Appui économique',
        'contribution_field': 'contributionEconomique',
        'is_climate': False,
        'extra_note_field': 'groupementsConcernes',
    },
    'Composante3': {
        'sector_map': PRIORITE_PURS_C3_TO_CATEGORY,
        'default_category': 'Sécurité et gouvernance',
        'contribution_field': 'contributionSecurite',
        'is_climate': False,
    },
}


def get_component_for_key(project, key):
    label = COMPONENT_LABELS.get(key)
    if not label:
        return None
    if key in SOUS_COMPOSANTE_KEYS:
        parent = get_or_create_component(project, 'Composante 1')
        return get_or_create_component(project, label, parent=parent)
    return get_or_create_component(project, label)


def sync_priorities_document(priorities_document, meeting_date, adm_index, is_considerate_sync_date=True):
    adm_id = priorities_document['administrative_level_id']

    try:
        administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=adm_id)
    except AdministrativeLevel.DoesNotExist:
        print("Administrative level not found", adm_id, priorities_document.get('project_name'))
        return

    project = Project.objects.filter(name=priorities_document.get('project_name')).first()
    document_date = parse_document_date(priorities_document)

    start_date = None
    try:
        start_date = safe_parse_date(meeting_date)
    except Exception as e:
        print(e, "Error [date] creating investment", meeting_date, administrative_level, priorities_document.get('project_name'))

    if start_date:
        administrative_level.identified_priority = start_date
        administrative_level.save()

    for entry in priorities_document.get('form_response') or []:
        for key, payload in entry.items():
            if not payload:
                continue
            component = get_component_for_key(project, key)
            if key in FLAT_COMPONENT_CONFIG:
                sync_flat_priorities(
                    payload, administrative_level, component, project, start_date,
                    document_date, is_considerate_sync_date, FLAT_COMPONENT_CONFIG[key],
                )
            elif key == 'sousComposante12a':
                sync_market_priorities(
                    payload, administrative_level, component, project,
                    document_date, is_considerate_sync_date, adm_index,
                )
            elif key == 'sousComposante12b':
                sync_socioeconomic_needs(
                    payload, administrative_level, component, project,
                    document_date, is_considerate_sync_date,
                )

    time.sleep(1)


def sync_flat_priorities(payload, administrative_level, component, project, start_date,
                          document_date, is_considerate_sync_date, config):
    """Sous-composantes 1.1/1.3 (COSO/FA-COSO) et Composante1/2/3 (PURS) : un
    array de priorités chiffrées, chacune devenant un Investment."""
    items = payload.get('prioritesDuVillage') or payload.get('classement') or []

    for idx, priority in enumerate(items):
        priorite_value = priority.get('priorite')
        if not priorite_value:
            continue

        category_name = config['sector_map'].get(priorite_value, config['default_category'])
        sector = resolve_sector(priorite_value, category_name)

        # FA-COSO ajoute IntituleDuSousprojet (avec parfois un espace de trop
        # dans la clé JSON selon le document) comme intitulé libre du sous-projet.
        intitule = priority.get('IntituleDuSousprojet') or priority.get('IntituleDuSousprojet ')
        intitule = intitule if intitule and intitule.strip() not in (IGNORES+IGNORES_SPECIALS_CASE) else None

        description = priority.get('siAutreVeuillezDecrire')
        description = description if description and description.strip() not in IGNORES else intitule

        title = ((priorite_value if priorite_value != 'Autre' else intitule) or '').strip() or priorite_value

        # Sans intitulé libre, plusieurs priorités "Autre" du même village
        # partagent le même title générique : la description les distingue.
        disambiguate = priorite_value == 'Autre' and not intitule

        investment = find_existing_flat_investment(
            administrative_level, component, title, description, disambiguate,
        )
        if investment and should_skip_for_sync_date(investment, document_date, is_considerate_sync_date):
            continue

        if not investment and priorite_value != 'Autre':
            cdd_match = find_cdd_imported_investment(administrative_level, sector, title)
            if cdd_match:
                investment = cdd_match

        if not investment:
            investment = Investment(
                administrative_level=administrative_level,
                investment_status=Investment.PRIORITY,
                delays_consumed=0, duration=0,
                financial_implementation_rate=0, physical_execution_rate=0,
                no_sql_id='',
            )

        investment.title = title
        investment.description = description
        investment.sector = sector
        investment.component = component
        investment.ranking = idx + 1
        investment.estimated_cost = priority.get('coutEstime')
        investment.beneficiaries = priority.get('nombreEstimeDeBeneficiaires')
        if start_date:
            investment.start_date = start_date

        contribution_text = priority.get(config['contribution_field'])
        extra_note_field = config.get('extra_note_field')
        if extra_note_field:
            extra_note = priority.get(extra_note_field)
            if extra_note and str(extra_note).strip().lower() not in ['', 'neant', 'néant'] + list(IGNORES):
                note = f"{extra_note_field}: {extra_note}"
                contribution_text = f"{contribution_text}\n{note}" if contribution_text else note
        investment.climate_contribution_text = contribution_text
        investment.climate_contribution = bool(contribution_text) and config.get('is_climate', False)

        apply_endorsements(investment, priority.get('proposePar'), reset=True)
        if config.get('force_youth'):
            investment.endorsed_by_youth = True

        mark_synced(investment, document_date)
        investment.save()

        if project:
            investment.came_from.add(project)

        investment.save()


def sync_market_priorities(payload, administrative_level, component, project,
                            document_date, is_considerate_sync_date, adm_index):
    """Sous-composante 1.2a : le marché cantonal le plus important pour le
    village et les équipements/infrastructures qu'il y souhaite."""
    nom_marche = payload.get('nomDuMarcheLePlusImportant')
    if not nom_marche:
        return
    lieu_marche = payload.get('lieuDuMarcheLePlusImportant')
    propose_par = payload.get('proposePar')  # absent selon les documents

    group_investment = find_or_create_group_investment(
        adm_index, nom_marche, lieu_marche, administrative_level, component, project,
    )
    if not group_investment:
        return

    for idx, item in enumerate(payload.get('typesInfrastructuresEtEquipements') or []):
        label = item.get('typeDeDeveloppement')
        if not label:
            continue
        investment = find_or_create_group_investment_item(
            group_investment, label, idx + 1, component, administrative_level,
        )
        if not investment:
            continue
        if should_skip_for_sync_date(investment, document_date, is_considerate_sync_date):
            continue

        # Les groupes ayant proposé les équipements de ce marché sont répliqués
        # sur chaque Investment (endorsement cumulatif, pas remplacé).
        apply_endorsements(investment, propose_par, reset=False)
        investment.administrative_levels.add(administrative_level)
        mark_synced(investment, document_date)
        investment.save()

        if project:
            investment.came_from.add(project)

        investment.save()

    group_investment.refresh_ranking()


def sync_socioeconomic_needs(payload, administrative_level, component, project,
                              document_date, is_considerate_sync_date):
    """Sous-composante 1.2b : les besoins socio-économiques et de renforcement
    de capacités des groupes économiques du village deviennent chacun un
    Investment, rattaché (si possible) au(x) groupe(s) socio-économique(s)
    concerné(s)."""
    village_group_names = [
        g.get('principalGroupeSocioeconomique')
        for g in payload.get('principauxGroupesSocioeconomiques') or []
        if g.get('principalGroupeSocioeconomique')
    ]
    contribution_text = payload.get('contributionClimatique')
    sector = resolve_sector('Besoin socio-économique', 'Appui économique')

    besoin_sources = [
        payload.get('principauxbesoinsSociauxEconomiques') or [],
        payload.get('principauxBesoinsEnRenforcementDeCapacites') or [],
    ]

    idx = 0
    for entries in besoin_sources:
        for entry in entries:
            besoin = entry.get('besoin')
            if not besoin:
                continue
            idx += 1

            investment = find_existing_flat_investment(administrative_level, component, besoin)
            if investment and should_skip_for_sync_date(investment, document_date, is_considerate_sync_date):
                continue

            if not investment:
                investment = Investment(
                    administrative_level=administrative_level,
                    investment_status=Investment.PRIORITY,
                    delays_consumed=0, duration=0,
                    financial_implementation_rate=0, physical_execution_rate=0,
                    no_sql_id='',
                )

            investment.title = besoin
            investment.sector = sector
            investment.component = component
            investment.ranking = idx
            investment.climate_contribution_text = contribution_text
            investment.climate_contribution = bool(contribution_text)

            mark_synced(investment, document_date)
            investment.save()

            groups = find_matching_groupes_socioeconomiques(besoin, village_group_names)
            if groups:
                investment.groupes_socioeconomiques.set(groups)

            if project:
                investment.came_from.add(project)
            
            investment.save()