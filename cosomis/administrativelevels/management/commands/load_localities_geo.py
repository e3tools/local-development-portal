"""
Geolocate administrative levels (and their investments) from a folder of Benin
shapefiles, so the dashboard-summary map can render commune/village pins.

What it does, mirroring the one-off import that seeded the local DB:

1. Read the commune polygons (named) and reproject them to WGS84.
2. Read the locality points (an anonymous point cloud — no names) and reproject.
3. Spatially assign each locality point to the commune polygon that contains it.
4. Match DB communes to shapefile communes by normalized name and give each
   commune the centroid of its polygon.
5. Give each village a *distinct* real locality point that falls inside its own
   commune polygon (round-robin), so village pins spread realistically. The DB
   coordinate is village-accurate at commune level; which specific point maps to
   which village is arbitrary because the locality file carries no names.
6. Give arrondissements / departments the mean of their descendants' coordinates.
7. Push each investment's coordinate down from its administrative level.

The locality shapefile has no attribute (.dbf) table, so exact village->point
identity is impossible; this places every pin in the correct commune.

Usage:
    python manage.py load_localities_geo --dir /path/to/Benin_localities_shp
    python manage.py load_localities_geo --dir ... --dry-run
    python manage.py load_localities_geo --dir ... --alias PEHUNCO=PEHONKO

Requires: pyshp, pyproj, shapely (see requirements.txt).
"""

import os
import re
import random
import unicodedata
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from administrativelevels.models import AdministrativeLevel
from investments.models import Investment


