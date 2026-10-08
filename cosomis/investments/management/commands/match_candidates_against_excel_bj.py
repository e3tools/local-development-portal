"""
Pipeline stage 3 — read-only fuzzy match of stage-2 "NO_MATCH" besoins
against the three COSO subproject tracking Excel files (en_cours, achevés,
tableau de bord complet).

Never writes to any database. We compare against all three files directly
(not just the "not yet processed" rows of the tableau complet) because a
prior import run could have silently dropped a legitimate funded row —
`import_new_funded_investments.py`'s dedup check collapses rows sharing
the same (village, sub_component, title) even when they came from distinct
Excel lines with different sector/cost, so some funded subprojects may be
missing from the DB despite being present in the Excel.

Within a bucket (administrative_level, sub_component), each Excel row can
be claimed by at most one besoin (the highest-scoring one) — losers that
still score above the review threshold are CONFLICT, not NO_MATCH, same
rule as stage 2.

Statuses:
  - MATCH:    score >= MATCH_THRESHOLD and won the bucket's assignment.
              This besoin is funded: carries the Excel row's real title,
              cost, "Sous-secteur d'activité" / "Type de sous-projet" text
              (sector/category still TBD — Excel has no Sector/Category
              taxonomy, only free text — stage 4 still assigns it).
  - REVIEW:   plausible but not confident — needs manual check.
  - CONFLICT: lost the 1:1 assignment to a better-scoring sibling.
  - NO_MATCH: genuinely unfunded — proceeds to stage 4 (categorization).

Usage:
    python manage.py match_candidates_against_excel_bj \
        --in new_needs_db_matched_bj.json \
        --out new_needs_excel_matched_bj.json \
        --files-dir .
"""
import re
import json
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from administrativelevels.utils.resolvers import resolve_adm_level


MATCH_THRESHOLD = 0.6
REVIEW_THRESHOLD = 0.35

# Threshold for the "is this Excel row already echoed in the DB" check —
# comparing against *existing Investments*, not Excel rows, so it follows
# the same "below 0.4 against an existing investment = treat as new" rule.
DB_ECHO_REVIEW_THRESHOLD = 0.4

EXCEL_FILES = {
    "en_cours": "BJ_GoG_COSO_Liste des sous-projets_en cours_16062026.xlsx",
    "acheves":  "BJ_GoG_COSO_Liste des sous-projets_achevés_15062026.xlsx",
    "complet":  "BJ_GoG_COSO_Tableau_de_bord_Sous_projet_complet_062026.xlsx",
}

STOPWORDS = {
    "de", "du", "des", "la", "le", "les", "l", "un", "une", "et", "à",
    "a", "au", "aux", "d", "en", "pour", "sur", "dans", "avec", "plus",
}


def normalize_text(s):
    s = str(s or "")
    s = s.replace("’", "'").replace("ʼ", "'").replace("‘", "'").replace("`", "'")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"[^a-z0-9' ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokenize(s):
    return [t for t in normalize_text(s).split() if t not in STOPWORDS and len(t) > 1]


def jaccard(a_tokens, b_tokens):
    a, b = set(a_tokens), set(b_tokens)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def similarity(title_a, title_b):
    norm_a, norm_b = normalize_text(title_a), normalize_text(title_b)
    tok_a, tok_b = tokenize(title_a), tokenize(title_b)
    return max(jaccard(tok_a, tok_b), SequenceMatcher(None, norm_a, norm_b).ratio())


def _best_title(row):
    titre = str(row.get("titre_sp", "") or "").strip()
    intitule = str(row.get("intitule", "") or "").strip()
    return titre if titre and titre.lower() not in ("nan", "") else intitule


def _already_in_db_via_excel_title(besoin, excel_title):
    """
    A besoin matching a confirmed-funded Excel row does NOT mean it's
    missing from the DB — that Excel row itself may already have been
    imported under its own (renamed) title, by a *different* besoin's
    ranking slot. Compare the Excel row's title (not the besoin's raw
    text) against every existing Investment in the same bucket, since
    that's the title the import would have used.
    """
    best = 0.0
    for e in besoin["existing_investments_same_adm_subcomp"]:
        score = similarity(excel_title, e["title"])
        if score > best:
            best = score
    return best


def _is_confirmed_funded(target):
    """
    en_cours/achevés are trusted by construction (the files ARE the funded
    tracking lists). The "complet" dashboard also contains subprojects
    merely earmarked for a future cycle (e.g. "MOC 2è Cycle sans les
    marchés") that are not actually funded/underway yet — only trust a
    "complet" row when its Phase explicitly says it's in realization.
    """
    if target["source"] in ("en_cours", "acheves"):
        return True
    return "realisation" in normalize_text(target.get("phase", ""))


