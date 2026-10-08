"""
Pipeline stage 2 — read-only fuzzy match of stage-1 candidate besoins
against existing Investments in the same (administrative_level,
sub_component) bucket that have no stable position (ranking is None),
i.e. investments force-added directly from the COSO tracking Excel files
without ever going through a CouchDB-synced besoin.

Never writes to the database. Reads the stage-1 JSON (extract_new_needs_bj)
and produces a new JSON with a `db_match` block per candidate.

Within a bucket, each existing target can be claimed by at most one besoin
(the highest-scoring one) — a besoin that also resembles a target already
claimed by a better-scoring sibling is marked CONFLICT, not MATCH, so it
isn't silently dropped as "already funded" when it might still be a
distinct, genuinely unfunded need.

Statuses:
  - MATCH:     score >= MATCH_THRESHOLD and won the bucket's assignment.
  - REVIEW:    REVIEW_THRESHOLD <= score < MATCH_THRESHOLD and won the
               assignment — plausible but not confident enough to auto-link.
  - CONFLICT:  score >= REVIEW_THRESHOLD but lost the assignment to a
               higher-scoring sibling targeting the same existing
               investment — needs manual arbitration.
  - NO_MATCH:  no candidate target scored >= REVIEW_THRESHOLD — treated as
               genuinely new, proceeds to stage 3 (Excel matching).

Usage:
    python manage.py match_candidates_against_db_bj \
        --in new_needs_candidates_bj.json \
        --out new_needs_db_matched_bj.json
"""
import json
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

from django.core.management.base import BaseCommand


MATCH_THRESHOLD = 0.6
REVIEW_THRESHOLD = 0.4

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


class Command(BaseCommand):
    help = (
        "Stage 2 (read-only): fuzzy-match stage-1 candidate besoins against "
        "existing Investments force-added from Excel (ranking is None) in "
        "the same (adm, sub_component) bucket, with a 1:1 assignment per "
        "bucket. Never writes to the database."
    )

    def add_arguments(self, parser):
        parser.add_argument("--in", dest="in_path", default="new_needs_candidates_bj.json")
        parser.add_argument("--out", dest="out_path", default="new_needs_db_matched_bj.json")

    def handle(self, *args, **options):
        with open(options["in_path"], encoding="utf-8") as f:
            candidates = json.load(f)

        by_bucket = defaultdict(list)
        for i, c in enumerate(candidates):
            key = (c["administrative_level_id"], c["sub_component"])
            by_bucket[key].append(i)

        results = [None] * len(candidates)
        stats = {"MATCH": 0, "REVIEW": 0, "CONFLICT": 0, "NO_MATCH": 0, "ALREADY_IN_DB": 0}

        for key, idxs in by_bucket.items():
            targets = [
                t for t in candidates[idxs[0]]["existing_investments_same_adm_subcomp"]
                if t["ranking"] is None
            ]
            if not targets:
                for i in idxs:
                    stats["NO_MATCH"] += 1
                    results[i] = {
                        **candidates[i],
                        "db_match": {"status": "NO_MATCH", "score": 0.0,
                                     "investment_id": None, "investment_title": None},
                    }
                continue

            # Score every (besoin, target) pair in this bucket.
            pairs = []
            for i in idxs:
                for t in targets:
                    score = similarity(candidates[i]["title_raw"], t["title"])
                    if score >= REVIEW_THRESHOLD:
                        pairs.append((score, i, t))
            pairs.sort(key=lambda p: -p[0])

            claimed_targets = set()
            assigned = {}  # candidate index -> (score, target)
            conflicted = set()

            for score, i, t in pairs:
                if i in assigned:
                    continue  # besoin already won a (better) target
                if t["id"] in claimed_targets:
                    conflicted.add(i)
                    continue
                assigned[i] = (score, t)
                claimed_targets.add(t["id"])

            for i in idxs:
                if i in assigned:
                    score, t = assigned[i]
                    status = "MATCH" if score >= MATCH_THRESHOLD else "REVIEW"
                    stats[status] += 1
                    results[i] = {
                        **candidates[i],
                        "db_match": {"status": status, "score": round(score, 3),
                                     "investment_id": t["id"], "investment_title": t["title"]},
                    }
                elif i in conflicted:
                    # When a bucket has 2+ existing targets each already won by
                    # a besoin, an extra besoin resembling one of them is taken
                    # to be covered by whichever of those investments it is —
                    # not a genuinely new need (per user decision).
                    status = "ALREADY_IN_DB" if len(assigned) > 1 else "CONFLICT"
                    stats[status] += 1
                    results[i] = {
                        **candidates[i],
                        "db_match": {"status": status, "score": None,
                                     "investment_id": None, "investment_title": None},
                    }
                else:
                    stats["NO_MATCH"] += 1
                    results[i] = {
                        **candidates[i],
                        "db_match": {"status": "NO_MATCH", "score": 0.0,
                                     "investment_id": None, "investment_title": None},
                    }

        with open(options["out_path"], "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f"MATCH: {stats['MATCH']} | REVIEW: {stats['REVIEW']} | "
            f"CONFLICT: {stats['CONFLICT']} | NO_MATCH: {stats['NO_MATCH']} | "
            f"ALREADY_IN_DB (multi-winner bucket): {stats['ALREADY_IN_DB']} | "
            f"written to {options['out_path']}"
        ))
