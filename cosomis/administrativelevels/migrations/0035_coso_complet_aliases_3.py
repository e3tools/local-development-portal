from django.db import migrations

SOURCE = "coso_complet_import_35"

# ---------------------------------------------------------------------------
# Village simple aliases
# ---------------------------------------------------------------------------
VIL_ALIASES = {
    "GOUANDE": {
        "GOUANDÉ":                  ["GOUANDE"],
    },
    "TOBRE": {
        "TOBRÉ":                    ["TOBRE"],
    },
    "DERASSI": {
        "DÉRASSI":                  ["DERASSI", "Dèrassi"],
    },
    "PEONGA": {
        "PÉONGA":                   ["PEONGA"],
    },
    "ALEDJO": {
        "ALÉDJO":                   ["ALEDJO"],
    },
    "PENESSOULOU": {
        "PÉNESSOULOU":              ["PENESSOULOU"],
    },
    "BADJOUDE": {
        "BADJOUDÈ":                 ["BADJOUDE"],
    },
    "KOMDE": {
        "KOMDÈ":                    ["KOMDE"],
    },
    "MADECALI": {
        "MADÉCALI":                 ["MADECALI", "Madécali-Fada", "MADÉCALI-FADA"],
        "MÉLAYAKOUARA":             ["Mélayakoara", "MÉLAYAKOARA"],
    },
    "GUINAGOUROU": {
        "BÉRÉKOUDO":                ["Bèrèkoudo", "BÈRÈKOUDO", "Bérékoundo", "BÉRÉKOUNDO"],
        "Gah-Maro":                 ["Gah Maro", "GAH MARO", "Toutes les 20 ADV de Guinagourou :porté par l'ADQ Gah Maro"],
    },
    "GNONKOUROKALI": {
        "GOUROU-PIBOU":             ["GOUROU PIBOU"],
        "GNONKOURAKALI":            ["GNONKOROKALI"],
    },
    "WARA": {
        "DASSARI DE WARA":          ["DASSARI"],
    },
    "KARIMAMA": {
        "KARIMAMA-DENDI-KOURÉ":     ["KARIMAMA"],
        "GOUROU BÉRI":              ["Goroubéri", "GOROUBÉRI"],
    },
    "GUENE": {
        "GUÉNÉ-ZERMÉ":              ["Guéné-Zermè", "GUÉNÉ-ZERMÈ"],
        "SOUNBEY-GOROU":            ["Soumbégorou", "SOUMBÉGOROU"],
    },
    "SEGBANA": {
        "LIMAFRANI":                ["Limanfrani", "LIMANFRANI"],
        "BATAZI":                   ["Porté par Batazi et\nLimanfrani"],
    },
    "1ER  ARRONDISSEMENT": {
        "BOSSO-CAMPS-PEULHS":       ["Bosso-Camp-Peulh"],
        "BÈYAROU":                  ["Bèyèrou"],
        "KPÉBIÉ DE PARAKOU1":       ["Kpébié", "KPÉBIÉ"],
    },
    "BASSILA": {
        "BIGUINA HOLOUDÈ":          ["Biguina Holloudè", "BIGUINA HOLLOUDÈ"],
    },
    "DJOUGOU I": {
        "ZONGO DE DJOUGOU1":        ["Zongo de Djougou", "ZONGO DE DJOUGOU"],
    },
    "NIKKI": {
        "MONNON DE NIKKI":          ["Monnon", "MONNON"],
        "TONTAROU":                 ["Tontarou, Kali, Gourou, Danri et  Sonwore"],
        "GBAOUSSI-KPAA":            ["Gbaoussi kpaa", "GBAOUSSI KPAA"],
    },
        "TCHATCHOU": {
        "SAKANA- KPÉBA":            ["Sakanakpéba", "SAKANAKPÉBA"],
        "SOUMON-GAH":               ["Soumon Gah", "SOUMON GAH"],
    },
    "KOMPA": {
        "KOMPA":                    ["Kompa, Banizoumou,  Kéné-Tounga, Kompanti, Dangazori, Gounngou-Béri,  Garbey-koara"],
        "GOUNGOU-BÉRI":             ["Gounngou-Béri", "GOUNNGOU-BÉRI"],
        "BANIZOUMBOU":              ["Banizoumou", "BANIZOUMOU"],
    },
    "GOMIA": {
        "BÈRÈKÈ-GOUROU":            ["Bèrèkè Gourou", "BÈRÈKÈ GOUROU"],
    },
}