def _normalize(name):
    """Case/accent/punctuation-insensitive key for matching commune names."""
    text = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _as_decimal(value):
    """AdministrativeLevel lat/long are DecimalField(max_digits=9, decimal_places=6)."""
    return Decimal(str(value)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


class Command(BaseCommand):
    help = (
        "Geolocate communes/villages and their investments from Benin shapefiles "
        "so the dashboard-summary map shows pins."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir", required=True,
            help="Folder containing the commune and locality shapefiles.",
        )
        parser.add_argument(
            "--commune-shp", default="ben_commune.shp",
            help="Commune polygon shapefile name (default: ben_commune.shp).",
        )
        parser.add_argument(
            "--locality-shp", default="ben_localite_2015.shp",
            help="Locality point shapefile name (default: ben_localite_2015.shp).",
        )
        parser.add_argument(
            "--commune-name-field", default="BN_NIV3",
            help="Attribute field holding the commune name (default: BN_NIV3).",
        )
        parser.add_argument(
            "--alias", action="append", default=[],
            metavar="DBNAME=SHPNAME",
            help="Map a DB commune name to a shapefile spelling, e.g. PEHUNCO=PEHONKO. "
                 "Repeatable.",
        )
        parser.add_argument(
            "--seed", type=int, default=42,
            help="Seed for the village->point assignment (reproducible).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Compute and report matches without writing to the database.",
        )

    # -- shapefile loading -------------------------------------------------

    def _load_geo(self, directory, commune_shp, locality_shp, name_field):
        try:
            import shapefile  # pyshp
            from pyproj import Transformer
            from shapely.geometry import shape, Point
            from shapely.prepared import prep
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise CommandError(
                "Missing geo dependencies. Install them with:\n"
                "    pip install pyshp pyproj shapely\n"
                f"(import error: {exc})"
            )

        commune_path = os.path.join(directory, commune_shp)
        locality_path = os.path.join(directory, locality_shp)
        for path in (commune_path, locality_path):
            if not os.path.exists(path):
                raise CommandError(f"Shapefile not found: {path}")

        def transformer_for(shp_path):
            """Build a transformer from the shapefile's .prj CRS to WGS84."""
            prj = os.path.splitext(shp_path)[0] + ".prj"
            if os.path.exists(prj):
                with open(prj) as handle:
                    src_crs = handle.read().strip()
            else:
                # Benin localities ship as UTM zone 31N.
                src_crs = "EPSG:32631"
                self.stdout.write(self.style.WARNING(
                    f"No .prj for {os.path.basename(shp_path)}; assuming EPSG:32631."
                ))
            return Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)

        # --- commune polygons: name -> (centroid_lat, centroid_lon, shapely geom)
        reader = shapefile.Reader(commune_path)
        fields = [f[0] for f in reader.fields[1:]]
        if name_field not in fields:
            raise CommandError(
                f"Commune name field '{name_field}' not in {commune_shp}. "
                f"Available fields: {fields}"
            )
        name_idx = fields.index(name_field)
        ct = transformer_for(commune_path)

        communes = {}  # normalized name -> dict(name, centroid, prepared geom)
        prepared = []  # (norm_name, prepared_geom, shapely_geom)
        for shape_rec in reader.iterShapeRecords():
            raw_name = shape_rec.record[name_idx]
            geom = shape(shape_rec.shape.__geo_interface__)
            # reproject every ring vertex to WGS84
            geom = self._reproject_geom(geom, ct)
            centroid = geom.centroid
            key = _normalize(raw_name)
            communes[key] = {
                "name": raw_name,
                "lat": centroid.y,
                "lon": centroid.x,
            }
            prepared.append((key, prep(geom), geom))
        reader.close()

        # --- locality points grouped by containing commune
        reader = shapefile.Reader(locality_path)
        lt = transformer_for(locality_path)
        points_by_commune = defaultdict(list)
        for shp in reader.iterShapes():
            x, y = shp.points[0][0], shp.points[0][1]
            lon, lat = lt.transform(x, y)
            pt = Point(lon, lat)
            for key, pgeom, _ in prepared:
                if pgeom.contains(pt):
                    points_by_commune[key].append((lat, lon))
                    break
        reader.close()

        return communes, points_by_commune

    @staticmethod
    def _reproject_geom(geom, transformer):
        from shapely.geometry import Polygon, MultiPolygon

        def rp(coords):
            return [transformer.transform(x, y) for x, y in coords]

        if geom.geom_type == "Polygon":
            return Polygon(rp(geom.exterior.coords),
                           [rp(r.coords) for r in geom.interiors])
        if geom.geom_type == "MultiPolygon":
            return MultiPolygon([
                Polygon(rp(p.exterior.coords), [rp(r.coords) for r in p.interiors])
                for p in geom.geoms
            ])
        raise CommandError(f"Unsupported commune geometry: {geom.geom_type}")

    # -- assignment --------------------------------------------------------

    def handle(self, *args, **options):
        directory = options["dir"]
        dry_run = options["dry_run"]
        AL = AdministrativeLevel

        alias = {}
        for item in options["alias"]:
            if "=" not in item:
                raise CommandError(f"--alias expects DBNAME=SHPNAME, got '{item}'")
            db_name, shp_name = item.split("=", 1)
            alias[_normalize(db_name)] = _normalize(shp_name)
        # Default alias observed in the Benin dataset.
        alias.setdefault(_normalize("PEHUNCO"), _normalize("PEHONKO"))

        def key_for(name):
            k = _normalize(name)
            return alias.get(k, k)

        self.stdout.write("Reading shapefiles (reproject + spatial join)...")
        communes, points_by_commune = self._load_geo(
            directory, options["commune_shp"], options["locality_shp"],
            options["commune_name_field"],
        )
        self.stdout.write(
            f"  {len(communes)} commune polygons, "
            f"{sum(len(v) for v in points_by_commune.values())} points joined."
        )

        rng = random.Random(options["seed"])
        for pts in points_by_commune.values():
            rng.shuffle(pts)

        def commune_ancestor(level):
            node = level
            while node is not None:
                if AL.matches_type(node.type, AL.COMMUNE):
                    return node
                node = node.parent
            return None

        al_coord = {}       # al.id -> (lat, lon) floats
        to_update = []
        cursor = defaultdict(int)
        missing_communes, missing_villages = [], []

        db_communes = list(AL.objects.filter(AL.type_filter_q(AL.COMMUNE)))
        db_villages = list(
            AL.objects.filter(AL.type_filter_q(AL.VILLAGE)).select_related("parent__parent")
        )

        # 1) communes -> polygon centroid
        for commune in db_communes:
            data = communes.get(key_for(commune.name))
            if data:
                commune.latitude = _as_decimal(data["lat"])
                commune.longitude = _as_decimal(data["lon"])
                al_coord[commune.id] = (data["lat"], data["lon"])
                to_update.append(commune)
            else:
                missing_communes.append(commune.name)

        # 2) villages -> distinct real point inside their commune (fallback centroid)
        for village in db_villages:
            commune = commune_ancestor(village)
            ck = key_for(commune.name) if commune else None
            pts = points_by_commune.get(ck) if ck else None
            if pts:
                lat, lon = pts[cursor[ck] % len(pts)]
                cursor[ck] += 1
            elif ck and ck in communes:
                lat, lon = communes[ck]["lat"], communes[ck]["lon"]
            else:
                missing_villages.append(village.name)
                continue
            village.latitude = _as_decimal(lat)
            village.longitude = _as_decimal(lon)
            al_coord[village.id] = (lat, lon)
            to_update.append(village)

        # 3) arrondissements + departments -> mean of descendants already placed
        for canonical in (AL.CANTON, AL.PREFECTURE):
            for node in AL.objects.filter(AL.type_filter_q(canonical)):
                kids = [al_coord[c.id] for c in AL.objects.filter(parent=node)
                        if c.id in al_coord]
                if not kids:
                    continue
                lat = sum(k[0] for k in kids) / len(kids)
                lon = sum(k[1] for k in kids) / len(kids)
                node.latitude = _as_decimal(lat)
                node.longitude = _as_decimal(lon)
                al_coord[node.id] = (lat, lon)
                to_update.append(node)

        # 4) investments -> coordinate of their administrative level (walk up)
        def coord_for(level):
            node = level
            while node is not None:
                if node.id in al_coord:
                    return al_coord[node.id]
                node = node.parent
            return None

        investment_updates = []
        investments_missing = 0
        investments = Investment.objects.select_related(
            "administrative_level__parent__parent__parent"
        )
        for investment in investments:
            coord = coord_for(investment.administrative_level) \
                if investment.administrative_level_id else None
            if coord:
                investment.latitude = float(coord[0])
                investment.longitude = float(coord[1])
                investment_updates.append(investment)
            else:
                investments_missing += 1

        # -- report + write ------------------------------------------------
        self.stdout.write(
            f"Communes:    {len(db_communes) - len(missing_communes)}/{len(db_communes)} matched"
        )
        if missing_communes:
            self.stdout.write(self.style.WARNING(
                f"  unmatched communes (add --alias?): {missing_communes}"
            ))
        self.stdout.write(
            f"Villages:    {len(db_villages) - len(missing_villages)}/{len(db_villages)} placed"
        )
        if missing_villages:
            self.stdout.write(self.style.WARNING(
                f"  unplaced villages: {len(missing_villages)} (e.g. {missing_villages[:5]})"
            ))
        self.stdout.write(
            f"Investments: {len(investment_updates)} geolocated, {investments_missing} missing"
        )

        if dry_run:
            self.stdout.write(self.style.NOTICE("Dry run — no changes written."))
            return

        with transaction.atomic():
            AL.objects.bulk_update(to_update, ["latitude", "longitude"], batch_size=500)
            Investment.objects.bulk_update(
                investment_updates, ["latitude", "longitude"], batch_size=1000
            )

        self.stdout.write(self.style.SUCCESS(
            f"Done. Updated {len(to_update)} administrative levels and "
            f"{len(investment_updates)} investments."
        ))
