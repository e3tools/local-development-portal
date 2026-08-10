from django.core.management.base import BaseCommand
from no_sql_client import NoSQLClient
from administrativelevels.models import AdministrativeLevel
from cosomis.constants import IGNORES

class Command(BaseCommand):
    help = 'Description of your command'

    def check_for_valid_facilitator(self, facilitator):
        db = self.nsc.get_db(facilitator).get_query_result({
            "type": "facilitator"
        })
        for document in db:
            print("Facilitator", document)
            try:
                if not document['develop_mode'] and not document["training_mode"]:
                    print("Facilitator is valid", document)
                    return True
            except:
                return False
        return False

    def handle(self, *args, **options):
        # Your command logic here
        self.nsc = NoSQLClient()
        facilitator_dbs = self.nsc.list_all_databases('facilitator')
        for db_name in facilitator_dbs:
            if self.check_for_valid_facilitator(db_name):
                db = self.nsc.get_db(db_name).get_query_result({
                    "type": "task",
                    "phase_name": "VISITES PREALABLES",
                    "name": "Etablissement du profil du village",
                })
                for document in db:
                    update_or_create_adm_document(self.nsc, document)
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))

def update_or_create_adm_document(client, population_document):

    # Access the 'purs_test' database

    # Extract the administrative_level_id from the priorities document
    adm_id = population_document['administrative_level_id']

    adm_object = AdministrativeLevel.objects.filter(no_sql_db_id=adm_id).first()
    if not adm_object:
        return

    old_forms = population_document.get('old_forms') or []
    old_form_response = old_forms[-1].get('form_response') if old_forms else None

    extracted_population_data = extract_population_data(
        population_document.get('form_response'),
        old_form_response,
    )

    if not extracted_population_data:
        return

    # If the document exists, update it
    adm_object.total_population = extracted_population_data['total_population']
    adm_object.population_men = extracted_population_data['population_men']
    adm_object.population_women = extracted_population_data['population_women']
    adm_object.population_young = extracted_population_data['population_young']
    adm_object.population_elder = extracted_population_data['population_elder']
    adm_object.population_handicap = extracted_population_data['population_handicap']
    adm_object.population_agriculture = extracted_population_data['population_agriculture']
    adm_object.population_breeders = extracted_population_data['population_breeders']
    adm_object.population_minorities = extracted_population_data['population_minorities']
    adm_object.total_house_holds = extracted_population_data['total_house_holds']
    adm_object.minorities = extracted_population_data['minorities']
    adm_object.ethnic_groups = extracted_population_data['ethnic_groups']
    adm_object.save()


