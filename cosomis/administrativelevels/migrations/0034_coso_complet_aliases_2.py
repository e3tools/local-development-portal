from django.db import migrations

SOURCE = "coso_complet_import_34"

# ---------------------------------------------------------------------------
# Arrondissement aliases
# ---------------------------------------------------------------------------
ARR_ALIASES = {
    "TOUMBOUTOU":          ["TOMBOUTOU"],
    "BOUKOUMBE":           ["BOUKOMBE"],
    "FOO-TANCE":           ["FO TANCE"],
    "GNONKOUROKALI":       ["GNONKOROKALI"],
    "1ER  ARRONDISSEMENT": ["PARAKOU 1"],
    "GUINAGOUROU":         ["GUNINANGOUROU"],
    "DJOUGOU I":           ["DJOUGOU 1"],
    "DJOUGOU II":          ["DJOUGOU 2"],
    "DJOUGOU III":         ["DJOUGOU 3"],
    "NIKKI":               ["Nikki 1"],
}

# ---------------------------------------------------------------------------
# Village simple aliases: { arr_name_in_db: { village_db: [aliases] } }
# Covers espace vs tiret variants and other spelling differences.
# ---------------------------------------------------------------------------
VIL_ALIASES = {
    "BOGO-BOGO": {
        "BOGO-BOGO":              ["BOGO BOGO"],
    },
    "GAROU": {
        "GAROU-TÉDJI":            ["GAROU TEDJI"],
        "GAROU-BÉRI":             ["GAROU", "Garou"],
    },
    "GUENE": {
        "BANITÈ-FÈRÈ KIRÈ":       ["Banitè Fèrè-Kiré"],
        "GOUN-GOUN":              ["Goungoun", "GOUNGOUN"],
        "MOKOLLÉ":                ["Mokolé", "MOKOLÉ"],
    },
    "SEGBANA": {
        "GUÉNÉ KOUZI":            ["Guéné-Kouzi"],
        "MAFOUTA-WAASSARÈ":       ["Mafouta wassarè", "MAFOUTA WASSARÈ"],
    },
    "BASSO": {
        "NÉGANZI-PEULH":          ["Néganzi peulh", "NÉGANZI PEULH"],
    },
    "BOUCA": {
        "GANDO-GOUROU":           ["Gando Gourou"],
    },
    "DERASSI": {
        "GUIRI-GANDO":            ["Guiri Gando"],
    },
    "PEONGA": {
        "BOA-GANDO":              ["Boa Gando"],
        "ANGARADÉBOU DE PÉONGA":  ["Angaradébou", "ANGARADÉBOU"],
    },
    "TASSO": {
        "FO- DAROU":              ["Fo-Darou", "FO-DAROU"],
    },
    "GNINSY": {
        "SANDILO-GANDO":          ["Sandilo Gando"],
        "SANRÉKOU":               ["Sanèkou", "SANÈKOU"],
        "SOMBIRIKPÉROU":          ["Sombrikpérou", "SOMBRIKPÉROU"],
    },
    "SEKERE": {
        "SÈKÈRÈ-PEULH":           ["Sèkèrè Peulh", "SÈKÈRÈ PEULH"],
        "YARRA-BARIBA":           ["Yarra Bariba", "YARRA BARIBA"],
        "YARRA-GANDO":            ["Yarra Gando", "YARRA GANDO"],
        "SÈKÈRÈ-MARO":            ["SEKERE", "Sekere"],
    },
    "FOUNOUGO": {
        "FOUNOUGO-GAH":           ["FOUNOUGO", "Founougo"],
    },
    "KARIMAMA": {
        "KARIMAMA-BATOUMA-BÉRI":  ["Batouma-Béri", "BATOUMA-BÉRI"],
    },
    "MALANVILLE": {
        "TASSI-TÉDJI-BOULANGA":   ["Tassitédji-Boulanga", "TASSITÉDJI-BOULANGA"],
    },
    "BIRNI": {
        "BIRNI MARO":             ["BIRNI", "Birni"],
    },
    "PEHUNCO": {
        "PÉHUNCO I":              ["PEHUNCO", "Pehunco"],
    },
    "1ER  ARRONDISSEMENT": {
        "KPÉROU-GUÉRA":           ["Kpérou-Guerra", "KPÉROU-GUERRA"],
        "WOROU-TOKOROU":          ["Tourou-Monon", "TOUROU-MONON"],
    },
    "TCHATCHOU": {
        "ATIRA-KPAROU":           ["Atirakparou", "ATIRAKPAROU"],
        "GOKANNA":                ["Gokana", "GOKANA"],
        "KINNOU-KPAROU":          ["KINNOUKPANOU", "Kinnoukpanou"],
        "SAKANA- KPÉBA":          ["SAKANAKPEBA", "Sakanakpeba"],
    },
    "BASSILA": {
        "BASSILA ALLAN":          ["BASSILA", "Bassila"],
        "IGBOMAKRO":              ["Igbomacro", "IGBOMACRO"],
    },
    "MANIGRI": {
        "MANIGRI-IKANNI":         ["MANIGRI", "Manigri"],
    },
    "KORONTIERE": {
        "KOUPAGOU-KORONTIÈRE":    ["KORONTIERE", "Korontiere"],
    },
    "GUILMARO": {
        "BORO DE GUIMARO":        ["GUILMARO", "Guilmaro"],
    },
    "KOUANDE": {
        "MARO DE KOUANDE":        ["KOUANDE", "Kouande"],
    },
}