# ---------------------------------------------------------------------------
# Contextual aliases — wrong parent or ambiguous
# ---------------------------------------------------------------------------
CONTEXTUAL_ALIASES = [
    # 1er Arrondissement — casse différente dans l'import
    {
        "alias":       "Bosso-Camp-Peulh",
        "db_name":     "BOSSO-CAMPS-PEULHS",
        "db_type":     "village",
        "parent_name": "1ER  ARRONDISSEMENT",
        "parent_type": "arrondissement",
        "note":        "1er Arrondissement casse variant",
    },
    {
        "alias":       "Bèyèrou",
        "db_name":     "BÈYAROU",
        "db_type":     "village",
        "parent_name": "1ER  ARRONDISSEMENT",
        "parent_type": "arrondissement",
        "note":        "1er Arrondissement casse variant",
    },
    {
        "alias":       "Kpébié",
        "db_name":     "KPÉBIÉ DE PARAKOU1",
        "db_type":     "village",
        "parent_name": "1ER  ARRONDISSEMENT",
        "parent_type": "arrondissement",
        "note":        "1er Arrondissement casse variant",
    },
    # FOO-TANCE — village TANCÉ sous FOO-TANCE
    {
        "alias":       "FO TANCE",
        "db_name":     "TANCÉ",
        "db_type":     "village",
        "parent_name": "FOO-TANCE",
        "parent_type": "arrondissement",
        "note":        "FO TANCE -> TANCÉ chef-lieu de FOO-TANCE",
    },
    # NATA — chef-lieu KOUDOGOU sous NATA
    {
        "alias":       "NATTA",
        "db_name":     "KOUDOGOU",
        "db_type":     "village",
        "parent_name": "NATA",
        "parent_type": "arrondissement",
        "note":        "NATTA -> premier village de NATA",
    },
    # GAMIA/GOMIA — chef-lieu GAMIA-EST sous GOMIA
    {
        "alias":       "GAMIA",
        "db_name":     "GAMIA-EST",
        "db_type":     "village",
        "parent_name": "GOMIA",
        "parent_type": "arrondissement",
        "note":        "GAMIA -> GAMIA-EST chef-lieu de GOMIA",
    },
    # BOUKOUMBE — chef-lieu Koussocoingou
    {
        "alias":       "BOUKOMBE",
        "db_name":     "KOUSSOCOINGOU",
        "db_type":     "village",
        "parent_name": "BOUKOUMBE",
        "parent_type": "arrondissement",
        "note":        "BOUKOMBE -> KOUSSOCOINGOU premier village de BOUKOUMBE",
    },
    # PARAKOU 1 -> chef-lieu sous 1ER ARRONDISSEMENT
    {
        "alias":       "PARAKOU 1",
        "db_name":     "GOUNIN DE PARAKOU1",
        "db_type":     "village",
        "parent_name": "1ER  ARRONDISSEMENT",
        "parent_type": "arrondissement",
        "note":        "PARAKOU 1 -> premier village de 1ER ARRONDISSEMENT",
    },
    # GUNINANGOUROU -> GUINAGOUROU village
    {
        "alias":       "GUNINANGOUROU",
        "db_name":     "GUINAGOUROU",
        "db_type":     "village",
        "parent_name": "GUINAGOUROU",
        "parent_type": "arrondissement",
        "note":        "GUNINANGOUROU -> GUINAGOUROU village chef-lieu",
    },
    # GNONKOROKALI -> GNONKOURAKALI village
    {
        "alias":       "GNONKOROKALI",
        "db_name":     "GNONKOURAKALI",
        "db_type":     "village",
        "parent_name": "GNONKOUROKALI",
        "parent_type": "arrondissement",
        "note":        "GNONKOROKALI -> GNONKOURAKALI village chef-lieu",
    },
    # DJOUGOU 1/2/3 -> chef-lieu sous DJOUGOU I/II/III
    {
        "alias":       "DJOUGOU 1",
        "db_name":     "MORWATCHOHI",
        "db_type":     "village",
        "parent_name": "DJOUGOU I",
        "parent_type": "arrondissement",
        "note":        "DJOUGOU 1 -> premier village de DJOUGOU I",
    },
    {
        "alias":       "DJOUGOU 2",
        "db_name":     "BASSALA",
        "db_type":     "village",
        "parent_name": "DJOUGOU II",
        "parent_type": "arrondissement",
        "note":        "DJOUGOU 2 -> premier village de DJOUGOU II",
    },
    {
        "alias":       "DJOUGOU 3",
        "db_name":     "BATOULOU",
        "db_type":     "village",
        "parent_name": "DJOUGOU III",
        "parent_type": "arrondissement",
        "note":        "DJOUGOU 3 -> premier village de DJOUGOU III",
    },
    # KARIMAMA multi-village -> porteur = FAKARA
    {
        "alias":       "Fakara, Dendi-kouré, Batouma-béri, Bello-Tounga, Goroubéri et Mamassy-peulh",
        "db_name":     "FAKARA",
        "db_type":     "village",
        "parent_name": "KARIMAMA",
        "parent_type": "arrondissement",
        "note":        "multi-village -> porteur = FAKARA",
    },
    # OUENOU villages under N'DALI — ambiguous parent
    {
        "alias":       "Ouénou Peulh",
        "db_name":     "OUÉNOU-PEULH",
        "db_type":     "village",
        "parent_name": "OUENOU",
        "parent_type": "arrondissement",
        "grandparent_name": "N\u2019DALI",
        "grandparent_type": "commune",
        "note":        "OUÉNOU-PEULH under OUENOU/N'DALI",
    },
    {
        "alias":       "OUÉNOU PEULH",
        "db_name":     "OUÉNOU-PEULH",
        "db_type":     "village",
        "parent_name": "OUENOU",
        "parent_type": "arrondissement",
        "grandparent_name": "N\u2019DALI",
        "grandparent_type": "commune",
        "note":        "OUÉNOU-PEULH under OUENOU/N'DALI",
    },
]


