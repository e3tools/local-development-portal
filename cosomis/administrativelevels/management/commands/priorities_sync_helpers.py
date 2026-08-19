"""
Fonctions et tables de correspondance partagées par 2_syncpriorities.py pour
transformer les sous-composantes 1.1/1.2a/1.2b/1.3 (COSO, FA-COSO) et
Composante1/2/3 (PURS) en Investment/GroupInvestment.

Les dictionnaires "*_TO_CATEGORY" ci-dessous sont des propositions de catégorie :
ils ne servent qu'à créer un Sector qui n'existe pas encore (le nom du secteur
recherché en base reste prioritaire — voir resolve_sector()). Ils peuvent être
librement réajustés.
"""
import re
import unicodedata
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone as dj_timezone
from fuzzywuzzy import fuzz
from django.db.models import Q

from administrativelevels.models import AdministrativeLevel, Category, Sector, Component, GroupeSocioeconomique
from administrativelevels.utils.functions import normalize_text
from investments.models import Investment, GroupInvestment
from administrativelevels.libraries.functions import safe_parse_date


_component_cache = {}


def get_or_create_component(project, name, parent=None):
    if not project:
        return None
    cache_key = (project.id, name, parent.id if parent else None)
    if cache_key in _component_cache:
        return _component_cache[cache_key]
    component, _ = Component.objects.get_or_create(project=project, name=name, parent=parent, defaults={'short_name': name.split(' ')[-1] if name else None})
    _component_cache[cache_key] = component
    return component


# ---------------------------------------------------------------------------
# Normalisation de texte libre (noms de marché/village, libellés d'équipement)
# ---------------------------------------------------------------------------

def strip_accents(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(text)) if not unicodedata.combining(c))


