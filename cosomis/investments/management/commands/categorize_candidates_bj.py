"""
Pipeline stage 4 — read-only sector/cost categorization of besoins that
reached this point without a funded match (stage-3 NO_MATCH) or that are
funded but still lack a Sector (stage-3 MATCH — Excel has no Sector/
Category taxonomy, only free-text "Sous-secteur d'activité").

Never writes to the database. Reads the stage-3 JSON and adds a
`categorization` block:
  - sector_name / category_name: best guess, or "Autre" if nothing matched.
  - confidence: "exact" (historical priority_to_sector_mapping.json hit),
    "high"/"medium" (keyword rule), or "low" (no rule matched — Autre).
  - estimated_cost: real Excel cost for funded rows, else
    SECTOR_ESTIMATED_COSTS[sector] (same table as
    update_investment_estimated_costs_by_sector_bj), else DEFAULT_ESTIMATED_COST.

Rows still sitting in MATCH/REVIEW/CONFLICT from stage 2 (already-in-DB
candidates) are passed through unchanged — they don't need a sector guess,
they need your manual arbitration first.

Usage:
    python manage.py categorize_candidates_bj \
        --in new_needs_excel_matched_bj.json \
        --out new_needs_categorized_bj.json
"""
import json
import re
import unicodedata

from django.core.management.base import BaseCommand

from administrativelevels.models import Sector
from investments.constants import SECTOR_ESTIMATED_COSTS, DEFAULT_ESTIMATED_COST


def _norm_apos(s):
    return str(s or "").replace("’", "'").replace("ʼ", "'").replace("‘", "'")


def nk(s):
    s = _norm_apos(s).strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# (keywords required, sector_name, category_name or None, confidence)
