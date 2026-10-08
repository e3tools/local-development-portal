"""
Second pass fix for investments incorrectly classified under "Forage + abreuvoir".

Context:
  "Forage + abreuvoir" should only contain investments that explicitly combine
  a borehole (forage) with animal watering infrastructure. This command moves
  investments that are purely pastoral (couloirs, barrages, retenues d'eau,
  aires de pâturage) to their correct sector.

Corrections:
  - 138 -> Production animale / Aménagement (barrages, retenues, couloirs pastoraux)
  -  15 -> Forage simple (eau potable generics with no animal component)
  -   6 -> Poste d'eau autonome (PEA) (confirmed PEA projects)
  -   1 -> Production végétale / Aménagement (bas-fond riziculture)
  -   1 -> Autre / Autre (multi-subject investment)

Run:
    python manage.py fix_forage_categorization_2 --dry-run
    python manage.py fix_forage_categorization_2
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from investments.models import Investment
from administrativelevels.models import Sector, Category


# ---------------------------------------------------------------------------
# ID sets — manually arbitrated
# ---------------------------------------------------------------------------

# Production animale / Aménagement
# Barrages, retenues d'eau, couloirs pastoraux, aires de pâturage,
# surcreusements without explicit forage mention
TO_PROD_ANIMALE = {
    2825,2984,3003,3174,3503,3714,3751,3770,3793,3829,
    4173,4250,4658,4677,4763,4881,
    5072,5111,5132,5149,5186,5570,5651,5662,5668,5878,5969,
    6310,6329,6350,6370,6391,6701,6722,6904,6962,6981,
    7001,7002,7021,7023,7063,7121,7342,7403,7458,7638,7658,7717,7895,
    8288,8354,8613,8634,8890,
    9334,9431,9553,9655,9694,9864,
    10484,11082,11196,11296,11643,
    12221,12422,
    13083,13086,13093,13180,13498,13884,
    14159,14196,14198,14396,14454,14866,14925,
    15111,15242,15245,15246,15401,
    15455,15456,15457,15463,15466,15474,15475,15485,
    15539,15540,15541,15542,
    15576,15577,15585,15587,15589,15593,15615,
    15682,15683,15684,15686,15687,15689,
    15752,15753,15759,
    15826,
    15875,15876,15877,15882,15884,15889,15891,15892,15894,
    15901,15904,15914,15915,15925,15930,15931,15932,15933,15934,
    15939,15940,15963,15971,
}

# Forage simple — generic "eau potable" titles with no pastoral component
TO_FORAGE_SIMPLE = {
    8375,8432,8450,8470,8490,8510,8546,
    11605,12566,13604,13080,8533,5233,
    8713,12901,
}

# Poste d'eau autonome (PEA)
TO_PEA = {15489,15490,15491,15524,5713,15995}

# Production végétale / Aménagement
TO_PROD_VEGETALE = {9251}

# Autre / Autre
TO_AUTRE = {14336}


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

    # 3. Not found
    return None


class Command(BaseCommand):
    help = (
        "Second pass fix: reclassifies investments under 'Forage + abreuvoir' "
        "that are actually pastoral infrastructure (barrages, couloirs, retenues d'eau)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "*** DRY RUN — no changes will be written to the database ***\n"
                )
            )

        # ------------------------------------------------------------------
        # Categories
        # ------------------------------------------------------------------

        try:
            cat_animale = Category.objects.get(name="Production animale")
            cat_vegetale = Category.objects.get(name="Production végétale")
            cat_autre = Category.objects.get(name="Autre")
        except Category.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f"Category not found: {e}"))
            return

        # ------------------------------------------------------------------
        # Sectors
        # ------------------------------------------------------------------

        sector_animale = Sector.objects.filter(
            name="Aménagement",
            category=cat_animale,
        ).first()

        sector_vegetale = Sector.objects.filter(
            name="Aménagement",
            category=cat_vegetale,
        ).first()

        sector_forage = get_sector("Forage simple")
        sector_pea = get_sector("Poste d'eau autonome (PEA)")

        sector_autre = Sector.objects.filter(
            name="Autre",
            category=cat_autre,
        ).first()

        for label, sector in [
            ("Aménagement/Production animale", sector_animale),
            ("Aménagement/Production végétale", sector_vegetale),
            ("Forage simple", sector_forage),
            ("Poste d'eau autonome (PEA)", sector_pea),
            ("Autre", sector_autre),
        ]:
            if not sector:
                self.stdout.write(
                    self.style.ERROR(f"Sector not found: {label}")
                )
                return

        # ------------------------------------------------------------------
        # Build corrections mapping
        # ------------------------------------------------------------------

        corrections = {}

        for id_ in TO_PROD_ANIMALE:
            corrections[str(id_)] = (
                sector_animale,
                "Production animale / Aménagement",
            )

        for id_ in TO_FORAGE_SIMPLE:
            corrections[str(id_)] = (
                sector_forage,
                "Forage simple",
            )

        for id_ in TO_PEA:
            corrections[str(id_)] = (
                sector_pea,
                "Poste d'eau autonome (PEA)",
            )

        for id_ in TO_PROD_VEGETALE:
            corrections[str(id_)] = (
                sector_vegetale,
                "Production végétale / Aménagement",
            )

        for id_ in TO_AUTRE:
            corrections[str(id_)] = (
                sector_autre,
                "Autre",
            )

        # ------------------------------------------------------------------
        # Coverage check
        # ------------------------------------------------------------------

        all_source_ids = {
            str(i)
            for i in (
                TO_PROD_ANIMALE
                | TO_FORAGE_SIMPLE
                | TO_PEA
                | TO_PROD_VEGETALE
                | TO_AUTRE
            )
        }

        dropped = all_source_ids - set(corrections.keys())

        if dropped:
            self.stdout.write(
                self.style.ERROR(
                    f"  [WARNING] {len(dropped)} ID(s) in source sets "
                    f"have no correction entry and will be silently skipped: "
                    f"{sorted(dropped)}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Coverage check OK — all {len(all_source_ids)} "
                    f"source IDs have a correction entry."
                )
            )

        self.stdout.write(
            f"Corrections to apply: {len(corrections)}\n"
        )

        updated = 0
        not_found = 0
        by_label = {}

        with transaction.atomic():
            for inv_id, (new_sector, label) in corrections.items():
                try:
                    inv = Investment.objects.get(id=inv_id)
                except Investment.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  [NOT FOUND] investment id={inv_id}"
                        )
                    )
                    not_found += 1
                    continue

                old_sector = inv.sector.name if inv.sector else "None"

                by_label[label] = by_label.get(label, 0) + 1

                if dry_run:
                    self.stdout.write(
                        f"  [DRY] id={inv_id} | "
                        f"{old_sector} -> {new_sector.name} "
                        f"({new_sector.category.name})\n"
                        f"        titre: {(inv.title or '')[:80]}"
                    )
                else:
                    inv.sector = new_sector
                    inv.save(update_fields=["sector"])

                updated += 1

            if dry_run:
                transaction.set_rollback(True)

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f"{'[DRY RUN] ' if dry_run else ''}Done."
            )
        )

        self.stdout.write(f"  Updated    : {updated}")
        self.stdout.write(f"  Not found  : {not_found}")

        self.stdout.write("\n  By new sector:")

        for label, count in sorted(
            by_label.items(),
            key=lambda x: -x[1]
        ):
            self.stdout.write(f"    {count:3d}  {label}")

        if not dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nRemember to verify PDL filters after correction."
                )
            )