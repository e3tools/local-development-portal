# investments/management/commands/import_funded_investments.py
import json
import pandas as pd
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from administrativelevels.models import AdministrativeLevel
from administrativelevels.utils.resolvers import resolve_adm_level
from investments.models import Investment, Project
from investments.models import Sector


IMPORT_FILES = {
    "en_cours": "BJ_GoG_COSO_Liste des sous-projets_en cours_16062026.xlsx",
    "acheves":  "BJ_GoG_COSO_Liste des sous-projets_achevés_15062026.xlsx",
}

# Path to arbitrage files produced by the matching scripts.
# Adjust to wherever you store them relative to manage.py.
FINAL_MATCHING_XLSX  = "final_matching.xlsx"
TO_CREATE_ARBITRAGE_JSON = "to_create_arbitrage.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_title(row):
    """Return the best available title from an import row."""
    titre   = str(row.get("titre_sp", "") or "").strip()
    intitule = str(row.get("intitule", "") or "").strip()
    return titre if titre and titre.lower() not in ("nan", "") else intitule


def _load_import_row(source, line, import_dfs):
    """Return the raw import DataFrame row for a given source + line number."""
    df = import_dfs[source]
    # line is 1-based Excel row; header=row1, data starts at row2 → index = line-2
    idx = line - 2
    if idx < 0 or idx >= len(df):
        return None
    return df.iloc[idx]