# category_name disambiguates the two Sector rows both named "Aménagement".
RULES = [
    (["hangar"], "Hangar de marché", "Infrastructure marchande", "high"),
    (["boutique"], "Boutique", "Infrastructure marchande", "high"),
    (["gare routiere"], "Gare routière à l'intérieur ou à proximité du marché", "Infrastructure marchande", "high"),
    (["auto gare"], "Gare routière à l'intérieur ou à proximité du marché", "Infrastructure marchande", "high"),
    (["autogare"], "Gare routière à l'intérieur ou à proximité du marché", "Infrastructure marchande", "high"),
    (["marche betail"], "Marché de bétail", "Infrastructure marchande", "high"),
    (["marche a betail"], "Marché de bétail", "Infrastructure marchande", "high"),
    (["parking", "marche"], "Passage d'accès à l'intérieur d'un marché", "Infrastructure marchande", "medium"),
    (["magasin", "stockage"], "Magasin de stockage", "Infrastructure marchande", "high"),

    (["latrine", "marche"], "Bloc de latrines pour les marchés locaux", "Hygiène et assainissement (WASH)", "high"),
    (["latrine", "ecole"], "Bloc de latrine pour les écoles maternelles et primaires", "Hygiène et assainissement (WASH)", "high"),
    (["latrine", "epp"], "Bloc de latrine pour les écoles maternelles et primaires", "Hygiène et assainissement (WASH)", "high"),
    (["latrine", "college"], "Bloc de latrine pour les collèges", "Hygiène et assainissement (WASH)", "high"),
    (["latrine", "lycee"], "Bloc de latrine pour les collèges", "Hygiène et assainissement (WASH)", "high"),
    (["latrine", "sante"], "Bloc de latrines pour les centres de santé et dispensaire isolés", "Hygiène et assainissement (WASH)", "high"),
    (["latrine", "dispensaire"], "Bloc de latrines pour les centres de santé et dispensaire isolés", "Hygiène et assainissement (WASH)", "high"),
    (["latrine"], "Blocs de latrines publiques modernes", "Hygiène et assainissement (WASH)", "medium"),
    (["toilette", "marche"], "Bloc de latrines pour les marchés locaux", "Hygiène et assainissement (WASH)", "medium"),
    (["toilette"], "Blocs de latrines publiques modernes", "Hygiène et assainissement (WASH)", "medium"),
    (["drainage", "marche"], "Ouvrage d'assainissement dans les marchés locaux", "Hygiène et assainissement (WASH)", "high"),
    (["hygiene"], "Hygiène des lieux publics", "Hygiène et assainissement (WASH)", "high"),

    (["parc", "vaccination"], "Parc de vaccination", "Production animale", "high"),
    (["pharmacie veterinaire"], "Pharmacie vétérinaire", "Production animale", "high"),
    (["couloir pastoral"], "Aménagement", "Production animale", "high"),
    (["espace pastoral"], "Aménagement", "Production animale", "high"),
    (["aire de paturage"], "Aménagement", "Production animale", "medium"),
    (["paturage"], "Aménagement", "Production animale", "medium"),
    (["elevage"], "Alimentation", "Production animale", "medium"),
    (["ruminant"], "Alimentation", "Production animale", "medium"),
    (["volaille"], "Alimentation", "Production animale", "medium"),
    (["porcin"], "Alimentation", "Production animale", "medium"),

    (["perimetre maraicher"], "Aménagement", "Production végétale", "medium"),
    (["maraich"], "Aménagement", "Production végétale", "medium"),
    (["plantation"], "Aménagement", "Production végétale", "medium"),

    (["chateau", "pea"], "Poste d'eau autonome (PEA)", "Accès à l'eau", "high"),
    (["poste d eau autonome"], "Poste d'eau autonome (PEA)", "Accès à l'eau", "high"),
    (["adduction"], "Adduction d'eau villageoise (AEV)", "Accès à l'eau", "high"),
    (["reseau", "eau potable"], "Système d'alimentation en eau potable (SAEP)", "Accès à l'eau", "medium"),
    (["forage", "agropastoral"], "Forage + abreuvoir", "Accès à l'eau", "high"),
    (["forage", "abreuvoir"], "Forage + abreuvoir", "Accès à l'eau", "high"),
    (["forage", "betail"], "Forage + abreuvoir", "Accès à l'eau", "high"),
    (["point d eau", "multifonctionnel"], "Forage + abreuvoir", "Accès à l'eau", "medium"),
    (["forage"], "Forage simple", "Accès à l'eau", "medium"),
    (["pompe"], "Forage simple", "Accès à l'eau", "medium"),

    (["terrain", "football"], "Terrain de football", "Sport et loisirs ", "high"),
    (["terrain", "foot"], "Terrain de football", "Sport et loisirs ", "high"),
    (["equipement sportif", "football"], "Kits de football (crampons, filets, ballon, maillots)", "Sport et loisirs ", "high"),
    (["equipement sportif"], "Terrain de football", "Sport et loisirs ", "medium"),
    (["basketball"], "Kits de basketball (crampons, filets, ballon, maillots)", "Sport et loisirs ", "high"),
    (["handball"], "Kits de handball (crampons, filets, ballon, maillots)", "Sport et loisirs ", "high"),
    (["lutte traditionnelle"], "Infrastructure", "Sport et loisirs ", "medium"),
    (["maison des jeunes"], "Infrastructure", "Sport et loisirs ", "medium"),
    (["maison de jeunes"], "Infrastructure", "Sport et loisirs ", "medium"),
    (["espace public de jeux"], "Jeu ludique", "Sport et loisirs ", "medium"),
    (["aire de jeu"], "Jeu ludique", "Sport et loisirs ", "medium"),

    (["alphabetis"], "Infrastructure d'alphabétisation", "Education", "high"),
    (["salle de lecture"], "Infrastructure d'alphabétisation", "Education", "medium"),
    (["module", "trois salle"], "Module de trois (3) salles de classes + bureau et magasins pour les écoles primaires", "Education", "high"),
    (["module", "3 salle"], "Module de trois (3) salles de classes + bureau et magasins pour les écoles primaires", "Education", "high"),
    (["salle de classe", "maternelle"], "Module de deux (2) salles de classe pour les écoles maternelles", "Education", "high"),
    (["salle de classe"], "Module de trois (3) salles de classes + bureau et magasins pour les écoles primaires", "Education", "medium"),
    (["module de classe"], "Module de trois (3) salles de classes + bureau et magasins pour les écoles primaires", "Education", "medium"),
    (["table", "banc", "maternelle"], "Table + chaises pour les écoles maternelles", "Education", "high"),
    (["table", "chaise", "maternelle"], "Table + chaises pour les écoles maternelles", "Education", "high"),
    (["table", "banc"], "Table + bancs pour les écoles primaires", "Education", "high"),
    (["cantine scolaire"], "Complexe pour les cantines scolaires", "Education", "high"),
    (["bureau d ecole"], "Bureau d'école primaire", "Education", "high"),
    (["magasin d ecole"], "Magasin d'école", "Education", "high"),
    (["logement", "enseignant"], "Logement pour les enseignants du primaire", "Education", "high"),

    (["eclairage public"], "Éclairage public solaire", "Énergie et éclairage", "high"),
    (["lampadaire"], "Éclairage public solaire", "Énergie et éclairage", "high"),
    (["electrification"], "Électrification rurale hors réseau", "Énergie et éclairage", "high"),
    (["extension", "reseau electrique"], "Extension du réseau électrique", "Énergie et éclairage", "high"),

    (["franchissement"], "Passage busé", "Transport rural (connectivité)", "high"),
    (["buse"], "Passage busé", "Transport rural (connectivité)", "high"),
    (["piste"], "Piste de desserte rurale", "Transport rural (connectivité)", "high"),
    (["caniveau"], "Caniveau", "Transport rural (connectivité)", "high"),
    (["dalot"], "Dalots", "Transport rural (connectivité)", "high"),

    (["maternite"], "Lits de maternité et d'hospitalisation", "Santé", "medium"),
    (["dispensaire"], "Dispensaire isolé", "Santé", "medium"),
    (["incinerateur"], "Incinérateur", "Santé", "high"),
    (["centre de sante"], "Centre de santé d'arrondissement (CSA) ou Centre de santé de commune (CSC)", "Santé", "medium"),

    (["transformation"], "Equipement", "Transformation", "medium"),
    (["materiel", "transformation"], "Equipement", "Transformation", "medium"),
]


