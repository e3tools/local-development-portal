from django.db import migrations

SOURCE = "coso_complet_import_32"

# ---------------------------------------------------------------------------
# New arrondissement aliases not covered by 0030/0031
# ---------------------------------------------------------------------------
ARR_ALIASES = {
    "NIKKI":     ["NIKKI 1", "Nikki 1"],
    "KALALE":    ["KALALÉ", "Kalalé"],
    "GOMIA":     ["GAMIA", "Gamia"],
    "FOO-TANCE": ["FÔ-TANCE", "Fô-Tance"],
}

# ---------------------------------------------------------------------------
# Simple village aliases: { arr_name_in_db: { village_db: [aliases] } }
# Only real aliases needed — exact iexact matches are handled automatically.
# ---------------------------------------------------------------------------
VIL_ALIASES = {
    "FOUNOUGO": {
        "GOUGNIROU-GAH":          ["Gougnirou peulh", "GOUGNIROU PEULH"],
    },
    "WARA": {
        "DASSARI DE WARA":        ["DASSARI", "Dassari"],
        "KALÉ":                   ["KALE", "Kale"],
    },
    "KARIMAMA": {
        "KARIMAMA-DENDI-KOURÉ":   ["Dendi-kouré", "DENDI-KOURÉ"],
    },
    "KOMPA": {
        "KOMPA": [
            "07 ADV (Banizoumou, kompa, Kéné-Tounga, Kompanti, Dangazori, Gounngou-Béri,  Garbey-koara ) ",
        ],
    },
    "GUENE": {
        "SOUNBEY-GOROU":          ["Soumbégorou", "SOUMBÉGOROU"],
    },
    "MADECALI": {
        "MADÉCALI":               ["Madécali-Fada", "MADÉCALI-FADA"],
        "MÉLAYAKOUARA":           ["Mélayakoara", "MÉLAYAKOARA"],
    },
    "TOUMBOUTOU": {
        "DÈGUÈ-DÈGUÉ":            ["Dèguè-Dèguè", "DÈGUÈ-DÈGUÈ"],
    },
    "SEGBANA": {
        "LIMAFRANI":              ["Limanfrani", "LIMANFRANI"],
        "SAMTIMBARA":             ["Satimbara", "SATIMBARA"],
    },
    "KOABAGOU": {
        "KAOBAGOU":               ["Koabagou", "KOABAGOU"],
    },
    "DERASSI": {
        "GANNOURÈ-HÈRÈ":          ["Gannourèhèrè", "GANNOURÈHÈRÈ"],
    },
    "NIKKI": {
        "GOUROU DE NIKKI":        ["GOUROU PIBOU", "Gourou Pibou"],
        "KPAWOLOU DE NIKKI":      ["Kpawolou", "KPAWOLOU"],
        "MONNON DE NIKKI":        ["Monnon", "MONNON"],
    },
    "1ER  ARRONDISSEMENT": {
        "BÈYAROU":                ["Bèyèrou", "BÈYÈROU"],
        "BOSSO-CAMPS-PEULHS":     ["Bosso-Camp-Peulh", "BOSSO-CAMP-PEULH"],
    },
    "BASSILA": {
        "BIGUINA HOLOUDÈ":        ["Biguina Holloudè", "BIGUINA HOLLOUDÈ"],
    },
    "DJOUGOU I": {
        "ZONGO DE DJOUGOU1":      ["Zongo de Djougou", "ZONGO DE DJOUGOU"],
    },
    "PARTAGO": {
        "ABINTAGA":               ["Abitanga", "ABITANGA"],
        "MONMONGOU":              ["Momongou", "MOMONGOU"],
        "NANOGOU":                ["Nanougou", "NANOUGOU"],
    },
    "TCHATCHOU": {
        "SOUMON-GAH":             ["Soumon Gah", "SOUMON GAH"],
    },
}

