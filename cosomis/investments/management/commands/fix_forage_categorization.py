# investments/management/commands/fix_forage_categorization.py
"""
Fixes the categorization of investments incorrectly classified under
"Forage simple" and "Forage + abreuvoir".

Reclassifies investments whose titles do not match water/drilling themes
into their correct sector (education, health, lighting, transport, etc.).

Run:
    python manage.py fix_forage_categorization --dry-run
    python manage.py fix_forage_categorization
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from investments.models import Investment
from administrativelevels.models import Sector

# ---------------------------------------------------------------------------
# IDs to reclassify — manually confirmed arbitration
# ---------------------------------------------------------------------------

# Energy & lighting / Public solar lighting
ECLAIRAGE = {15472, 8480, 8670, 15985, 10428, 14965, 7755, 7967}

# Education / 3-classroom module
EDUCATION = {
    4521, 5502, 6008, 9925, 7497, 9534, 5632, 9306, 9411,
    5605, 15640, 4349, 15090, 3408, 4353, 6049, 10683,
    # UNCLEAR scolaires
    15418,  # SONEB network extension -> drinking water -> kept as Forage simple, removed from EDUCATION set
}
# 15418 = SONEB network extension -> drinking water -> keep as Forage simple
EDUCATION.discard(15418)

# Health / CSA or CSC
SANTE = {15991, 15295, 15326, 10489}

# Market infrastructure
INFRA_MARCHANDE_MAGASIN = {8690, 15210}   # storage warehouse
INFRA_MARCHANDE_MARCHE  = {11839}          # market rehabilitation

# Sport & leisure / Infrastructure or Kits
SPORT = {4352, 4356, 4755, 7332}

# Hygiene and sanitation (WASH)
WASH = {15467, 15982, 10756, 15216, 15468}

# Rural transport / Track or crossing
TRANSPORT_PISTE        = {9290, 15948, 15987}
TRANSPORT_FRANCHIS     = {15486}
TRANSPORT_CANIVEAU     = {10085}

# Crop production / Development (market gardening without primary water component)
PROD_VEGETALE = {
    7784, 5657, 6991, 14207, 14267, 14266, 14249, 14168,
    5474, 7527, 7071, 7091, 7316, 7298, 7391, 9685, 9742,
    5890,
}

# Processing / Equipment
TRANSFORMATION = {7331}

# Animal production / Equipment
PROD_ANIMALE = {15881}


def get_sector(name):
    """
    Look up a Sector by exact name, then via SECTOR_ALIASES.
    Returns None if not found — add the missing name to
    investments/sector_aliases.py to resolve it.
    """
    try:
        from investments.sector_aliases import SECTOR_ALIASES
    except ImportError:
        SECTOR_ALIASES = {}

    # 1. Exact match
    sector = Sector.objects.filter(name=name).first()
    if sector:
        return sector

    # 2. Alias lookup
    canonical = SECTOR_ALIASES.get(name)
    if canonical:
        sector = Sector.objects.filter(name=canonical).first()
        if sector:
            return sector

    # 3. Not found — caller will log a warning
    return None


class Command(BaseCommand):
    help = "Fixes the categorization of investments incorrectly classified under Forage simple / Forage + abreuvoir."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche les changements sans écrire en base.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "*** DRY RUN — no changes will be written to the database ***\n"
            ))

        # Load target sectors
        sectors = {
            "eclairage":         get_sector("Éclairage public solaire"),
            "education_3salles": get_sector("Module de trois (3) salles de classes + bureau et magasins pour les écoles primaires"),
            "education_autre":   get_sector("Infrastructure d'alphabétisation"),
            "sante":             get_sector("Centre de santé d'arrondissement (CSA) ou Centre de santé de commune (CSC)"),
            "magasin":           get_sector("Magasin de stockage"),
            "hangar_marche":     get_sector("Hangar de marché"),
            "sport_infra":       get_sector("Infrastructure"),
            "piste":             get_sector("Piste de desserte rurale"),
            "franchissement":    get_sector("Passage busé"),
            "prod_veg":          get_sector("Aménagement"),
            "transformation":    get_sector("Equipement"),
            "prod_animale":      get_sector("Equipement"),
            "caniveau":          get_sector("Caniveau"),
            "wash_latrines":     get_sector("Blocs de latrines publiques modernes"),
            "wash_assain":       get_sector("Hygiène des lieux publics"),
        }

        # Check that all sectors exist in DB
        missing = [k for k, v in sectors.items() if v is None]
        if missing:
            self.stdout.write(self.style.ERROR(
                f"Sectors not found in DB: {missing}\n"
                "Aborting — check sector names."
            ))
            return

        # Mapping ID -> (new sector, label)
        corrections = {}

        for id_ in ECLAIRAGE:
            corrections[str(id_)] = (sectors["eclairage"], "Éclairage public solaire")

        for id_ in EDUCATION:
            corrections[str(id_)] = (sectors["education_3salles"], "Education / 3 salles")

        for id_ in SANTE:
            corrections[str(id_)] = (sectors["sante"], "Santé / CSA-CSC")

        for id_ in INFRA_MARCHANDE_MAGASIN:
            corrections[str(id_)] = (sectors["magasin"], "Magasin de stockage")

        for id_ in INFRA_MARCHANDE_MARCHE:
            corrections[str(id_)] = (sectors["hangar_marche"], "Hangar de marché")

        for id_ in SPORT:
            corrections[str(id_)] = (sectors["sport_infra"], "Sport et loisirs / Infrastructure")

        for id_ in WASH - {10756}:
            corrections[str(id_)] = (sectors["wash_latrines"], "WASH / Blocs de latrines")
        # id=10756 "Assainissement fluvial" -> Hygiène des lieux publics
        corrections["10756"] = (sectors["wash_assain"], "WASH / Hygiène des lieux publics")

        for id_ in TRANSPORT_PISTE:
            corrections[str(id_)] = (sectors["piste"], "Transport / Piste")

        for id_ in TRANSPORT_FRANCHIS:
            corrections[str(id_)] = (sectors["franchissement"], "Transport / Franchissement")

        for id_ in TRANSPORT_CANIVEAU:
            corrections[str(id_)] = (sectors["piste"], "Transport / Caniveau → Piste")

        for id_ in PROD_VEGETALE:
            corrections[str(id_)] = (sectors["prod_veg"], "Production végétale / Aménagement")

        for id_ in TRANSFORMATION:
            corrections[str(id_)] = (sectors["transformation"], "Transformation / Equipement")

        for id_ in PROD_ANIMALE:
            corrections[str(id_)] = (sectors["prod_animale"], "Production animale / Equipement")

        # --- Coverage check: ensure every ID in every source set has a correction ---
        all_source_ids = set()
        for s in [
            ECLAIRAGE, EDUCATION, SANTE,
            INFRA_MARCHANDE_MAGASIN, INFRA_MARCHANDE_MARCHE,
            SPORT, WASH,
            TRANSPORT_PISTE, TRANSPORT_FRANCHIS, TRANSPORT_CANIVEAU,
            PROD_VEGETALE, TRANSFORMATION, PROD_ANIMALE,
        ]:
            all_source_ids |= {str(i) for i in s}

        dropped = all_source_ids - set(corrections.keys())
        if dropped:
            self.stdout.write(self.style.ERROR(
                f"  [WARNING] {len(dropped)} ID(s) in source sets have no correction entry "
                f"and will be silently skipped: {sorted(dropped)}"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"  Coverage check OK — all {len(all_source_ids)} source IDs have a correction entry."
            ))

        self.stdout.write(f"Corrections to apply: {len(corrections)}\n")

        updated   = 0
        not_found = 0
        by_label  = {}

        with transaction.atomic():
            for inv_id, (new_sector, label) in corrections.items():
                try:
                    inv = Investment.objects.get(id=inv_id)
                except Investment.DoesNotExist:
                    self.stdout.write(self.style.ERROR(
                        f"  [NOT FOUND] investment id={inv_id}"
                    ))
                    not_found += 1
                    continue

                old_sector = inv.sector.name if inv.sector else "None"
                by_label[label] = by_label.get(label, 0) + 1

                if dry_run:
                    self.stdout.write(
                        f"  [DRY] id={inv_id} | {old_sector} → {new_sector.name}\n"
                        f"        titre: {(inv.title or '')[:80]}"
                    )
                else:
                    inv.sector = new_sector
                    inv.save(update_fields=["sector"])

                updated += 1

            if dry_run:
                transaction.set_rollback(True)

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(
            f"{'[DRY RUN] ' if dry_run else ''}Done."
        ))
        self.stdout.write(f"  Updated    : {updated}")
        self.stdout.write(f"  Not found  : {not_found}")
        self.stdout.write("\n  By new sector:")
        for label, count in sorted(by_label.items(), key=lambda x: -x[1]):
            self.stdout.write(f"    {count:3d}  {label}")

        if not dry_run:
            self.stdout.write(self.style.WARNING(
                "\nRemember to verify PDL filters after correction."
            ))
