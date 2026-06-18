from django.db import migrations

SOURCE = "coso_import"

# Actual types stored in the production DB:
#   country       →  1  (Benin root)
#   département   →  4
#   commune       → 27
#   arrondissement → 73
#   village       → 848
#
# Key points:
#   - The DB uses typographic apostrophe \u2019 in some names (N\u2019DALI,
#     N\u2019DAHONTA, etc.) while import files use straight apostrophe \u0027.
#     These cases are handled by explicit aliases rather than normalisation,
#     so that names like "1ER  ARRONDISSEMENT" (double space, identical in DB
#     and import) are not accidentally mangled.
#   - Ambiguous names (same name, different parent) are in CONTEXTUAL_ALIASES
#     and resolved by (db_name, db_type, parent_name, parent_type).

SIMPLE_ALIASES = {
    "commune": {
        "BEMBEREKE": [
            "BEMBÈRÈKÈ"
        ],
        "N’DALI": [
            "N'DALI"
        ]
    },
    "arrondissement": {
        "FOO-TANCE": [
            "FÔ-TANCE"
        ],
        "GOMIA": [
            "GAMIA"
        ],
        "KALALE": [
            "KALALÉ"
        ],
        "NATA": [
            "NATTA"
        ],
        "NIKKI": [
            "NIKKI 1"
        ],
        "N’DAHONTA": [
            "N'DAHONTA"
        ]
    },
    "village": {
        "BANIKANNI-DOUWÉROU": [
            "BANIKANI-DOUWÉROU"
        ],
        "GOUNIN DE PARAKOU1": [
            "GOUNIN"
        ],
        "MADINA DE PRKOU1": [
            "MADINA"
        ],
        "WOROU-TOKOROU": [
            "TOUROU-SOUROU"
        ],
        "BOHOMDO": [
            "BOHOMBO"
        ],
        "FRIGNIOU": [
            "FRIGNON"
        ],
        "BANAGBASSON": [
            "BANAGBANSSON"
        ],
        "GBÈKONA": [
            "GBÉKONA"
        ],
        "GOROGAWO": [
            "GOROGAO"
        ],
        "TOURA": [
            "TOURAH"
        ],
        "ADA-KPANÉ": [
            "ADA KPANÉ"
        ],
        "BESSASSI-BOUCA": [
            "BESSASSI BOUCA"
        ],
        "BOUCA-GANDO": [
            "BOUCA GANDO"
        ],
        "BOUCA-PEULH": [
            "BOUCA PEULH"
        ],
        "BOUCA-WOOROU": [
            "BOUCA WOOROU"
        ],
        "GBÉROUGBASSI": [
            "GBÉROU GBASSI"
        ],
        "GNEL-BOUCATOU": [
            "GNEL BOUCATOU"
        ],
        "KARÈL": [
            "KAREL"
        ],
        "ZONGO DE BOUKOUMBE": [
            "ZONGO DE BOUKOMBÉ"
        ],
        "ALAFIAROU-DÉRASSI": [
            "ALAFIAROU II"
        ],
        "GANNOURÈ-HÈRÈ": [
            "GANNOURÈHÈRÈ"
        ],
        "GNEL-KÉLÉ": [
            "GNEL-KÈLÈ"
        ],
        "GUIRI-PEULH": [
            "GUIRI PEULH"
        ],
        "MAREGUINTA": [
            "MARÉGUINTA"
        ],
        "BAPARAPÉÏ": [
            "BAPARAPEI"
        ],
        "DÉNDOUGOU": [
            "DENDOUGOU"
        ],
        "SEHVESSI": [
            "SERVESSI"
        ],
        "ALAFIAROU-GANDO": [
            "ALAFIAROU GANDO"
        ],
        "DJÈGA-DUNKASSA": [
            "DJÈGA DUNKASSA"
        ],
        "GBÉSSAKPÉROU": [
            "GBESSAKPÉROU"
        ],
        "KIRICOUBÈ": [
            "KRICOUBÉ"
        ],
        "FOUNOUGO-GAH": [
            "FOUNOUGO PEULH",
            "FOUNOUGO SINAKPAROU"
        ],
        "FOUNOUGO-YOMON": [
            "FOUNOUGO YOROUNON"
        ],
        "GAMÉRÉ-ZONGO": [
            "GAMARÈ ZONGO"
        ],
        "YINYINPOGOU": [
            "GNINGNINPOGOU"
        ],
        "GOUGNIROU": [
            "GOUGNIROU BARIBA",
            "GOUGNIROU PEULH"
        ],
        "KANDÉROU-KOTCHERA": [
            "KANDÉROU-KOTCHÉRA"
        ],
        "KPAKO-GBABI": [
            "KPAKO GBABI"
        ],
        "YANGUÉRI": [
            "YANGUERI"
        ],
        "BOROYINDÉ": [
            "BORIYINDÉ"
        ],
        "BÈRÈKÈ-GANDO": [
            "BÈRÈKÈ GANDO"
        ],
        "GAMIA-EST": [
            "GAMIA EST"
        ],
        "GAMIA-OUEST": [
            "GAMIA OUEST"
        ],
        "GUESSOU-NORD": [
            "GUESSOU NORD"
        ],
        "BOUAY DE GAMIA": [
            "BOUAY"
        ],
        "GNÉMASSON-GANDO": [
            "GNÉMASSON GANDO"
        ],
        "SAYAKROU – GAH": [
            "SAYAKROU-GAH"
        ],
        "DIGUIDIROU -PEULH": [
            "DIGUIDIROU-PEULH"
        ],
        "KOUKOUMBOU": [
            "KOUNKOUMBOU"
        ],
        "GNONKOURAKALI": [
            "GNONKOUROKALI"
        ],
        "GUEMA": [
            "GUINMA"
        ],
        "GUINROU-PEULH": [
            "GUINROU PEULH"
        ],
        "SOUBO-BARAWOROU": [
            "SOUBO BARAWOROU"
        ],
        "SOUBO-GANDÉROU": [
            "SOUBO GANDEROU"
        ],
        "KANDEGUEHOUN": [
            "KANDÉGUÉHOUN"
        ],
        "KOUANTIÉNI": [
            "KOUANTIENI"
        ],
        "TASSAHOUN": [
            "TANSAHOUN"
        ],
        "KANTORO": [
            "KANTRO"
        ],
        "LAKALI-KANEY": [
            "LAKALY-KANEY",
            "PORTÉ PAR L’ADV DE LAKALY-KANEY"
        ],
        "TORO-ZOUGOU": [
            "TOROZOUGOU"
        ],
        "BOUGNANKOU": [
            "BOUGNAKOU"
        ],
        "GANDO-ALAFIAROU": [
            "GANDO ALAFIAROU"
        ],
        "GOUNKPARÉ": [
            "GOUNKPARÈ"
        ],
        "GUINAGOUROU": [
            "GUINAGOUROU CENTRE"
        ],
        "GUINAGOUROU-PEULH": [
            "GUINAGOUROU PEULH"
        ],
        "DJEGA-KALALÉ": [
            "DJÈGA-KALALÉ"
        ],
        "KALALÉ": [
            "KALALE"
        ],
        "KALALÉ-SESSOUAN": [
            "KALALÉ SESSOUAN"
        ],
        "NASSICONZI": [
            "NASSINCONZI"
        ],
        "KARIMAMA-DENDI-KOURÉ": [
            "DENDI-KOURÉ"
        ],
        "GOUROU BÉRI": [
            "GOROUBÉRI"
        ],
        "KAOBAGOU": [
            "KOABAGOU"
        ],
        "GNAMPOLI": [
            "YAMPOLI"
        ],
        "ADJÊDÈ": [
            "ADJÈDÈ"
        ],
        "AGBONTÊ": [
            "AGBONTÉ"
        ],
        "KÊYORDAKÊ": [
            "KAYODARKÈ"
        ],
        "BECKET-PEULH": [
            "BECKET-DJADJI"
        ],
        "MARO DE KOUANDE": [
            "MARO"
        ],
        "SÉKOGOUROU-BAÏLA": [
            "SÉKOGOUROU-BAILA"
        ],
        "ZONGO DE KOUANDE": [
            "ZONGO"
        ],
        "GOROUSSOUNDOUGOU": [
            "GOROU-SOUNDOUGOU"
        ],
        "ILLOUA": [
            "ILOUA"
        ],
        "KOUALÉROU": [
            "KOALÉROU"
        ],
        "KOTCHI": [
            "PORTÉ PAR KOTCHI"
        ],
        "TASSI-TÉDJI-BANIZOUNBOU": [
            "TASSITÉDJI-BANIZOUMBOU"
        ],
        "WOURO-YESSO": [
            "WOURO-YÉSSO"
        ],
        "DIPOKORFONTRI": [
            "DIPOKOR FONTRI"
        ],
        "KOUTCHA-KOUMAGOU": [
            "KOUTCHAMAGOU"
        ],
        "BOUKANÈRÈ": [
            "BOUCANÈRÈ"
        ],
        "DONKPARAWI": [
            "DONKPLAWI"
        ],
        "GAH- MARO-PEULH": [
            "GAH MARO PEULH"
        ],
        "GUIDANDOLÉ": [
            "GUIDA N’DOLÈ",
            "Guida N'Dolè",
            "GUIDA N'DOLÈ"
        ],
        "KPARISSÉROU": [
            "KPARISSEROU"
        ],
        "GOUROU DE NIKKI": [
            "GOUROU"
        ],
        "TÉPA": [
            "TEPA"
        ],
        "TONTAROU-PEULH": [
            "TONTAROU PEULH"
        ],
        "NIGNÈRI": [
            "NIGNÉRI"
        ],
        "SAMMONGOU": [
            "SAMONGOU"
        ],
        "BOROUKOU-PEULH": [
            "BOROKOU-PEULH"
        ],
        "KÈTÉRÉ": [
            "KÉTÉRÉ"
        ],
        "KPÉSSOUROU": [
            "PESSOUROU"
        ],
        "YINKÈNÈ": [
            "YINKININ"
        ],
        "WÉKÉTÈRÈ": [
            "WEKETERE"
        ],
        "GNELKIRADJÉ": [
            "GNELKIRADJE",
            "Gnelkiradje"
        ],
        "OUÉNOU": [
            "OUENOU"
        ],
        "TCHICANDOU": [
            "TCHIKANDOU"
        ],
        "BANHOUN-KPO": [
            "BANHOUNKPO"
        ],
        "POURAMPARÈ": [
            "POURAPARE"
        ],
        "ABINTAGA": [
            "ABITANGA"
        ],
        "MONMONGOU": [
            "MOMONGOU"
        ],
        "NANOGOU": [
            "NANOUGOU"
        ],
        "GANDO-BAKA": [
            "GANDO BAKA"
        ],
        "GBÉÏ": [
            "GBÉI"
        ],
        "GNEL-YAKAN": [
            "GNEL - YAKAN"
        ],
        "GBESSARÈ": [
            "GBÈSSARÈ"
        ],
        "SAMTIMBARA": [
            "SATIMBARA"
        ],
        "SÈKÈRÈ-GANDO": [
            "SÈKÈRÈ GANDO"
        ],
        "SÈKÈRÈ-MARO": [
            "SÈKÈRÈ MARO"
        ],
        "YARRA-KOURI": [
            "YARRA KOURI"
        ],
        "YARRA-PEULH": [
            "YARRA PEULH"
        ],
        "GBÉNIKI DE SOROKO": [
            "GBÉNIKI"
        ],
        "ZANNIOURI": [
            "ZANNOUIRI"
        ],
        "DÉMAN": [
            "DÉEMAN"
        ],
        "GAN -GBÉROU": [
            "GAH-GBÉROU"
        ],
        "GBABIRÉ": [
            "GBAGBIRÉ"
        ],
        "KONTOUBAROU": [
            "KOUTOUBARAROU"
        ],
        "SOUMON-GAH": [
            "SOUMON GAH"
        ],
        "TCHATCHOU": [
            "TCHATCHOU\n CENTRE",
            "Tchatchou\n centre"
        ],
        "KOUKOUATCHIENGOU": [
            "Koukouatchien-maagou",
            "KOUKOUATCHIEN-MAAGOU"
        ],
        "KOUTIÉ TCHATIDO": [
            "Koutié-Tchatido",
            "KOUTIÉ-TCHATIDO"
        ],
        "MOUPÉMOU": [
            "MOUPEMOU"
        ],
        "WIMMOU": [
            "WINMOU"
        ],
        "TÉCTIBAYAOU": [
            "TECTIBAYAOU"
        ],
        "TOUKOUNTOUNA": [
            "TOUCOUNTOUNA"
        ],
        "KALÉ": [
            "KALE"
        ],
        "WARA": [
            "07 ADV DE WARA (DASSARI, DOUGOU, KALÉ, SOUKAROU, WARA, WARA-GAH ET WARA-GBIGOGO) PORTÉ PAR WARA"
        ],
        "N’ TCHIÉGA": [
            "N' Tchiéga",
            "N'TCHIÉGA",
            "N' TCHIÉGA"
        ],
        "N’DAM": [
            "N'Dam",
            "N'DAM"
        ],
        "N’DJAKADA": [
            "N'Djakada",
            "N'DJAKADA"
        ],
        "KOUWA N'PONGOU": [
            "Kouanpogou",
            "KOUANPOGOU"
        ],
        "BESSASSI-BÉA": [
            "Béssassi-Béa",
            "BESSASSI-BEA"
        ],
        "GOURÉ-GBATA": [
            "Gourè-Gbata",
            "GOURE-GBATA"
        ],
        "BOFOUNOU": [
            "Bofounou-Peulh",
            "BOFOUNOU-PEULH"
        ],
        "DOGA DE GOUANDE": [
            "Doga",
            "DOGA"
        ],
        "KOUCONGOU": [
            "Koucointiégou",
            "KOUCOINTIÉGOU"
        ],
        "KOUSSAYAGOU": [
            "Koussagou",
            "KOUSSAGOU"
        ],
        "NIÈKÈNÈ-BANSOU": [
            "Niekebanssou",
            "NIEKEBANSSOU"
        ],
        "MAKROU-GOUROU": [
            "Makrou",
            "MAKROU"
        ],
        "OUROUMON": [
            "OUROUMON"
        ],
        "OUROUMONSI- PEULH": [
            "OUROUMONSI"
        ]
    }
}