# ---------------------------------------------------------------------------
# Contextual aliases
# ---------------------------------------------------------------------------
CONTEXTUAL_ALIASES = [
    # N'DAHONTA — straight apostrophe in import vs typographic in DB
    # Already handled as arrondissement in 0032, but also needed as village
    {
        "alias":       "N'DAHONTA",
        "db_name":     "N\u2019DAHONTA",
        "db_type":     "village",
        "parent_name": "N\u2019DAHONTA",
        "parent_type": "arrondissement",
        "note":        "village homonyme de l'arrondissement, apostrophe droite vs typographique",
    },
    # KOUGNIERI under N'DAHONTA
    {
        "alias":       "Kougneri",
        "db_name":     "KOUGNIERI",
        "db_type":     "village",
        "parent_name": "N\u2019DAHONTA",
        "parent_type": "arrondissement",
        "note":        "KOUGNIERI under N'DAHONTA",
    },
    {
        "alias":       "KOUGNERI",
        "db_name":     "KOUGNIERI",
        "db_type":     "village",
        "parent_name": "N\u2019DAHONTA",
        "parent_type": "arrondissement",
        "note":        "KOUGNIERI under N'DAHONTA",
    },
    # MOUSSOUKOURÉ under OUENOU — OUENOU is ambiguous (2 communes)
    # under N'DALI
    {
        "alias":       "Mousoukouré",
        "db_name":     "MOUSSOUKOURÉ",
        "db_type":     "village",
        "parent_name": "OUENOU",
        "parent_type": "arrondissement",
        "grandparent_name": "N\u2019DALI",
        "grandparent_type": "commune",
        "note":        "MOUSSOUKOURÉ under OUENOU/N'DALI",
    },
    {
        "alias":       "MOUSOUKOURÉ",
        "db_name":     "MOUSSOUKOURÉ",
        "db_type":     "village",
        "parent_name": "OUENOU",
        "parent_type": "arrondissement",
        "grandparent_name": "N\u2019DALI",
        "grandparent_type": "commune",
        "note":        "MOUSSOUKOURÉ under OUENOU/N'DALI",
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
        if "grandparent_name" in entry:
            gp_qs = AdministrativeLevel.objects.filter(
                name__iexact=entry["grandparent_name"],
                type__iexact=entry["grandparent_type"],
            )
            if not gp_qs.exists():
                errors.append(f"CONTEXTUAL grandparent NOT FOUND '{entry['grandparent_name']}'")
                continue
            parent_qs = parent_qs.filter(parent=gp_qs.first())

        if not parent_qs.exists():
            errors.append(f"CONTEXTUAL parent NOT FOUND '{entry['parent_name']}'")
            continue
        if parent_qs.count() > 1:
            errors.append(f"CONTEXTUAL parent AMBIGUOUS '{entry['parent_name']}' ({parent_qs.count()} results)")
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
        f"\n[0034_coso_complet_aliases_2] "
        f"created={created}, skipped={skipped}, errors={len(errors)}"
    )
    for e in errors:
        print(f"  ⚠️  {e}")


def depopulate_aliases(apps, schema_editor):
    AdministrativeLevelAlias = apps.get_model("administrativelevels", "AdministrativeLevelAlias")
    AdministrativeLevelAlias.objects.filter(source=SOURCE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("administrativelevels", "0033_commune_aliases"),
    ]

    operations = [
        migrations.RunPython(populate_aliases, reverse_code=depopulate_aliases),
    ]