def extract_population_data(form_response, old_form_response=None):
    """
    Le formulaire "Etablissement du profil du village" a changé de structure au fil
    des projets. `form_response` porte le format courant (clé `generalitiesSurVillage`,
    répartition hommes/femmes par tranche d'âge, éventuellement par statut
    réfugié/déplacé interne/communauté d'accueil), tandis que les documents plus
    anciens - ou `old_forms`, conservé en historique lors d'une mise à jour du
    formulaire - utilisent l'ancien format (`population`, `personnesVulnerables`).
    On lit le format courant en priorité et on complète les champs manquants avec
    le format legacy trouvé dans `form_response` puis dans `old_forms`.
    """
    fields = [
        "total_population", "population_men", "population_women",
        "population_young", "population_elder", "population_handicap",
        "population_agriculture", "population_breeders", "population_minorities",
        "total_house_holds", "minorities", "ethnic_groups"
    ]
    data = {field: None for field in fields}

    def set_if_empty(field, value):
        if (data[field] is None or data[field] in IGNORES) and (value is not None or value not in IGNORES):
            data[field] = value

    def scan_current_format(entries):
        for entry in entries or []:
            generalities = entry.get("generalitiesSurVillage")
            if generalities:
                set_if_empty("total_population", generalities.get("populationVillage"))
                men = sum(v or 0 for k, v in generalities.items() if k.startswith("totalHommes"))
                women = sum(v or 0 for k, v in generalities.items() if k.startswith("totalFemmes"))
                set_if_empty("population_men", men)
                set_if_empty("population_women", women)
                # set_if_empty("population_minorities", generalities.get("nombreEthniques"))
                set_if_empty("total_house_holds", generalities.get("totalHouseHolds"))

                set_if_empty("population_young", (
                    generalities.get("totalHommesMoins35", 0) + generalities.get("totalFemmesMoins35", 0)
                ))

            # principale_ethnies = entry.get("principaleEthnies")
            # if principale_ethnies:
            #     nb_ethnies = sum(1 for i in (1, 2, 3) if principale_ethnies.get(f"principaleEthnie{i}"))
            #     set_if_empty("population_minorities", nb_ethnies)

            ethnics_groups = entry.get("principaleEthnies")
            if ethnics_groups:
                set_if_empty("ethnic_groups", [
                    v for k, v in ethnics_groups.items() if k.startswith("principaleEthnie") and (v and v not in IGNORES)
                ])

    def scan_legacy_format(entries):
        for entry in entries or []:
            generalities = entry.get("generalitiesSurVillage")
            if generalities:
                set_if_empty("total_population", generalities.get("populationVillage"))
                set_if_empty("total_house_holds", generalities.get("totalHouseHolds"))

            population = entry.get("population")
            if population:
                set_if_empty("total_population", population.get("populationTotaleDuVillage"))
                set_if_empty("population_men", population.get("populationNombreDeHommes"))
                set_if_empty("population_women", population.get("populationNombreDeFemmes"))
                set_if_empty("minorities", population.get("populationEthniqueMinoritaire"))
                set_if_empty("population_minorities", population.get("populationEthniqueMinoritaireNombrePersonnes"))
                set_if_empty("total_house_holds", population.get("totalHouseHolds"))

            ethnics_groups = entry.get("Ethnicité")
            if ethnics_groups:
                set_if_empty("ethnic_groups", [
                    elt['NomEthnicité'] for elt in ethnics_groups if elt
                ])

            persons_vulnerable_proportion = entry.get("personnesVulnerables")
            donnes_proportion = entry.get("donnees")
            if donnes_proportion:
                jeunes = donnes_proportion.get("populationPersonnesJeunes")
                if jeunes:
                    total_jeunes_proportion = jeunes.get("populationPersonnesJeunesTotal")
                    if total_jeunes_proportion and data['total_population']:
                        population_young = int(data['total_population'] * total_jeunes_proportion / 100)
                        set_if_empty("population_young", 0 if population_young > data['total_population'] else population_young)

            if persons_vulnerable_proportion:
                
                personnes_agees = persons_vulnerable_proportion.get("populationPersonnesAgees")
                if personnes_agees:
                    personnes_agees_proportion = personnes_agees.get("populationPersonnesAgeesTotal")
                    if personnes_agees_proportion and data['total_population']:
                        population_elder = int(data['total_population'] * personnes_agees_proportion / 100)
                        set_if_empty("population_elder", 0 if population_elder > data['total_population'] else population_elder)


                personnes_handicapees = persons_vulnerable_proportion.get("populationPersonnesHandicape")
                if personnes_handicapees:
                    population_handicap_proportion = personnes_handicapees.get("populationPersonnesHandicapeTotal")
                    if population_handicap_proportion and data['total_population']:
                        population_handicap = int(data['total_population'] * population_handicap_proportion / 100)
                        set_if_empty("population_handicap", 0 if population_handicap > data['total_population'] else population_handicap)
                    

    scan_current_format(form_response)
    scan_legacy_format(form_response)
    scan_legacy_format(old_form_response)

    if all(value is None for value in data.values()):
        return None

    extracted_population_data = {field: (data[field] or 0) for field in fields}
    print('here is the result:', extracted_population_data)
    return extracted_population_data