def normalize_loose(text):
    """Majuscules, sans accents, séparateurs (espaces/tirets/apostrophes) réduits
    à un seul espace. Utilisé comme base pour les comparaisons exactes et fuzzy."""
    if not text:
        return ""
    text = strip_accents(text).upper()
    text = re.sub(r"[-_'’]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compact(text):
    """Comme normalize_loose(), sans aucun espace — absorbe les variantes du
    type "naki ouest" / "naki-ouest" / "nakiouest"."""
    return normalize_loose(text).replace(" ", "")


MARKET_NAME_NOISE_PREFIXES = ["MARCHE DE ", "LE MARCHE DE ", "AU ", "A ", "À "]
MARKET_NAME_NOISE_SUFFIX = " CENTRE"


def extract_place_candidate(raw_text, strip_suffix_centre=False):
    """Retire les mots de liaison usuels d'un texte de type "Marché de Dapaong"
    ou "A naki-ouest centre" pour ne garder que le nom de lieu probable."""
    candidate = normalize_loose(raw_text)
    for prefix in MARKET_NAME_NOISE_PREFIXES:
        if candidate.startswith(prefix):
            candidate = candidate[len(prefix):]
            break
    if strip_suffix_centre and candidate.endswith(MARKET_NAME_NOISE_SUFFIX):
        candidate = candidate[: -len(MARKET_NAME_NOISE_SUFFIX)]
    return candidate.strip()


# ---------------------------------------------------------------------------
# Résolution floue d'un nom de lieu contre les AdministrativeLevel existants
# ---------------------------------------------------------------------------

class AdministrativeLevelIndex:
    """Index (léger cache) des noms de cantons/villages, reconstruit une fois
    par exécution de la commande plutôt qu'à chaque document traité."""

    def __init__(self):
        self._by_type = {}

    def _entries(self, adm_type):
        if adm_type not in self._by_type:
            qs = AdministrativeLevel.objects.filter(AdministrativeLevel.type_filter_q(adm_type)).only('id', 'name')
            self._by_type[adm_type] = [(compact(adm.name), adm) for adm in qs]
        return self._by_type[adm_type]

    def find(self, candidate, adm_type, threshold=90):
        if not candidate:
            return None
        compact_candidate = compact(candidate)
        if not compact_candidate:
            return None
        best, best_score = None, 0
        for compact_name, adm in self._entries(adm_type):
            if compact_name == compact_candidate:
                return adm
            score = fuzz.ratio(compact_name, compact_candidate)
            if score > best_score:
                best_score, best = score, adm
        return best if best_score >= threshold else None


GROUP_INVESTMENT_TITLE_MATCH_THRESHOLD = 90
GROUP_INVESTMENT_ITEM_MATCH_THRESHOLD = 85


def find_or_create_group_investment(index, nom_marche, lieu_marche, declaring_administrative_level, component, project):
    """Marché cantonal (1.2a) : réutilise un GroupInvestment existant du même
    projet dont le titre correspond (exact puis flou, sur formes compactées)
    avant d'en créer un nouveau — c'est ce qui absorbe les variantes de saisie
    comme "naki ouest centre" / "naki-ouest centre" / "naki-uest centre"."""
    title = (nom_marche or "").strip()
    if not title:
        return None
    compact_title = normalize_text(compact(title))

    candidates = list(GroupInvestment.objects.filter(component__project=project))
    for gi in candidates:
        if normalize_text(compact(gi.title)) == compact_title:
            return gi

    best, best_score = None, 0
    for gi in candidates:
        score = fuzz.ratio(normalize_text(compact(gi.title)), compact_title)
        if score > best_score:
            best_score, best = score, gi
    if best and best_score >= GROUP_INVESTMENT_TITLE_MATCH_THRESHOLD:
        return best

    canton, lieu = resolve_group_investment_location(index, nom_marche, lieu_marche, declaring_administrative_level)

    if component and str(component.short_name).lower() == '1.2a':
        if canton:
            gi = GroupInvestment.objects.filter(component__project=project, administrative_level=canton).first()
            if gi:
                return gi
        if lieu:
            gi = GroupInvestment.objects.filter(component__project=project, administrative_level=lieu.parent).first()
            if gi:
                return gi

    return GroupInvestment.objects.create(title=title, administrative_level=canton, lieu=lieu, component=component)


def find_or_create_group_investment_item(group_investment, type_de_developpement, ranking, component,
                                          fallback_administrative_level, category_name="Marché et commerce"):
    """Équipement demandé pour un marché (1.2a) : réutilise un Investment déjà
    créé pour ce même GroupInvestment si son libellé est le même (ou très
    proche), pour qu'un même équipement cité par deux villages ne soit pas
    dupliqué dans le canton."""
    label = (type_de_developpement or "").strip()
    if not label:
        return None
    compact_label = compact(label)

    siblings = list(group_investment.investments.filter(
        Q(came_from__id=component.project.id) | 
        Q(~Q(came_from__id=component.project.id) & Q(project_status=Investment.NOT_FUNDED))
    ).all().distinct())

    for inv in siblings:
        if compact(inv.title) == compact_label:
            return inv

    best, best_score = None, 0
    for inv in siblings:
        score = fuzz.ratio(compact(inv.title), compact_label)
        if score > best_score:
            best_score, best = score, inv
    if best and best_score >= GROUP_INVESTMENT_ITEM_MATCH_THRESHOLD:
        return best

    return Investment.objects.create(
        title=label,
        administrative_level=group_investment.administrative_level or fallback_administrative_level,
        sector=resolve_sector(label, category_name),
        ranking=ranking,
        component=component,
        group_investment=group_investment,
        investment_status=Investment.PRIORITY,
        delays_consumed=0, duration=0,
        financial_implementation_rate=0, physical_execution_rate=0,
        no_sql_id='',
    )


def resolve_group_investment_location(index, nom_marche, lieu_marche, declaring_administrative_level):
    """Cascade de résolution du canton/lieu d'un marché cantonal (sous-composante 1.2a) :
    1) nom du marché -> canton, ou nom du marché -> village -> son canton
    2) sinon, canton du village déclarant
    3) sinon, lieu du marché -> village -> son canton, ou lieu du marché -> canton
    4) sinon, None
    Le "lieu" (village) est, lui, toujours tenté depuis lieuDuMarcheLePlusImportant.
    """
    nom_candidate = extract_place_candidate(nom_marche, strip_suffix_centre=True)
    canton = index.find(nom_candidate, AdministrativeLevel.CANTON)
    if not canton:
        nom_village = index.find(nom_candidate, AdministrativeLevel.VILLAGE)
        if nom_village:
            canton = nom_village.parent

    lieu_candidate = extract_place_candidate(lieu_marche, strip_suffix_centre=False)
    lieu_village = index.find(lieu_candidate, AdministrativeLevel.VILLAGE)

    if not canton and declaring_administrative_level:
        canton = (
            declaring_administrative_level.parent
            if declaring_administrative_level.is_village()
            else declaring_administrative_level
        )

    if not canton and lieu_village:
        canton = lieu_village.parent

    if not canton:
        canton = index.find(lieu_candidate, AdministrativeLevel.CANTON)

    return canton, lieu_village


# ---------------------------------------------------------------------------
# Secteurs : priorite (enum fermé) -> Sector
# ---------------------------------------------------------------------------

_sector_cache = {}


def resolve_sector(value, category_name="Autre"):
    """Recherche d'abord un Sector du même nom (comme le fait déjà le script
    actuel pour la 1.1, où ces Sector existent en base) ; n'en crée un nouveau
    (avec sa Category si besoin) que si aucun n'existe encore."""
    if not value:
        value = "Autre"
    cache_key = value
    if cache_key in _sector_cache:
        return _sector_cache[cache_key]
    sector = Sector.objects.filter(name=value).order_by('id').first()
    if not sector:
        category, _ = Category.objects.get_or_create(name=category_name)
        sector = Sector.objects.create(name=value, category=category)
    _sector_cache[cache_key] = sector
    return sector


# 1.1 (COSO/FA-COSO) — les 25 valeurs sont déjà exploitées telles quelles par le
# script actuel (Sector.objects.get(name=title) fonctionne) : ces Sector existent
# donc déjà en base, la catégorie indiquée ici ne sert qu'en filet de sécurité.
PRIORITE_11_TO_CATEGORY = {
    'Construction magasin de stockage': 'Agriculture', 

    'Réhabilitation magasin de stockage': 'Assainissement', 

    'Autre': 'Autre', 

    'Réalisation Forage photovoltaïque Agri': 'Developpement–a–la–Base', 
    'Construction Centre communautaire': 'Developpement–a–la–Base', 
    'Construction Maison des jeunes': 'Developpement–a–la–Base', 

    'Construction Latrine communautaire': 'Eau', 
    'Réalisation Forage photovoltaïque AEP': 'Eau', 

    'Réhabilitation Bâtiment scolaire EPP': 'Education', 
    'Réhabilitation Bâtiment scolaire CEG': 'Education', 
    'Réhabilitation Bâtiment scolaire Lycée': 'Education', 
    'Construction Bâtiment scolaire EPP': 'Education', 
    'Construction Bâtiment scolaire CEG': 'Education', 
    'Construction Bâtiment scolaire Lycée': 'Education', 

    'Extention réseau électrique': 'Energie', 
    'Electrification avec Panneaux solaires': 'Energie', 

    'Construction Ponts': 'Pistes', 
    'Construction Radier': 'Pistes', 
    'Construction Ponceaux': 'Pistes', 
    'Amenagement Piste': 'Pistes', 

    'Réhabilitation CMS': 'Sante', 
    'Réhabilitation CHP': 'Sante', 
    'Construction CMS': 'Sante', 
    'Construction USP': 'Sante', 
    'Réhabilitation USP': 'Sante'
}

# 1.3 (COSO/FA-COSO) — vocabulaire jamais traité jusqu'ici, ces Sector sont donc
# probablement à créer.
PRIORITE_13_TO_CATEGORY = {
    "Réhabilitation/équipement terrain foot": "Sport",
    "Aménagement/équipement terrain de foot": "Sport",
    "Appui groupements maraichers": "Appui Economique",
    "Appui groupements éleveurs": "Appui Economique",
    "Appui groupements producteurs de Maïs": "Appui Economique",
    "Appui groupements producteurs de Riz": "Appui Economique",
    "Appui aux jeunes producteurs de Soja": "Appui Economique",
    "Appui groupements transformateurs": "Appui Economique",
    "Appui groupements artisans": "Appui Economique",
    "Appui commerçants produits Agricoles/élevages": "Appui Economique",
    "Appui Commerçants produits transformés": "Appui Economique",
    "Appui Commerçant produit artisanaux": "Appui Economique",
    "Autre": "Autre",
}

# PURS — Composante 1 (infrastructures sociales de base)
PRIORITE_PURS_C1_TO_CATEGORY = {
    "Renforcement et financement des coopératives de femmes et de jeunes": "Appui Economique",
    "Equipement des jeunes en kits d'outillage": "Appui Economique",

    "Construction Latrine communautaire": "Assainissement",

    "Construction de marché y compris les blocs latrines": "Commerce",

    "Réalisation Forage photovoltaïque AEP": "Eau",
    "Equipement de forage": "Eau",
    "Travaux d'adduction et de distribution d'eau": "Eau",
    "Travaux de renouvellement et d'extension": "Eau",
    "Fourniture et pose de canalisation": "Eau",

    "Construction Bâtiment scolaire EPP": "Education",
    "Construction Bâtiment scolaire CEG": "Education",
    "Construction Bâtiment scolaire Lycée": "Education",
    "Réhabilitation Bâtiment scolaire EPP": "Education",
    "Réhabilitation Bâtiment scolaire CEG": "Education",
    "Réhabilitation Bâtiment scolaire Lycée": "Education",
    "Acquisition de photocopieurs pour écoles": "Education",
    "Acquisition d'ordinateur": "Education",
    "Formation des enseignants": "Education",
    "Fournitures des repas chauds dans les écoles": "Education",
    "Fournitures des repas chauds aux élèves": "Education",
    
    "Construction Maison des jeunes": "Developpement–a–la–Base",
    "Construction Centre communautaire": "Developpement–a–la–Base",
    
    "Electrification avec Panneaux solaires": "Energie",
    "Extension réseau électrique": "Energie",

    "Aménagement Piste": "Pistes",
    "Construction Radier": "Pistes",
    "Construction Ponceaux": "Pistes",
    "Construction Ponts": "Pistes",
    "Construction de dalots multiple": "Pistes",
    "Réhabilitation des plateformes": "Pistes",

    "Construction USP": "Sante",
    "Construction CMS": "Sante",
    "Réhabilitation USP": "Sante",
    "Réhabilitation CMS": "Sante",
    "Réhabilitation CHP": "Sante",
    "Equipement USP": "Sante",
    "Equipement CMS": "Sante",


    "Contrôle et surveillance des travaux": "Autre",
    "Réalisation d'étude technique détaillé": "Autre",
    "Transfère monétaire": "Autre",
    "Extension de la couverture des services voix et internet": "Autre",
    "Autre": "Autre",
}

# PURS — Composante 2 (développement économique)
PRIORITE_PURS_C2_TO_CATEGORY = {
    "Appui groupements maraichers": "Appui Economique",
    "Appui groupements éleveurs": "Appui Economique",
    "Appui groupements producteurs de Maïs": "Appui Economique",
    "Appui groupements producteurs de Riz": "Appui Economique",
    "Appui aux jeunes producteurs de Soja": "Appui Economique",
    "Appui groupements transformateurs": "Appui Economique",
    "Appui groupements artisans": "Appui Economique",
    "Appui commerçants de produits Agricoles/élevages": "Appui Economique",
    "Appui Commerçants de produits transformés": "Appui Economique",
    "Appui Commerçant produit artisanaux": "Appui Economique",
    "Appui aux semences certifiées": "Appui Economique",
    "Appui aux fertilisants et biopesticides": "Appui Economique",
    "Appui aux équipements d'élevage": "Appui Economique",
    "Appui matériel et technique": "Appui Economique",
    
    "Construction d'infrastructures de marché": "Commerce",

    "Réalisation Forage photovoltaïque Agri": "Eau",

    "Construction magasin de stockage": "Agriculture",
    "Aménagement de ZAAP": "Agriculture",
    "Réhabilitation magasin de stockage": "Agriculture",
    "Construction de zones de stockage": "Agriculture",
    "Installation de systèmes d'irrigation": "Agriculture",
    "Aménagement des bas-fonds": "Agriculture",
    "Réhabiliter des barrages et retenu d'eau": "Agriculture",
    "Mise en place de parcs agroforestiers": "Agriculture",
    "Formation en techniques agricoles modernes": "Agriculture",

    "Aménagement des routes pour faciliter l'accès au marché": "Route",

    "Renforcer les capacités des éleveurs": "Renforcement",

    "Réhabilitation/équipement terrain foot": "Sport",
    "Aménagement/équipement terrain de foot": "Sport",

    "Appui à la sensibilisation": "Autre",
    "Autre": "Autre",
}

# PURS — Composante 3 (sécurité / gouvernance)
PRIORITE_PURS_C3_TO_CATEGORY = {
    "Reconnaissance de chef traditionnel": "Gouvernance",
    "Sensibilisation sur la cohésion sociale": "Gouvernance",
    "Formation des magistrats": "Gouvernance",

    "Mise en place d’une maison de justice": "Securite",
    "Construction des commissariats de Police": "Securite",
    "Construction des Brigades de Gendarmerie": "Securite",

    "Autre": "Autre",
}


def find_existing_flat_investment(administrative_level, component, title, description=None, disambiguate_by_description=False):
    """Retrouve un Investment déjà synchronisé pour 1.1/1.3/Composante1/2/3.
    Cherche d'abord avec le `component` résolu, puis (compatibilité) parmi les
    Investment synchronisés avant l'introduction de ce champ (component NULL),
    pour les adopter au lieu d'en recréer un doublon."""

    investments = Investment.objects.filter(
        Q(came_from__id=component.project.id) | 
        Q(~Q(came_from__id=component.project.id) & Q(project_status=Investment.NOT_FUNDED))
    ).distinct()

    filters = dict(administrative_level=administrative_level, title=title)
    if disambiguate_by_description:
        filters['description'] = description
    investment = investments.filter(component=component, **filters).first()
    if not investment:
        investment = investments.filter(component__isnull=True, **filters).first()

    if not investment and disambiguate_by_description:
        del filters['description']
        investment = investments.filter(component=component, **filters).first()
        if not investment:
            investment = investments.filter(component__isnull=True, **filters).first()


    if not investment:
        label = (title or "").strip()
        if not label:
            return None
        compact_label = compact(label)
    
        siblings = list(investments.filter(administrative_level=administrative_level))
        for inv in siblings:
            if compact(inv.title) == compact_label:
                return inv
    
        best, best_score = None, 0
        for inv in siblings:
            score = fuzz.ratio(compact(inv.title), compact_label)
            if score > best_score:
                best_score, best = score, inv
        if best and best_score >= GROUP_INVESTMENT_ITEM_MATCH_THRESHOLD:
            return best
    
    return investment


CDD_TITLE_MATCH_THRESHOLD = 75


def find_cdd_imported_investment(administrative_level, sector, title):
    """Rattache une priorité nouvellement synchronisée à un Investment déjà
    importé de la CDD (imported_project_id renseigné) dont le titre est proche,
    pour éviter un doublon quand ce sous-projet existait déjà sous un intitulé
    légèrement différent. Restreint au même secteur résolu (en plus du même
    village) pour ne pas rapprocher deux investissements de nature différente
    juste parce que leurs titres se ressemblent."""
    candidates = Investment.objects.filter(
        administrative_level=administrative_level,
        sector=sector,
        imported_project_id__isnull=False,
    )
    normalized_title = normalize_text(compact(title))
    best, best_score = None, 0
    for candidate in candidates:
        score = fuzz.token_set_ratio(normalize_text(compact(candidate.title)), normalized_title)
        if score > best_score:
            best_score, best = score, candidate
    return best if best_score >= CDD_TITLE_MATCH_THRESHOLD else None


# ---------------------------------------------------------------------------
# Groupes ayant proposé une priorité (proposePar) -> endorsed_by_*
# ---------------------------------------------------------------------------

ENDORSEMENT_FIELDS = [
    "endorsed_by_youth", "endorsed_by_women", "endorsed_by_agriculturist",
    "endorsed_by_pastoralist", "endorsed_by_displaced",
]

# proposePar en chaîne simple (COSO 1.1/1.3, PURS Composante1/2/3) — un même
# libellé a le même sens quel que soit le formulaire d'origine.
PROPOSE_PAR_FLAT_TO_ENDORSEMENTS = {
    "Hommes": [],
    "Femmes": ["endorsed_by_women"],
    "Hommes et Femmes": ["endorsed_by_women"],
    "jeunes hommes": ["endorsed_by_youth"],
    "jeunes femmes": ["endorsed_by_youth", "endorsed_by_women"],
    "jeunes hommes et femmes": ["endorsed_by_youth", "endorsed_by_women"],
    "Groupe des minorités ethniques": ["endorsed_by_pastoralist"],
    "Groupe des leaders/chefferie": [],
    "Groupe des réfugiés et des déplacés internes": ["endorsed_by_displaced"],
    "Groupe des agriculteurs et éleveurs": ["endorsed_by_agriculturist"],
    "Groupe des jeunes": ["endorsed_by_youth"],
    "Groupe des femmes": ["endorsed_by_women"],
    "Autre": [],
}

# proposePar en objet (FA-COSO 1.1 uniquement) : {clé: "Oui"/"Non"}
PROPOSE_PAR_DICT_TO_ENDORSEMENT_FIELD = {
    "groupeDesJeunes": "endorsed_by_youth",
    "groupeDesFemmes": "endorsed_by_women",
    "groupeDesAgriculteursEtEleveurs": "endorsed_by_agriculturist",
    "groupeDesMinoritesEthniques": "endorsed_by_pastoralist",
    "groupeDesRefugiesEtDesDeplacesInternes": "endorsed_by_displaced",
}


def apply_endorsements(investment, propose_par, reset=True):
    """Applique les flags endorsed_by_* déduits de `propose_par` (chaîne ou objet).
    reset=True (1.1/1.3/PURS) : le document fait foi, les flags non concernés sont
    remis à False. reset=False (1.2a) : les flags ne font que s'ajouter, plusieurs
    villages pouvant contribuer les leurs au même Investment partagé."""
    flags = set()
    if isinstance(propose_par, dict):
        for key, field in PROPOSE_PAR_DICT_TO_ENDORSEMENT_FIELD.items():
            if str(propose_par.get(key, "")).strip().lower() == "oui":
                flags.add(field)
    elif isinstance(propose_par, str):
        flags.update(PROPOSE_PAR_FLAT_TO_ENDORSEMENTS.get(propose_par.strip(), []))

    for field in ENDORSEMENT_FIELDS:
        if field in flags:
            setattr(investment, field, True)
        elif reset:
            setattr(investment, field, False)


# ---------------------------------------------------------------------------
# Sous-composante 1.2b : rapprochement besoin (texte libre) <-> GroupeSocioeconomique
# ---------------------------------------------------------------------------

GROUPES_SOCIOECONOMIQUES_PREDEFINIS = [
    "anacarde", "artisans", "commerçants de produits agricoles/élevages",
    "commerçants de produits transformés", "commerçants de produits artisanaux",
    "éleveurs", "karité", "maïs", "maraîchers", "riz", "sesame", "soja",
    "transformation de produits agricoles (soja, riz, sesame, karité, anacarde)",
]


def ensure_predefined_groupes_socioeconomiques():
    for name in GROUPES_SOCIOECONOMIQUES_PREDEFINIS:
        GroupeSocioeconomique.objects.get_or_create(name=name)


def find_matching_groupes_socioeconomiques(besoin_text, village_group_names):
    """Ne cherche que parmi les groupes que CE village a lui-même déclarés
    (village_group_names), pour éviter les rapprochements hasardeux."""
    if not besoin_text or not village_group_names:
        return []
    text_norm = normalize_loose(besoin_text)
    matched = []
    for name in village_group_names:
        group, _ = GroupeSocioeconomique.objects.get_or_create(name=name)
        needles = [group.name] + list(group.keywords or [])
        if any(normalize_loose(needle) in text_norm for needle in needles if needle):
            matched.append(group)
    return matched


# ---------------------------------------------------------------------------
# last_sync : ignorer une mise à jour plus ancienne que ce qui est déjà appliqué
# ---------------------------------------------------------------------------

def _ensure_aware(value):
    """Coerce a naive datetime to aware UTC. Used as a safety net both when
    parsing a document's date and when reading back Investment.last_sync —
    a value written naive by any past/buggy code path must never crash a
    later comparison; it gets normalized (and, via mark_synced, healed in
    the DB) instead."""
    if value is not None and dj_timezone.is_naive(value):
        return dj_timezone.make_aware(value, timezone=dt_timezone.utc)
    return value


def parse_document_date(document):
    """Parse last_updated_moment (ISO 8601, ex. "2025-10-15T10:21:00.716Z") ou,
    à défaut, last_updated (ex. "2025-10-15 10:21:2" / "2023-10-5 0:5:27" —
    composants non zéro-paddés, que fromisoformat() refuse). safe_parse_date()
    (dateutil, dayfirst=True — pour des formats vraiment différents type
    dd/mm/yyyy) n'est tenté qu'en tout dernier recours et toujours protégé :
    avec une chaîne de forme ISO mais mal paddée, dateutil peut mal
    interpréter les champs (voire lever une exception non-ValueError) — jamais
    laisser une erreur de parsing de date interrompre toute la synchro."""
    raw = document.get('last_updated_moment') or document.get('last_updated')
    if not raw:
        return None
    raw = str(raw).strip()

    try:
        return _ensure_aware(datetime.fromisoformat(raw.replace('Z', '+00:00')))
    except ValueError:
        pass

    match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})[ T](\d{1,2}):(\d{1,2}):(\d{1,2})", raw)
    if match:
        y, mo, d, h, mi, s = (int(g) for g in match.groups())
        try:
            return dj_timezone.make_aware(datetime(y, mo, d, h, mi, s), timezone=dt_timezone.utc)
        except ValueError:
            return None

    try:
        return _ensure_aware(safe_parse_date(raw))
    except Exception:
        return None


def should_skip_for_sync_date(investment, document_date, is_considerate_sync_date=True):
    if not is_considerate_sync_date:
        return False
    if document_date is None or not investment.pk or investment.last_sync is None:
        return False
    return document_date < _ensure_aware(investment.last_sync)


def mark_synced(investment, document_date):
    if not document_date:
        return
    last_sync = _ensure_aware(investment.last_sync)
    if last_sync is None or document_date > last_sync:
        investment.last_sync = document_date