def _resolve_village(row):
    """Resolve village AdministrativeLevel from an import row using resolve_adm_level."""
    dep = resolve_adm_level(str(row.get("departement", "") or ""), "département")
    com = resolve_adm_level(str(row.get("commune", "") or ""), "commune", parent=dep)
    arr = resolve_adm_level(str(row.get("arrondissement", "") or ""), "arrondissement", parent=com)
    vil_name = str(row.get("village", "") or "").strip()
    vil = resolve_adm_level(vil_name, "village", parent=arr)
    if not vil:
        porteur = str(row.get("porteur", "") or "").strip()
        if porteur and porteur.lower() not in ("nan", ""):
            vil = resolve_adm_level(porteur, "village", parent=arr)
    return vil


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Import funded sub-projects from Excel files into Investment records. "
        "Uses final_matching.xlsx + to_create_arbitrage.json produced by the "
        "matching scripts."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate without writing to the database.",
        )
        parser.add_argument(
            "--files-dir",
            type=str,
            default=".",
            help="Directory containing the Excel import files (default: current dir).",
        )
        parser.add_argument(
            "--matching-dir",
            type=str,
            default=".",
            help="Directory containing final_matching.xlsx and to_create_arbitrage.json.",
        )

    def handle(self, *args, **options):
        dry_run      = options["dry_run"]
        files_dir    = Path(options["files_dir"])
        matching_dir = Path(options["matching_dir"])

        if dry_run:
            self.stdout.write(self.style.WARNING("*** DRY RUN — no changes will be saved ***"))

        # --- Load COSO project ---
        try:
            project = Project.objects.get(name="COSO")
        except Project.DoesNotExist:
            raise CommandError('Project with name "COSO" not found in the database.')

        self.stdout.write(f"Project: {project.name} (ID: {project.id})")

        # --- Load import DataFrames ---
        import_dfs = {}
        for source, fname in IMPORT_FILES.items():
            path = files_dir / fname
            if not path.exists():
                raise CommandError(f"Import file not found: {path}")
            xl = pd.ExcelFile(path)
            df = xl.parse(xl.sheet_names[0])
            df = df.rename(columns={
                "Département":              "departement",
                "Commmune":                 "commune",
                "Arrondissement":           "arrondissement",
                "Communauté":               "village",
                "Porteur":                  "porteur",
                "Intitulé du sous projet":  "intitule",
                "Titre du sous-projet":     "titre_sp",
                "Description du projet":    "description",
                "Sous-composante":          "sous_composante",
                "Coût prévisionnel":        "cout",
            })
            for col in ["departement", "commune", "arrondissement", "village",
                        "porteur", "intitule", "titre_sp", "description",
                        "sous_composante"]:
                df[col] = df[col].astype(str).str.strip() if col in df.columns else ""
            import_dfs[source] = df

        # --- Load matching results ---
        matching_path = matching_dir / FINAL_MATCHING_XLSX
        if not matching_path.exists():
            raise CommandError(f"Matching file not found: {matching_path}")
        matching_df = pd.read_excel(matching_path, sheet_name="Final Matching")

        arbitrage_path = matching_dir / TO_CREATE_ARBITRAGE_JSON
        if not arbitrage_path.exists():
            raise CommandError(f"Arbitrage file not found: {arbitrage_path}")
        with open(arbitrage_path, "r", encoding="utf-8") as f:
            to_create_meta = {
                (r["source"], int(r["line"])): r
                for r in json.load(f)
            }

        # --- Stats ---
        stats = {
            "updated":  0,
            "created":  0,
            "skipped":  0,
            "errors":   0,
        }

        with transaction.atomic():

            for _, mrow in matching_df.iterrows():
                source       = mrow["source"]
                line         = int(mrow["line"])
                final_status = mrow["final_status"]

                # Skip empty / unresolvable rows
                if str(mrow.get("import_village", "")).lower() in ("nan", ""):
                    stats["skipped"] += 1
                    continue

                project_status = (
                    Investment.IN_PROGRESS if source == "en_cours"
                    else Investment.COMPLETED
                )

                # Load raw import row
                imp_row = _load_import_row(source, line, import_dfs)
                if imp_row is None:
                    self.stdout.write(
                        self.style.WARNING(f"  [{source} l{line}] Import row not found — skipped")
                    )
                    stats["skipped"] += 1
                    continue

                # ----------------------------------------------------------------
                # MATCHED / TO_REVIEW → update existing Investment
                # ----------------------------------------------------------------
                if final_status in ("MATCHED", "TO_REVIEW"):
                    db_id = mrow.get("db_id")
                    if pd.isna(db_id) or str(db_id).strip() in ("", "nan"):
                        self.stdout.write(
                            self.style.WARNING(f"  [{source} l{line}] MATCHED but db_id missing — skipped")
                        )
                        stats["skipped"] += 1
                        continue

                    try:
                        investment = Investment.objects.get(id=int(db_id))
                    except Investment.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(f"  [{source} l{line}] Investment id={db_id} not found — skipped")
                        )
                        stats["errors"] += 1
                        continue

                    title = _get_title(imp_row)
                    sub_comp = str(imp_row.get("sous_composante", "") or "").strip()
                    try:
                        cost = int(float(str(imp_row.get("cout", "") or "0").replace(" ", "").replace("\xa0", "") or 0))
                    except (ValueError, TypeError):
                        cost = investment.estimated_cost

                    if dry_run:
                        self.stdout.write(
                            f"  [DRY] UPDATE inv={investment.id} '{investment.title[:50]}'"
                            f" → title='{title[:50]}' status={project_status} sub={sub_comp}"
                        )
                    else:
                        investment.investment_status = Investment.SUBPROJECT
                        investment.project_status    = project_status
                        investment.funded_by         = project
                        if title:
                            investment.title         = title
                        if cost:
                            investment.estimated_cost = cost
                        if sub_comp:
                            investment.sub_component = sub_comp
                        investment.save()

                    stats["updated"] += 1

                # ----------------------------------------------------------------
                # TO_CREATE → create new Investment
                # ----------------------------------------------------------------
                elif final_status == "TO_CREATE":
                    meta = to_create_meta.get((source, line))
                    if meta is None:
                        self.stdout.write(
                            self.style.WARNING(f"  [{source} l{line}] TO_CREATE but no arbitrage meta — skipped")
                        )
                        stats["skipped"] += 1
                        continue

                    # Resolve village
                    db_village_id = mrow.get("db_village_id")
                    if pd.notna(db_village_id) and str(db_village_id).strip() not in ("", "nan"):
                        try:
                            village = AdministrativeLevel.objects.get(id=int(db_village_id))
                        except AdministrativeLevel.DoesNotExist:
                            village = _resolve_village(imp_row)
                    else:
                        village = _resolve_village(imp_row)

                    if village is None:
                        self.stdout.write(
                            self.style.WARNING(f"  [{source} l{line}] Village unresolvable — skipped")
                        )
                        stats["skipped"] += 1
                        continue

                    # Sector
                    sector = Sector.objects.filter(name=meta["sector"]).first()
                    if sector is None:
                        sector = Sector.objects.filter(name="Autre").first()

                    title = _get_title(imp_row)
                    sub_comp = str(imp_row.get("sous_composante", "") or "").strip()
                    try:
                        cost = int(float(str(imp_row.get("cout", "") or "0").replace(" ", "").replace("\xa0", "") or 0))
                    except (ValueError, TypeError):
                        cost = 0

                    description = meta["groupe"]  # group stored in description field

                    if dry_run:
                        self.stdout.write(
                            f"  [DRY] CREATE village={village.name} sector={sector.name if sector else '?'}"
                            f" sub={sub_comp} titre='{title[:50]}' groupe={description}"
                        )
                    else:
                        Investment.objects.create(
                            title=title,
                            description=description,
                            investment_status=Investment.SUBPROJECT,
                            project_status=project_status,
                            funded_by=project,
                            administrative_level=village,
                            sector=sector,
                            sub_component=sub_comp,
                            estimated_cost=cost or 0,
                            climate_contribution=True,
                            climate_contribution_text="",
                            duration=0,
                            delays_consumed=0,
                            physical_execution_rate=0,
                            financial_implementation_rate=0,
                            ranking=None,
                        )

                    stats["created"] += 1

                else:
                    stats["skipped"] += 1

            if dry_run:
                # Roll back everything even if no error
                transaction.set_rollback(True)

        # --- Summary ---
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(
            f"Done {'(DRY RUN) ' if dry_run else ''}"
            f"— updated={stats['updated']}, created={stats['created']}, "
            f"skipped={stats['skipped']}, errors={stats['errors']}"
        ))