def _extract_porteur(communaute):
    m = re.search(
        r"port[ée]\s+par\s+(?:l['’]ad[vq]\s+(?:de\s+)?)?(.+?)[\s,\.\)]*$",
        communaute, re.IGNORECASE
    )
    porteur = m.group(1).strip() if m else ""
    porteur = re.sub(
        r"^(?:adv?\s+(?:de\s+)?|adq\s+(?:de\s+)?|de\s+)", "", porteur, flags=re.IGNORECASE
    ).strip()
    return porteur


class Command(BaseCommand):
    help = (
        "Stage 3 (read-only): fuzzy-match stage-2 NO_MATCH besoins against "
        "the three COSO subproject tracking Excel files, with a 1:1 "
        "assignment per (adm, sub_component) bucket. Never writes to the DB."
    )

    def add_arguments(self, parser):
        parser.add_argument("--in", dest="in_path", default="new_needs_db_matched_bj.json")
        parser.add_argument("--out", dest="out_path", default="new_needs_excel_matched_bj.json")
        parser.add_argument("--files-dir", dest="files_dir", default=".")

    def handle(self, *args, **options):
        files_dir = Path(options["files_dir"])

        with open(options["in_path"], encoding="utf-8") as f:
            all_rows = json.load(f)

        pending = [r for r in all_rows if r["db_match"]["status"] == "NO_MATCH"]
        already_handled = [r for r in all_rows if r["db_match"]["status"] != "NO_MATCH"]

        self.stdout.write(f"Besoins to check against Excel: {len(pending)}")

        excel_rows = self._load_excel_rows(files_dir)
        self.stdout.write(f"Excel subproject rows loaded: {len(excel_rows)}")

        adm_cache = {}

        def resolve_village(row):
            cache_key = (row["departement"], row["commune"], row["arrondissement"], row["village"])
            if cache_key in adm_cache:
                return adm_cache[cache_key]
            dep = resolve_adm_level(row["departement"], "département")
            com = resolve_adm_level(row["commune"], "commune", parent=dep)
            arr = resolve_adm_level(row["arrondissement"], "arrondissement", parent=com)
            vil = resolve_adm_level(row["village"], "village", parent=arr)
            if not vil:
                porteur = row["porteur"]
                if porteur and porteur.lower() not in ("nan", ""):
                    vil = resolve_adm_level(porteur, "village", parent=arr)
            if not vil:
                extracted = _extract_porteur(row["village"])
                if extracted:
                    vil = resolve_adm_level(extracted, "village", parent=arr)
            adm_cache[cache_key] = vil
            return vil

        by_bucket = defaultdict(list)
        for row in excel_rows:
            vil = resolve_village(row)
            if vil is None:
                continue
            by_bucket[(vil.id, row["sub_component"])].append(row)

        unresolved_excel_rows = sum(
            1 for row in excel_rows if resolve_village(row) is None
        )
        if unresolved_excel_rows:
            self.stdout.write(self.style.WARNING(
                f"{unresolved_excel_rows} Excel rows have no resolvable village — excluded from matching."
            ))

        besoins_by_bucket = defaultdict(list)
        for i, r in enumerate(pending):
            key = (r["administrative_level_id"], r["sub_component"])
            besoins_by_bucket[key].append(i)

        stats = {"MATCH": 0, "REVIEW": 0, "CONFLICT": 0, "NO_MATCH": 0,
                  "ALREADY_IN_DB": 0, "DUPLICATE_RISK": 0}
        results = [None] * len(pending)

        for key, idxs in besoins_by_bucket.items():
            targets = by_bucket.get(key, [])
            if not targets:
                for i in idxs:
                    stats["NO_MATCH"] += 1
                    results[i] = self._with_excel_match(pending[i], "NO_MATCH", None, None)
                continue

            pairs = []
            for i in idxs:
                for t_idx, t in enumerate(targets):
                    score = similarity(pending[i]["title_raw"], t["title"])
                    if score >= REVIEW_THRESHOLD:
                        pairs.append((score, i, t_idx))
            pairs.sort(key=lambda p: -p[0])

            assigned = {}
            claimed = set()
            conflicted = set()

            for score, i, t_idx in pairs:
                if i in assigned:
                    continue
                if t_idx in claimed:
                    conflicted.add(i)
                    continue
                assigned[i] = (score, t_idx)
                claimed.add(t_idx)

            for i in idxs:
                if i in assigned:
                    score, t_idx = assigned[i]
                    target = targets[t_idx]
                    if score >= MATCH_THRESHOLD and _is_confirmed_funded(target):
                        db_echo_score = _already_in_db_via_excel_title(pending[i], target["title"])
                        if db_echo_score >= MATCH_THRESHOLD:
                            status = "ALREADY_IN_DB"
                        elif db_echo_score >= DB_ECHO_REVIEW_THRESHOLD:
                            # Strong textual match to a confirmed-funded Excel
                            # row, but an ambiguous echo in the DB — too risky
                            # to create (could be a duplicate), not confident
                            # enough to call it already-in-DB either. Dropped
                            # per user decision rather than queued for review.
                            status = "DUPLICATE_RISK"
                        else:
                            status = "MATCH"
                    else:
                        status = "REVIEW"
                    stats[status] += 1
                    results[i] = self._with_excel_match(pending[i], status, score, target)
                elif i in conflicted:
                    # Same rule as the DB-matching stage: in a bucket with
                    # 2+ already-won Excel rows, an extra besoin resembling
                    # one of them is taken to be covered already.
                    status = "ALREADY_IN_DB" if len(assigned) > 1 else "CONFLICT"
                    stats[status] += 1
                    results[i] = self._with_excel_match(pending[i], status, None, None)
                else:
                    stats["NO_MATCH"] += 1
                    results[i] = self._with_excel_match(pending[i], "NO_MATCH", None, None)

        final = already_handled + results
        with open(options["out_path"], "w", encoding="utf-8") as f:
            json.dump(final, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f"Excel match — MATCH: {stats['MATCH']} | REVIEW: {stats['REVIEW']} | "
            f"CONFLICT: {stats['CONFLICT']} | NO_MATCH: {stats['NO_MATCH']} | "
            f"ALREADY_IN_DB: {stats['ALREADY_IN_DB']} | "
            f"DUPLICATE_RISK: {stats['DUPLICATE_RISK']} | "
            f"written to {options['out_path']}"
        ))

    def _with_excel_match(self, besoin, status, score, target):
        return {
            **besoin,
            "excel_match": {
                "status": status,
                "score": round(score, 3) if score is not None else None,
                "source": target["source"] if target else None,
                "line": target["line"] if target else None,
                "title": target["title"] if target else None,
                "cost": target["cost"] if target else None,
                "sous_secteur": target["sous_secteur"] if target else None,
                "type_sous_projet": target["type_sp"] if target else None,
                "phase": target.get("phase") if target else None,
                "confirmed_funded": _is_confirmed_funded(target) if target else None,
            },
        }

    def _load_excel_rows(self, files_dir):
        rows = []

        for source in ("en_cours", "acheves"):
            path = files_dir / EXCEL_FILES[source]
            if not path.exists():
                raise CommandError(f"Import file not found: {path}")
            xl = pd.ExcelFile(path)
            df = xl.parse(xl.sheet_names[0])
            df = df.rename(columns={
                "Département": "departement", "Commmune": "commune",
                "Arrondissement": "arrondissement", "Communauté": "village",
                "Porteur": "porteur", "Intitulé du sous projet": "intitule",
                "Titre du sous-projet": "titre_sp", "Sous-composante": "sub_component",
                "Coût prévisionnel": "cout", "Sous-secteur d'activité": "sous_secteur",
                "Type de sous-projet": "type_sp",
            })
            for col in ["departement", "commune", "arrondissement", "village", "porteur",
                        "intitule", "titre_sp", "sub_component", "sous_secteur", "type_sp"]:
                df[col] = df[col].astype(str).str.strip() if col in df.columns else ""
            df = df[~df["departement"].str.lower().isin(["nan", ""])]

            for idx, row in df.iterrows():
                rows.append({
                    "source": source,
                    "line": idx + 2,
                    "departement": row["departement"], "commune": row["commune"],
                    "arrondissement": row["arrondissement"], "village": row["village"],
                    "porteur": row["porteur"], "sub_component": row["sub_component"],
                    "title": _best_title(row),
                    "cost": str(row.get("cout", "") or ""),
                    "sous_secteur": row.get("sous_secteur", ""),
                    "type_sp": row.get("type_sp", ""),
                    "phase": None,
                })

        path = files_dir / EXCEL_FILES["complet"]
        if not path.exists():
            raise CommandError(f"Import file not found: {path}")
        df_full = pd.read_excel(path, sheet_name="Phase de réalisation", header=0)
        df_full = df_full.iloc[2:].reset_index(drop=True)
        for col in df_full.columns:
            df_full[col] = df_full[col].fillna("").astype(str).str.strip()
        df_full = df_full[~df_full["Département"].str.lower().isin(["nan", ""])].reset_index(drop=True)

        for idx, row in df_full.iterrows():
            rows.append({
                "source": "complet",
                "line": idx + 3,
                "departement": row.get("Département", ""), "commune": row.get("Commmune", ""),
                "arrondissement": row.get("Arrondissement", ""), "village": row.get("Communauté", ""),
                "porteur": row.get("Porteur", ""), "sub_component": row.get("Sous-composante", ""),
                "title": _best_title({
                    "titre_sp": row.get("Titre du sous-projet", ""),
                    "intitule": row.get("Intitulé du sous projet", ""),
                }),
                "cost": str(row.get("Coût prévisionnel", "") or ""),
                "sous_secteur": row.get("Sous-secteur d'activité", ""),
                "type_sp": row.get("Type de sous-projet", ""),
                "phase": row.get("Phase du sous-projet", ""),
            })

        return rows
