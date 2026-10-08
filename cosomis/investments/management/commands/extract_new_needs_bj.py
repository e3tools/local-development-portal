"""
Pipeline stage 1 — read-only extraction of besoins from CouchDB.

Never writes to the SQL database or to CouchDB. Separates besoins into:
  - "already synced by position": an Investment already exists at the same
    (administrative_level, sub_component, ranking) — this is the stable key
    since `title` can be renamed later during funding arbitration.
  - "candidate": no positional match found. These need the next pipeline
    stages (fuzzy match against existing Investments, then against the
    COSO tracking Excel files) before we know if they are truly new.

Each candidate carries the list of existing Investments sharing the same
(administrative_level, sub_component) so stage 2 (fuzzy DB match) has what
it needs without re-querying the DB.

Besoins already arbitrated in a previous pipeline run — found in
config_data/resolved_needs_bj.json, written by import_new_needs_bj after
a real (non-dry-run) execution — are skipped entirely here, even when no
Investment was created for them (e.g. ALREADY_IN_DB, EXCLUDED_*). This is
what keeps a repeat synctasks sync from re-surfacing the same besoins for
arbitration every time.

Usage:
    python manage.py extract_new_needs_bj --out new_needs_candidates_bj.json
"""
import json
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from no_sql_client import NoSQLClient

from administrativelevels.models import AdministrativeLevel
from investments.models import Investment

LEDGER_PATH = Path(settings.BASE_DIR) / "config_data" / "resolved_needs_bj.json"


SUB_COMPONENT_FIELDS = {
    "priorisationSC11":  Investment.SUB_COMPONENT_11,
    "priorisationSC12A": Investment.SUB_COMPONENT_12A,
    "priorisationSC12B": Investment.SUB_COMPONENT_12B,
    "priorisationSC13":  Investment.SUB_COMPONENT_13,
}

PHASE_NAME = "Diagnostic et planification participative"
TASK_NAME = (
    "Quatrième Assemblée Générale Villageoise -Pratique de l’Évaluation "
    "Participative des Besoins (EPB) - Soutenir la communauté dans la "
    "sélection des priorités par sous-composante à soumettre à la "
    "discussion au niveau arrondissement"
)


class Command(BaseCommand):
    help = (
        "Stage 1 (read-only): extract besoins from CouchDB and split them "
        "into 'already synced' (matches an existing Investment by stable "
        "position) vs 'candidate' (needs stage 2/3 matching). Never writes "
        "to any database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--out", default="new_needs_candidates_bj.json",
            help="Output path for the candidate besoins JSON.",
        )

    def check_for_valid_facilitator(self, facilitator):
        db = self.nsc.get_db(facilitator).get_query_result({"type": "facilitator"})
        for document in db:
            develop_mode = document.get("develop_mode", False)
            training_mode = document.get("training_mode", False)
            return not (develop_mode or training_mode)
        return False

    def handle(self, *args, **options):
        out_path = options["out"]
        self.nsc = NoSQLClient()
        facilitator_dbs = self.nsc.list_all_databases("facilitator")

        existing_by_position = {}
        existing_by_adm_subcomp = defaultdict(list)
        for inv in Investment.objects.select_related("administrative_level").all():
            if inv.ranking is not None:
                key = (inv.administrative_level_id, inv.sub_component, inv.ranking)
                existing_by_position[key] = inv.id
            existing_by_adm_subcomp[(inv.administrative_level_id, inv.sub_component)].append({
                "id": inv.id,
                "title": inv.title or "",
                "ranking": inv.ranking,
                "project_status": inv.project_status,
                "investment_status": inv.investment_status,
            })

        ledger = {}
        if LEDGER_PATH.exists():
            with open(LEDGER_PATH, encoding="utf-8") as f:
                ledger = json.load(f)

        stats = {
            "facilitator_dbs_total": len(facilitator_dbs),
            "facilitator_dbs_valid": 0,
            "total_besoins": 0,
            "already_synced_by_position": 0,
            "already_resolved_in_ledger": 0,
            "no_adm_level": 0,
            "candidates": 0,
        }
        candidates = []

        for db_name in facilitator_dbs:
            if not self.check_for_valid_facilitator(db_name):
                continue
            stats["facilitator_dbs_valid"] += 1

            docs = self.nsc.get_db(db_name).get_query_result({
                "type": "task",
                "phase_name": PHASE_NAME,
                "name": TASK_NAME,
            })

            for document in docs:
                adm_id = document.get("administrative_level_id")
                try:
                    adm = AdministrativeLevel.objects.get(no_sql_db_id=adm_id)
                except AdministrativeLevel.DoesNotExist:
                    stats["no_adm_level"] += 1
                    continue

                if "form_response" not in document or not document["form_response"]:
                    continue
                form = document["form_response"][0]

                for sc_field, sub_component_value in SUB_COMPONENT_FIELDS.items():
                    priorities = form.get(sc_field, [])
                    for idx, priority in enumerate(priorities):
                        if priority.get("besoin") is None:
                            continue

                        stats["total_besoins"] += 1
                        ranking = idx + 1
                        title_raw = (
                            priority["besoin"].strip().strip("'")
                            .replace("\n", "").replace("\t", "")
                        )

                        pos_key = (adm.id, sub_component_value, ranking)
                        if pos_key in existing_by_position:
                            stats["already_synced_by_position"] += 1
                            continue

                        no_sql_id = f"{document.get('_id')}:{sub_component_value}:{ranking}"
                        if no_sql_id in ledger:
                            stats["already_resolved_in_ledger"] += 1
                            continue

                        stats["candidates"] += 1
                        candidates.append({
                            "facilitator_db": db_name,
                            "nosql_document_id": document.get("_id"),
                            "administrative_level_id": adm.id,
                            "administrative_level_name": adm.name,
                            "sub_component": sub_component_value,
                            "ranking": ranking,
                            "title_raw": title_raw,
                            "groupe": priority.get("groupe", ""),
                            "adaptation_climatique": priority.get("adaptationClimatique"),
                            "existing_investments_same_adm_subcomp":
                                existing_by_adm_subcomp.get((adm.id, sub_component_value), []),
                        })

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(candidates, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f"Facilitator DBs: {stats['facilitator_dbs_valid']}/{stats['facilitator_dbs_total']} valid | "
            f"Besoins total: {stats['total_besoins']} | "
            f"Already synced (position match): {stats['already_synced_by_position']} | "
            f"Already resolved (ledger): {stats['already_resolved_in_ledger']} | "
            f"No adm level resolved: {stats['no_adm_level']} | "
            f"Candidates written to {out_path}: {stats['candidates']}"
        ))
