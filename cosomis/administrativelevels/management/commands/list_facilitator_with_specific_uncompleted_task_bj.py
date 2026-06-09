import json
from datetime import datetime
from collections import defaultdict
from django.core.management.base import BaseCommand
from no_sql_client import NoSQLClient


TARGET_TASK_NAME = "Quatrième Assemblée Générale Villageoise -Pratique de l’Évaluation Participative des Besoins (EPB) - Soutenir la communauté dans la sélection des priorités par sous-composante à soumettre à la discussion au niveau arrondissement"


class Command(BaseCommand):
    help = "Export the list of facilitators who have not completed the EPB task"

    def handle(self, *args, **options):
        self.nsc = NoSQLClient()
        facilitator_dbs = self.nsc.list_all_databases('facilitator')

        facilitators = defaultdict(set)

        for db_name in facilitator_dbs:
            db = self.nsc.get_db(db_name)

            tasks = db.get_query_result({
                "type": "task",
                "name": TARGET_TASK_NAME
            })

            villages_with_empty_task = set()

            for task in tasks:
                form_response = task.get("form_response")
                if not form_response or form_response == []:
                    village = task.get("administrative_level_name")
                    if village:
                        villages_with_empty_task.add(village.strip())

            if not villages_with_empty_task:
                continue

            facilitator_docs = db.get_query_result({
                "type": "facilitator"
            })

            for facilitator in facilitator_docs:
                facilitator_name = facilitator.get("name")
                if facilitator_name:
                    facilitators[facilitator_name.strip()].update(villages_with_empty_task)

        export_data = {
            "exported_at": datetime.today().strftime('%d-%m-%Y'),
            "task_name": TARGET_TASK_NAME,
            "data": {
                name: sorted(list(villages))
                for name, villages in facilitators.items()
            }
        }

        output_file = "facilitators_and_villages_not_completed.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=4, ensure_ascii=False)

        self.stdout.write(self.style.WARNING("\nFacilitateurs à interpeller :\n"))
        for name, villages in sorted(facilitators.items()):
            villages_str = ", ".join(sorted(villages))
            self.stdout.write(f"{name} ({villages_str})")

        self.stdout.write(self.style.SUCCESS(f"\nExport terminé → {output_file}"))