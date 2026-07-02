"""
Extract new subprojects from the complete dashboard file, deduplicate against
already-processed files, then match against DB investments using resolve_adm_level.

Run with: python manage.py shell < match_new_subprojects.py
Outputs:  new_matching_results.json  +  new_matching_results.xlsx
Place both output files alongside manage.py before running.
"""
import json, re, unicodedata
from collections import defaultdict

import pandas as pd

from administrativelevels.utils.resolvers import resolve_adm_level
from investments.models import Investment

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def nk(s):
    """Normalize string for robust comparison (no accents, lowercase, etc.)."""
    s = str(s or '').strip()
    if s.lower() in ('nan', 'none', ''):
        return ''
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^a-z0-9]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

# ---------------------------------------------------------------------------
# Step 1 — Build already-processed keys from en_cours + acheves files
# ---------------------------------------------------------------------------
FILES_ALREADY = {
    "en_cours": "BJ_GoG_COSO_Liste des sous-projets_en cours_16062026.xlsx",
    "acheves":  "BJ_GoG_COSO_Liste des sous-projets_achevés_15062026.xlsx",
}

already_keys = set()
for source, fname in FILES_ALREADY.items():
    xl = pd.ExcelFile(fname)
    df_src = xl.parse(xl.sheet_names[0])
    df_src = df_src.rename(columns={
        'Département': 'dept', 'Commmune': 'com',
        'Arrondissement': 'arr', 'Communauté': 'vil',
        'Sous-composante': 'sub',
        'Titre du sous-projet': 'titre',
        'Intitulé du sous projet': 'intitule',
    })
    for col in ['dept','com','arr','vil','sub','titre','intitule']:
        df_src[col] = df_src.get(col, pd.Series([''] * len(df_src))).fillna('').astype(str).str.strip()
    df_src = df_src[~df_src['dept'].str.lower().isin(['nan',''])]

    for _, row in df_src.iterrows():
        base = (nk(row['dept']), nk(row['com']), nk(row['arr']),
                nk(row['vil']), nk(row['sub']))
        if nk(row.get('titre','')):
            already_keys.add(base + (nk(row['titre']),))
        if nk(row.get('intitule','')):
            already_keys.add(base + (nk(row['intitule']),))

print(f"Already-processed keys: {len(already_keys)}")

# ---------------------------------------------------------------------------
# Step 2 — Load complete file and extract new rows (not already processed)
# ---------------------------------------------------------------------------
FILE_FULL = "BJ_GoG_COSO_Tableau_de_bord_Sous_projet_complet_062026.xlsx"
df_full = pd.read_excel(FILE_FULL, sheet_name='Phase de réalisation', header=0)
df_full = df_full.iloc[2:].reset_index(drop=True)
for col in df_full.columns:
    df_full[col] = df_full[col].fillna('').astype(str).str.strip()
df_full = df_full[~df_full['Département'].str.lower().isin(['nan',''])].reset_index(drop=True)

def row_key(row):
    base = (nk(row.get('Département','')), nk(row.get('Commmune','')),
            nk(row.get('Arrondissement','')), nk(row.get('Communauté','')),
            nk(row.get('Sous-composante','')))
    titre = nk(row.get('Titre du sous-projet',''))
    intit = nk(row.get('Intitulé du sous projet',''))
    keys = set()
    if titre: keys.add(base + (titre,))
    if intit: keys.add(base + (intit,))
    return keys

df_full['_already_done'] = df_full.apply(
    lambda row: bool(row_key(row) & already_keys), axis=1
)
new_rows = df_full[~df_full['_already_done']].reset_index(drop=True)
print(f"Total in full file : {len(df_full)}")
print(f"Already done (skip): {df_full['_already_done'].sum()}")
print(f"New rows to process: {len(new_rows)}")

# ---------------------------------------------------------------------------
# Step 3 — Build DB index from Investment model
# ---------------------------------------------------------------------------
db_index = defaultdict(list)
qs = Investment.objects.select_related('sector','administrative_level').all()
for inv in qs:
    key = (str(inv.administrative_level_id), str(inv.sub_component or '').strip())
    db_index[key].append({
        "id":       str(inv.id),
        "title":    inv.title or '',
        "ranking":  inv.ranking,
        "sector":   inv.sector.name if inv.sector else '',
    })
print(f"DB investments indexed: {sum(len(v) for v in db_index.values())}")