CONTEXTUAL_ALIASES = [
    {
        "alias": "OUÉNOU",
        "db_name": "OUENOU",
        "db_type": "arrondissement",
        "parent_name": "NIKKI",
        "parent_type": "commune",
        "note": "arrondissement OUENOU under commune NIKKI"
    },
    {
        "alias": "OUÉNOU",
        "db_name": "OUENOU",
        "db_type": "arrondissement",
        "parent_name": "N’DALI",
        "parent_type": "commune",
        "note": "arrondissement OUENOU under commune N'DALI"
    },
    {
        "alias": "GOROBANI",
        "db_name": "GOROBANI DE DOUKASSA",
        "db_type": "village",
        "parent_name": "DUNKASSA",
        "parent_type": "arrondissement",
        "note": "village under DUNKASSA"
    },
    {
        "alias": "GOROBANI",
        "db_name": "GOROBANI DE GNINSY",
        "db_type": "village",
        "parent_name": "GNINSY",
        "parent_type": "arrondissement",
        "note": "village under GNINSY"
    },
    {
        "alias": "WONKO",
        "db_name": "WONKO DERASSI",
        "db_type": "village",
        "parent_name": "DERASSI",
        "parent_type": "arrondissement",
        "note": "village under DERASSI"
    },
    {
        "alias": "WONKO",
        "db_name": "WONKO DE NIKKI",
        "db_type": "village",
        "parent_name": "NIKKI",
        "parent_type": "arrondissement",
        "note": "village under arrondissement NIKKI"
    },
    {
        "alias": "KOARATÉDJI",
        "db_name": "KOARATÉDJI",
        "db_type": "village",
        "parent_name": "BOGO-BOGO",
        "parent_type": "arrondissement",
        "note": "village under BOGO-BOGO"
    },
    {
        "alias": "KOARATÉDJI",
        "db_name": "KOARA-TÉDJI",
        "db_type": "village",
        "parent_name": "GUENE",
        "parent_type": "arrondissement",
        "note": "village under GUENE"
    },
    {
        "alias": "KOARATÉDJI",
        "db_name": "GODJÉKOARA",
        "db_type": "village",
        "parent_name": "MADECALI",
        "parent_type": "arrondissement",
        "note": "village under MADECALI"
    },
    {
        "alias": "ALAFIAROU",
        "db_name": "ALAFIAROU DE OUENOU",
        "db_type": "village",
        "parent_name": "OUENOU",
        "parent_type": "arrondissement",
        "grandparent_name": "N\u2019DALI",
        "grandparent_type": "commune",
        "note": "ALAFIAROU DE OUENOU — arrondissement OUENOU under commune N'DALI"
    },
    {
        "alias": "Kpawolou",
        "db_name": "KPAWOLOU DE NIKKI",
        "db_type": "village",
        "parent_name": "NIKKI",
        "parent_type": "arrondissement",
        "note": "KPAWOLOU under arrondissement NIKKI"
    },
    {
        "alias": "KPAWOLOU",
        "db_name": "KPAWOLOU DE NIKKI",
        "db_type": "village",
        "parent_name": "NIKKI",
        "parent_type": "arrondissement",
        "note": "KPAWOLOU under arrondissement NIKKI"
    },
    {
        "alias": "Kpawolou",
        "db_name": "KPAWOLOU",
        "db_type": "village",
        "parent_name": "GUINAGOUROU",
        "parent_type": "arrondissement",
        "note": "KPAWOLOU under GUINAGOUROU"
    },
    {
        "alias": "WEKETERE",
        "db_name": "WÉKÉTÈRÈ",
        "db_type": "village",
        "parent_name": "OUENOU",
        "parent_type": "arrondissement",
        "grandparent_name": "N\u2019DALI",
        "grandparent_type": "commune",
        "note": "WÉKÉTÈRÈ — arrondissement OUENOU under commune N'DALI"
    }
]