def guess_sector(title_raw):
    text = nk(title_raw)
    best = None  # (num_matched_keywords, sector_name, category_name, confidence)
    for keywords, sector_name, category_name, confidence in RULES:
        if all(kw in text for kw in keywords):
            score = len(keywords)
            if best is None or score > best[0]:
                best = (score, sector_name, category_name, confidence)
    if best is None:
        return "Autre", None, "low"
    return best[1], best[2], best[3]


class Command(BaseCommand):
    help = (
        "Stage 4 (read-only): assign a best-guess Sector/Category and "
        "estimated cost to besoins that have no funded match (final "
        "NO_MATCH) or are funded via Excel but still lack a Sector. Never "
        "writes to the database."
    )

    def add_arguments(self, parser):
        parser.add_argument("--in", dest="in_path", default="new_needs_excel_matched_bj.json")
        parser.add_argument("--out", dest="out_path", default="new_needs_categorized_bj.json")

    def handle(self, *args, **options):
        with open(options["in_path"], encoding="utf-8") as f:
            rows = json.load(f)

        try:
            with open("config_data/priority_to_sector_mapping.json", encoding="utf-8") as f:
                exact_mapping = json.load(f)
        except FileNotFoundError:
            exact_mapping = {}
        exact_mapping_norm = {nk(k): v for k, v in exact_mapping.items()}

        sector_cache = {}

        def resolve_sector_fk(sector_name, category_name):
            key = (sector_name, category_name)
            if key in sector_cache:
                return sector_cache[key]
            qs = Sector.objects.filter(name=sector_name)
            if category_name:
                qs = qs.filter(category__name=category_name)
            sector = qs.first() or Sector.objects.filter(name="Autre").first()
            sector_cache[key] = sector
            return sector

        stats = {"exact": 0, "high": 0, "medium": 0, "low": 0}
        out_rows = []

        for row in rows:
            em = row.get("excel_match")
            dm = row.get("db_match", {})

            cap_override = row.get("capacity_override", {})
            needs_categorization = (
                cap_override.get("reason") == "under_capacity_no_arbitration"
                or (
                    not cap_override.get("applied")
                    and (
                        (em is not None and em["status"] in ("MATCH", "NO_MATCH"))
                        or (em is None and dm.get("status") == "NO_MATCH")
                    )
                )
            )

            if not needs_categorization:
                out_rows.append(row)
                continue

            title_raw = row["title_raw"]
            exact_hit = exact_mapping_norm.get(nk(title_raw))

            if exact_hit:
                sector_name, category_name, confidence = exact_hit, None, "exact"
            else:
                sector_name, category_name, confidence = guess_sector(title_raw)

            stats[confidence] += 1
            sector = resolve_sector_fk(sector_name, category_name)

            is_funded = em is not None and em["status"] == "MATCH"
            if is_funded and em.get("cost"):
                try:
                    estimated_cost = int(float(str(em["cost"]).replace(" ", "").replace("\xa0", "")))
                except (ValueError, TypeError):
                    estimated_cost = SECTOR_ESTIMATED_COSTS.get(sector.name, DEFAULT_ESTIMATED_COST)
            else:
                estimated_cost = SECTOR_ESTIMATED_COSTS.get(sector.name, DEFAULT_ESTIMATED_COST)

            out_rows.append({
                **row,
                "categorization": {
                    "sector_id": sector.id,
                    "sector_name": sector.name,
                    "category_name": sector.category.name,
                    "confidence": confidence,
                    "estimated_cost": estimated_cost,
                    "funded": is_funded,
                },
            })

        with open(options["out_path"], "w", encoding="utf-8") as f:
            json.dump(out_rows, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f"Categorized — exact: {stats['exact']} | high: {stats['high']} | "
            f"medium: {stats['medium']} | low (Autre): {stats['low']} | "
            f"written to {options['out_path']}"
        ))