# ---------------------------------------------------------------------------
# Step 4 — Semantic matching rules
# ---------------------------------------------------------------------------
RULES = [
    ("apicult",          ["apicult"],                     10),
    ("concassage",       ["concassage"],                  10),
    ("anacarde",         ["anacarde"],                    10),
    ("karite",           ["karite","beurre"],             10),
    ("arachide",         ["arachide"],                    10),
    ("warrantage",       ["warrantage","stockage"],       10),
    ("soja",             ["soja"],                         8),
    ("riz",              ["riz"],                          8),
    ("mais",             ["mais","farine"],                8),
    ("volaille",         ["volaille","poulet"],            8),
    ("porc",             ["porc","porcin"],                8),
    ("alphabetis",       ["alphabetis"],                   8),
    ("football",         ["football","terrain de foot"],   8),
    ("sport",            ["sport","equipements sportifs"], 8),
    ("danse",            ["danse","troupe"],               8),
    ("latrine",          ["latrine"],                      6),
    ("maraich",          ["maraich","perimetre"],          6),
    ("maternite",        ["maternite","maternelle"],       6),
    ("dispensaire",      ["dispensaire","centre de sante","csa","csc"], 6),
    ("stockage",         ["stockage","magasin de stock"],  6),
    ("hangar de marche", ["hangar","marche"],              6),
    ("electr",           ["electr","lampadaire","solaire"], 6),
    ("piste",            ["piste","route","voie"],         6),
    ("franchissement",   ["franchissement","buse"],        6),
    ("trois salles",     ["trois salles","3 salles"],      8),
    ("deux salles",      ["deux salles","2 salle"],        8),
    ("salle de class",   ["salle de class","module de class"], 6),
    ("chateau d eau",    ["chateau","pea "],               8),
    ("forage",           ["forage","abreuvoir","pompe"],   6),
    ("retenue d eau",    ["retenue d eau","barrage"],      8),
    ("eau potable",      ["eau potable"],                  4),
    ("eau",              ["eau","forage","hydraul"],       4),
    ("maison des jeunes",["maison des jeunes"],            5),
    ("cloture",          ["cloture grillag","grillag"],    4),
    ("couloir pastoral", ["couloir","pastoral","paturage","betail"], 8),
]

def best_candidate(import_title, candidates):
    ititle = nk(import_title)
    scored = []
    for c in candidates:
        ctitle = nk(c.get("title","") + " " + c.get("sector",""))
        best_score, matched = 0, []
        for imp_kw, cand_kws, rule_score in RULES:
            if imp_kw in ititle and any(k in ctitle for k in cand_kws):
                if rule_score > best_score:
                    best_score, matched = rule_score, [imp_kw]
        try:
            rank_bonus = max(0, (6 - int(c.get("ranking") or 99)) * 0.1)
        except:
            rank_bonus = 0
        scored.append((best_score + rank_bonus, best_score, c["id"], matched))
    scored.sort(key=lambda x: -x[0])
    best_total, best_rule, best_id, best_rules = scored[0]
    second = scored[1][0] if len(scored) > 1 else 0
    if best_rule == 0:
        ranked = sorted(candidates, key=lambda c: int(c.get("ranking") or 99))
        return ranked[0]["id"], "low", "no_keyword_rank1_fallback"
    gap = best_total - second
    conf = "high" if gap >= 1.5 else ("medium" if gap >= 0.5 else "low")
    return best_id, conf, ", ".join(best_rules)

# ---------------------------------------------------------------------------
# Step 5 — Match each new row
# ---------------------------------------------------------------------------
results  = []
stats    = {"UNIQUE":0,"BEST":0,"AMBIGUOUS":0,"NO_MATCH":0,"NO_VILLAGE":0}
adm_cache = {}
total = len(new_rows)


# ---------------------------------------------------------------------------
# Cases pending arbitration — village/porteur not resolvable in DB.
# Isolated in cas_a_arbitrer.xlsx for staff review.
# ---------------------------------------------------------------------------
SKIP_PENDING = {
    ("kandi 1",    "kandi 1"),
    ("karimama",   "karimama"),
    ("malanville", "malanville"),
    ("segbana",    "segbana"),
    ("boukoumbe",  "boukombe"),
    ("boukoumbe",  "boukoumbe"),
    ("nikki",      "nikki"),
    ("ouake",      "ouake"),
    ("semere 1",   "semere 1"),
    ("semere 2",   "semere 2"),
    ("toumboutou", "tomboutou"),
    ("segbana",    "toutes les adv"),
    ("tchatchou",  "tous les  16 adv"),
    ("tchatchou",  "tous les 16 adv"),
    ("tomboutou",  "tomboutou"),
    ("toumboutou", "toumboutou"),
    ("gnonkourokali", "porté par adv de gnonkourokali"),
    ("karimama",   nk("Fakara, Dendi-kour\u00e9, Batouma-b\u00e9ri, Bello-Tounga, Goroub\u00e9ri et Mamassy-peulh")),
    ("kompa",      nk("Kompa, Banizoumou,  K\u00e9n\u00e9-Tounga, Kompanti, Dangazori, Gounngou-B\u00e9ri,  Garbey-koara")),
    ("segbana",    nk("Port\u00e9 par Batazi et\nLimanfrani")),
    ("nikki",      nk("Tontarou, Kali, Gourou, Danri et  Sonwore")),
    ("nikki 1",    nk("Tontarou, Kali, Gourou, Danri et  Sonwore")),
}

print(f"\nMatching {total} new rows...")