def populate_aliases(apps, schema_editor):
    AdministrativeLevel = apps.get_model("administrativelevels", "AdministrativeLevel")
    AdministrativeLevelAlias = apps.get_model("administrativelevels", "AdministrativeLevelAlias")

    created = 0
    skipped = 0
    errors = []

    # --- Simple aliases ---
    for adm_type, entries in SIMPLE_ALIASES.items():
        for db_name, alias_list in entries.items():
            qs = AdministrativeLevel.objects.filter(
                name__iexact=db_name,
                type__iexact=adm_type,
            )
            if not qs.exists():
                errors.append(f"NOT FOUND [{adm_type}] '{db_name}'")
                continue
            if qs.count() > 1:
                errors.append(
                    f"AMBIGUOUS [{adm_type}] '{db_name}' ({qs.count()} results)"
                    " — add to CONTEXTUAL_ALIASES"
                )
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

    # --- Contextual aliases (resolved by parent to disambiguate) ---
    for entry in CONTEXTUAL_ALIASES:
        parent_qs = AdministrativeLevel.objects.filter(
            name__iexact=entry["parent_name"],
            type__iexact=entry["parent_type"],
        )
        # If a grandparent is specified, use it to narrow down the parent lookup
        if "grandparent_name" in entry:
            grandparent_qs = AdministrativeLevel.objects.filter(
                name__iexact=entry["grandparent_name"],
                type__iexact=entry["grandparent_type"],
            )
            if not grandparent_qs.exists():
                errors.append(
                    f"CONTEXTUAL grandparent NOT FOUND [{entry['grandparent_type']}] '{entry['grandparent_name']}'"
                )
                continue
            parent_qs = parent_qs.filter(parent=grandparent_qs.first())
        if not parent_qs.exists():
            errors.append(
                f"CONTEXTUAL parent NOT FOUND [{entry['parent_type']}] '{entry['parent_name']}'"
            )
            continue
        if parent_qs.count() > 1:
            errors.append(
                f"CONTEXTUAL parent AMBIGUOUS [{entry['parent_type']}] '{entry['parent_name']}'"
                f" ({parent_qs.count()} results) — note: {entry.get('note', '')}"
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
                f"CONTEXTUAL NOT FOUND '{entry['db_name']}' "
                f"under '{entry['parent_name']}' — note: {entry.get('note', '')}"
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
        f"\n[populate_adm_level_aliases] "
        f"created={created}, skipped={skipped}, errors={len(errors)}"
    )
    for e in errors:
        print(f"  ⚠️  {e}")


def depopulate_aliases(apps, schema_editor):
    AdministrativeLevelAlias = apps.get_model("administrativelevels", "AdministrativeLevelAlias")
    AdministrativeLevelAlias.objects.filter(source=SOURCE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("administrativelevels", "0029_administrativelevelalias"),
    ]

    operations = [
        migrations.RunPython(populate_aliases, reverse_code=depopulate_aliases),
    ]