def populate_aliases(apps, schema_editor):
    AdministrativeLevel = apps.get_model("administrativelevels", "AdministrativeLevel")
    AdministrativeLevelAlias = apps.get_model("administrativelevels", "AdministrativeLevelAlias")

    created = 0
    skipped = 0
    errors  = []

    # --- Village simple aliases ---
    seen_arrs = {}
    for arr_name, entries in VIL_ALIASES.items():
        if arr_name in seen_arrs:
            arr = seen_arrs[arr_name]
        else:
            arr_qs = AdministrativeLevel.objects.filter(
                name__iexact=arr_name, type__iexact="arrondissement",
            )
            if not arr_qs.exists():
                errors.append(f"ARR NOT FOUND '{arr_name}'")
                continue
            if arr_qs.count() > 1:
                errors.append(f"ARR AMBIGUOUS '{arr_name}' ({arr_qs.count()} results)")
                continue
            arr = arr_qs.first()
            seen_arrs[arr_name] = arr

        for db_vil_name, alias_list in entries.items():
            vil_qs = AdministrativeLevel.objects.filter(
                name__iexact=db_vil_name, type__iexact="village", parent=arr,
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
            name__iexact=entry["parent_name"], type__iexact=entry["parent_type"],
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
            name__iexact=entry["db_name"], type__iexact=entry["db_type"], parent=parent,
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
        f"\n[0035_coso_complet_aliases_3] "
        f"created={created}, skipped={skipped}, errors={len(errors)}"
    )
    for e in errors:
        print(f"  ⚠️  {e}")


def depopulate_aliases(apps, schema_editor):
    AdministrativeLevelAlias = apps.get_model("administrativelevels", "AdministrativeLevelAlias")
    AdministrativeLevelAlias.objects.filter(source=SOURCE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("administrativelevels", "0034_coso_complet_aliases_2"),
    ]

    operations = [
        migrations.RunPython(populate_aliases, reverse_code=depopulate_aliases),
    ]