# ---------------------------------------------------------------------------
# Contextual aliases: villages/arrondissements placed under wrong parent
# in import files but resolvable via their correct parent in DB.
# ---------------------------------------------------------------------------
CONTEXTUAL_ALIASES = [
# GNONKOUROKALI villages — import puts them under arrondissement NIKKI
    {
        "alias":       "GBARI",
        "db_name":     "GBARI",
        "db_type":     "village",
        "parent_name": "GNONKOUROKALI",
        "parent_type": "arrondissement",
        "note":        "import lists under NIKKI, DB has it under GNONKOUROKALI",
    },
    {
        "alias":       "GUINROU",
        "db_name":     "GUINROU",
        "db_type":     "village",
        "parent_name": "GNONKOUROKALI",
        "parent_type": "arrondissement",
        "note":        "import lists under NIKKI, DB has it under GNONKOUROKALI",
    },
    {
        "alias":       "GUINROU PEULH",
        "db_name":     "GUINROU-PEULH",
        "db_type":     "village",
        "parent_name": "GNONKOUROKALI",
        "parent_type": "arrondissement",
        "note":        "import lists under NIKKI, DB has it under GNONKOUROKALI",
    },
    {
        "alias":       "GNELTOKO",
        "db_name":     "GNELTOKO",
        "db_type":     "village",
        "parent_name": "GNONKOUROKALI",
        "parent_type": "arrondissement",
        "note":        "import lists under NIKKI, DB has it under GNONKOUROKALI",
    },
    {
        "alias":       "WOROUMANGASSAROU",
        "db_name":     "WOROUMANGASSAROU",
        "db_type":     "village",
        "parent_name": "GNONKOUROKALI",
        "parent_type": "arrondissement",
        "note":        "import lists under NIKKI, DB has it under GNONKOUROKALI",
    },
    {
        "alias":       "Gnonkourokali",
        "db_name":     "GNONKOURAKALI",
        "db_type":     "village",
        "parent_name": "GNONKOUROKALI",
        "parent_type": "arrondissement",
        "note":        "village homonyme de l'arrondissement, casse différente",
    },
    {
        "alias":       "GUINMA",
        "db_name":     "GUEMA",
        "db_type":     "village",
        "parent_name": "GNONKOUROKALI",
        "parent_type": "arrondissement",
        "note":        "import GUINMA -> DB GUEMA, both under GNONKOUROKALI",
    },
    {
        "alias":       "SOUBO GANDEROU",
        "db_name":     "SOUBO-GAND\u00c9ROU",
        "db_type":     "village",
        "parent_name": "GNONKOUROKALI",
        "parent_type": "arrondissement",
        "note":        "space vs hyphen, import lists under NIKKI",
    },
    {
        "alias":       "SOUBO BARAWOROU",
        "db_name":     "SOUBO-BARAWOROU",
        "db_type":     "village",
        "parent_name": "GNONKOUROKALI",
        "parent_type": "arrondissement",
        "note":        "space vs hyphen, import lists under NIKKI",
    },
    # N'DAHONTA — straight apostrophe in import vs typographic in DB
    {
        "alias":       "N'DAHONTA",
        "db_name":     "N\u2019DAHONTA",
        "db_type":     "arrondissement",
        "parent_name": "TANGUIETA",
        "parent_type": "commune",
        "note":        "straight apostrophe \\u0027 vs typographic \\u2019",
    },
]


