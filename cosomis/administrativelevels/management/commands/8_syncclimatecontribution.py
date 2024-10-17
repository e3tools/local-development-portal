from django.core.management.base import BaseCommand
from no_sql_client import NoSQLClient
from investments.models import Investment
from administrativelevels.models import AdministrativeLevel


class Command(BaseCommand):
    def check_for_valid_facilitator(self, facilitator):
        db = self.nsc.get_db(facilitator).get_query_result({"type": "facilitator"})
        for document in db:
            try:
                if not document["develop_mode"] and not document["training_mode"]:
                    return True
            except:
                return False
        return False

    def handle(self, *args, **options):
        self.nsc = NoSQLClient()
        facilitator_dbs = self.nsc.list_all_databases("facilitator")
        for db_name in facilitator_dbs:
            if self.check_for_valid_facilitator(db_name):
                db = self.nsc.get_db(db_name).get_query_result(
                    {
                        "type": "task",
                        "phase_name": "PLANIFICATION",
                        "name": "Soutenir la communauté dans la sélection des priorités par sous-composante (1.1, 1.2 et 1.3) à soumettre à la discussion du CCD lors de la réunion cantonale d'arbitrage",
                    }
                )
                for document in db:
                    update_investment_document(document)
        self.stdout.write(self.style.SUCCESS("Successfully executed mycommand!"))


def update_administrative_level_investment(administrative_level, priority):
    investment = Investment.objects.filter(
        administrative_level=administrative_level,
        title=priority["priorite"]
        if priority["priorite"]
        else priority["priorite"],
    )
    if len(investment) > 0:
        investment = investment.first()
        investment.climate_contribution = True if priority["contributionClimatique"] else False
        investment.climate_contribution_text = priority["contributionClimatique"]
        investment.save()


def update_from_sous_composante(
    administrative_level,
    form_response_document,
    form_response,
    sousComposanteIndex,
    sousComposanteName,
    sousComposanteElementName,
):
    sous_composante = form_response[sousComposanteIndex][sousComposanteName]
    if (
        form_response_document is not None
        and sousComposanteElementName in sous_composante
    ):
        for priority in sous_composante[sousComposanteElementName]:
            update_administrative_level_investment(administrative_level, priority)


def update_investment_document(document):
    adm_id = document["administrative_level_id"]

    administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=adm_id)

    if "form_response" in document:
        form_response_document = document.get("form_response")
        form_response = document["form_response"]
        try:
            update_from_sous_composante(
                administrative_level,
                form_response_document,
                form_response,
                0,
                "sousComposante11",
                "prioritesDuVillage",
            )
        except:
            pass

        try:
            update_from_sous_composante(
                administrative_level,
                form_response_document,
                form_response,
                3,
                "sousComposante13",
                "classement",
            )
        except:
            pass