for idx, row in new_rows.iterrows():
    sub        = str(row.get('Sous-composante','')).strip()
    titre      = row.get('Titre du sous-projet','')
    intit      = row.get('Intitulé du sous projet','')
    best_title = titre if nk(titre) else intit
    cout       = row.get('Coût prévisionnel','')

    # Skip cases pending staff arbitration
    arr_nk = nk(row['Arrondissement'])
    vil_nk = nk(row['Communauté'])
    if (arr_nk, vil_nk) in SKIP_PENDING:
        stats["SKIP"] = stats.get("SKIP", 0) + 1
        results.append({
            "line":           idx + 3,
            "source":         "complet",
            "departement":    row.get('Département',''),
            "commune":        row.get('Commmune',''),
            "arrondissement": row.get('Arrondissement',''),
            "village":        row.get('Communauté',''),
            "sub_component":  sub,
            "import_intitule": best_title[:120],
            "cout":           cout,
            "db_village":     "",
            "db_village_id":  "",
            "match_status":   "SKIP_PENDING_ARBITRATION",
            "db_id":          "",
            "db_title":       "",
            "db_ranking":     "",
            "confidence":     "",
            "match_reason":   "pending staff arbitration — see cas_a_arbitrer.xlsx",
        })
        continue

    cache_key = (row['Département'], row['Commmune'],
                 row['Arrondissement'], row['Communauté'])

    if cache_key not in adm_cache:
        dept = resolve_adm_level(row['Département'],    'département')
        com  = resolve_adm_level(row['Commmune'],       'commune',        parent=dept)
        arr  = resolve_adm_level(row['Arrondissement'], 'arrondissement', parent=com)
        vil  = resolve_adm_level(row['Communauté'],     'village',        parent=arr)
        if not vil:
            import re as _re
            communaute = row['Communauté']
            # Extract porteur from patterns like "porté par [l'ADV/ADQ de] X"
            m = _re.search(
                r"port[ée]\s+par\s+(?:l['’]ad[vq]\s+(?:de\s+)?)?(.+?)[\s,\.\)]*$",
                communaute, _re.IGNORECASE
            )
            porteur_extracted = m.group(1).strip() if m else ""
            porteur_extracted = _re.sub(r"^(?:adv?\s+(?:de\s+)?|adq\s+(?:de\s+)?|de\s+)", "", porteur_extracted, flags=_re.IGNORECASE).strip()
            # Try extracted porteur
            if porteur_extracted and nk(porteur_extracted):
                vil = resolve_adm_level(porteur_extracted, 'village', parent=arr)
            # Fallback to Porteur column
            if not vil:
                porteur_col = str(row.get('Porteur', '') or '')
                if nk(porteur_col):
                    vil = resolve_adm_level(porteur_col, 'village', parent=arr)
        adm_cache[cache_key] = vil

    village = adm_cache[cache_key]

    base = {
        "line":           idx + 3,
        "source":         "complet",
        "departement":    row.get('Département',''),
        "commune":        row.get('Commmune',''),
        "arrondissement": row.get('Arrondissement',''),
        "village":        row.get('Communauté',''),
        "sub_component":  sub,
        "import_intitule": best_title[:120],
        "cout":           cout,
        "db_village":     village.name if village else "",
        "db_village_id":  village.id   if village else "",
    }

    if not village:
        stats["NO_VILLAGE"] += 1
        results.append({**base, "match_status":"NO_VILLAGE",
                        "db_id":"","db_title":"","db_ranking":"",
                        "confidence":"","match_reason":"village not resolved"})
        continue

    candidates = db_index.get((str(village.id), sub), [])

    if not candidates:
        stats["NO_MATCH"] += 1
        results.append({**base, "match_status":"NO_MATCH",
                        "db_id":"","db_title":"","db_ranking":"",
                        "confidence":"","match_reason":"no investment in DB"})
        continue

    if len(candidates) == 1:
        db_id, conf, reason = candidates[0]["id"], "high", "unique candidate"
        status = "UNIQUE"
        stats["UNIQUE"] += 1
    else:
        db_id, conf, reason = best_candidate(best_title, candidates)
        status = "BEST" if conf in ("high","medium") else "AMBIGUOUS"
        stats[status] += 1

    inv = next((c for c in candidates if c["id"] == db_id), {})
    results.append({**base,
        "match_status": status,
        "db_id":        db_id,
        "db_title":     (inv.get("title","") or "")[:100],
        "db_ranking":   inv.get("ranking",""),
        "confidence":   conf,
        "match_reason": reason,
    })

    if (idx + 1) % 200 == 0:
        print(f"  {idx+1}/{total} — {stats}")

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
with open("new_matching_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

pd.DataFrame(results).to_excel("new_matching_results.xlsx", index=False)

print("\n=== FINAL STATS ===")
for k, v in stats.items():
    print(f"  {k:12s}: {v}")
print(f"\nSaved → new_matching_results.json + new_matching_results.xlsx")