def populate_aliases(apps, schema_editor):
    AdministrativeLevel = apps.get_model("administrativelevels", "AdministrativeLevel")
    AdministrativeLevelAlias = apps.get_model("administrativelevels", "AdministrativeLevelAlias")

    created = 0
    skipped = 0
    errors  = []

    # --- Arrondissement aliases ---
    for db_name, alias_list in ARR_ALIASES.items():
        qs = AdministrativeLevel.objects.filter(
            name__iexact=db_name,
            type__iexact="arrondissement",
        )
        if not qs.exists():
            errors.append(f"NOT FOUND [arrondissement] '{db_name}'")
            continue
        if qs.count() > 1:
            errors.append(f"AMBIGUOUS [arrondissement] '{db_name}' ({qs.count()} results)")
            continue
        adm = qs.first()
        for alias in alias_list:
            _, was_created = AdministrativeLevelAlias.objects.get_or_create(
                administrative_level=adm,
                name=alias,
                defaults={"source": SOURCE},
            )
            created += was_created
            skipped += not was_created

    # --- Village simple aliases ---
    for arr_name, entries in VIL_ALIASES.items():
        arr_qs = AdministrativeLevel.objects.filter(
            name__iexact=arr_name,
            type__iexact="arrondissement",
        )
        if not arr_qs.exists():
            errors.append(f"ARR NOT FOUND '{arr_name}'")
            continue
        if arr_qs.count() > 1:
            errors.append(f"ARR AMBIGUOUS '{arr_name}' ({arr_qs.count()} results)")
            continue
        arr = arr_qs.first()

        for db_vil_name, alias_list in entries.items():
            vil_qs = AdministrativeLevel.objects.filter(
                name__iexact=db_vil_name,
                type__iexact="village",
                parent=arr,
            )
            if not vil_qs.exists():
                errors.append(f"VIL NOT FOUND '{db_vil_name}' under '{arr_name}'")
                continue
            adm = vil_qs.first()
            for alias in alias_list:
                _, was_created = AdministrativeLevelAlias.objects.get_or_create(
                    administrative_level=adm,
                    name=alias,
                    defaults={"source": SOURCE},
                )
                created += was_created
                skipped += not was_created

    # --- Contextual aliases ---
    for entry in CONTEXTUAL_ALIASES:
        parent_qs = AdministrativeLevel.objects.filter(
            name__iexact=entry["parent_name"],
            type__iexact=entry["parent_type"],
        )
        if not parent_qs.exists():
            errors.append(
                f"CONTEXTUAL parent NOT FOUND [{entry['parent_type']}] '{entry['parent_name']}'"
            )
            continue
        if parent_qs.count() > 1:
            errors.append(
                f"CONTEXTUAL parent AMBIGUOUS '{entry['parent_name']}' ({parent_qs.count()} results)"
            )
            continue
        parent = parent_qs.first()

        # If grandparent specified, narrow parent lookup first
        if "grandparent_name" in entry:
            grandparent_qs = AdministrativeLevel.objects.filter(
                name__iexact=entry["grandparent_name"],
                type__iexact=entry["grandparent_type"],
            )
            if not grandparent_qs.exists():
                errors.append(
                    f"CONTEXTUAL grandparent NOT FOUND '{entry['grandparent_name']}'"
                )
                continue
            parent_qs = parent_qs.filter(parent=grandparent_qs.first())
            if not parent_qs.exists():
                errors.append(
                    f"CONTEXTUAL parent NOT FOUND '{entry['parent_name']}'"
                    f" under '{entry['grandparent_name']}'"
                )
                continue
            if parent_qs.count() > 1:
                errors.append(
                    f"CONTEXTUAL parent AMBIGUOUS '{entry['parent_name']}'"
                    f" ({parent_qs.count()} results)"
                )
                continue
            parent = parent_qs.first()

        adm_qs = AdministrativeLevel.objects.filter(
            name__iexact=entry["db_name"],
            type__iexact=entry["db_type"],
            parent=parent,
        )
        if not adm_qs.exists():
            errors.append(
                f"CONTEXTUAL NOT FOUND '{entry['db_name']}' under '{entry['parent_name']}'"
                f" — {entry.get('note', '')}"
            )
            continue
        adm = adm_qs.first()
        _, was_created = AdministrativeLevelAlias.objects.get_or_create(
            administrative_level=adm,
            name=entry["alias"],
            defaults={"source": SOURCE},
        )
        created += was_created
        skipped += not was_created

    print(
        f"\n[0032_coso_complet_aliases] "
        f"created={created}, skipped={skipped}, errors={len(errors)}"
    )
    for e in errors:
        print(f"  ⚠️  {e}")


def depopulate_aliases(apps, schema_editor):
    AdministrativeLevelAlias = apps.get_model("administrativelevels", "AdministrativeLevelAlias")
    AdministrativeLevelAlias.objects.filter(source=SOURCE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("administrativelevels", "0031_realisation_image_aliases"),
    ]

    operations = [
        migrations.RunPython(populate_aliases, reverse_code=depopulate_aliases),
    ]
