# Protocole de synchronisation des nouveaux besoins (BJ)

Ce document décrit le pipeline utilisé pour récupérer les nouveaux besoins
exprimés par les agents de terrain (via `synctasks`/CouchDB) et les ajouter
au portail (LDP) sans jamais écrire en base avant la toute dernière étape.

## Pourquoi ce pipeline existe

- Les besoins sont collectés non catégorisés. Quand un besoin est
  sélectionné pour être financé par COSO, il est renommé et catégorisé —
  mais ce renommage casse tout rapprochement par titre entre le besoin
  d'origine et le sous-projet financé.
- Le contenu des fichiers Excel de suivi COSO (`en_cours`, `achevés`,
  tableau de bord complet) est déjà en grande partie importé en base — mais
  certains sous-projets ont été ajoutés directement depuis l'Excel sans
  jamais passer par un besoin CouchDB (agents n'ayant pas renseigné
  l'application). Un besoin qui semble "nouveau" peut donc déjà être
  couvert par un Investment existant sous un autre nom.
- Les apostrophes (droite `'` vs courbe `’`) sont utilisées sans aucun
  pattern cohérent dans les données sources — toute comparaison de texte
  doit les normaliser.

## Les 7 commandes, dans l'ordre

Toutes sous `investments/management/commands/`. Les 6 premières sont
**strictement en lecture** (aucune écriture SQL ni CouchDB) ; seule la
dernière (`import_new_needs_bj`) écrit en base et est destinée à tourner en
prod.

| # | Commande | Entrée | Sortie | Rôle |
|---|---|---|---|---|
| 1 | `extract_new_needs_bj` | CouchDB + DB (lecture) + ledger | `new_needs_candidates_bj.json` | Extrait les besoins, exclut ceux déjà synchronisés par position `(adm, sous_composante, ranking)` et ceux déjà verrouillés dans le ledger |
| 2 | `match_candidates_against_db_bj` | sortie de 1 | `new_needs_db_matched_bj.json` | Matching flou 1:1 par bucket contre les Investments déjà existants (cas "ajouté directement depuis l'Excel") |
| 3 | `match_candidates_against_excel_bj` | sortie de 2 | `new_needs_excel_matched_bj.json` | Matching flou 1:1 contre les 3 fichiers Excel COSO, + vérification que le sous-projet Excel matché n'a pas déjà un écho en base sous un autre nom |
| 3.5 | `apply_capacity_cap_bj` | sortie de 3 | `new_needs_capacity_capped_bj.json` | Applique la règle métier "max 5 besoins par (village, sous-composante)" et la règle "sous la capacité, pas d'arbitrage forcé" |
| 4 | `categorize_candidates_bj` | sortie de 3.5 | `new_needs_categorized_bj.json` | Secteur/catégorie (mapping exact puis règles heuristiques par mots-clés) + coût estimatif |
| 5 | `build_review_file_bj` | sortie de 4 | `new_needs_review_bj.xlsx` | Consolide tout en un seul Excel, colonne `decision` pré-remplie, à éditer à la main si besoin |
| 5.5 | `lock_in_resolved_needs_bj` | Excel de 5 (après arbitrage) | `config_data/resolved_needs_bj.json` | Verrouille l'arbitrage dans le ledger, **sans toucher la base** — peut se faire indépendamment de l'import final |
| 6 | `import_new_needs_bj` | Excel de 5 | écrit en DB + met à jour le ledger | **Seule commande à exécuter en prod.** Crée les Investments pour les lignes `CREATE_FUNDED`/`CREATE_UNFUNDED`, idempotente via `no_sql_id` |

Commande type pour un futur sync (tout en lecture jusqu'à l'étape 5.5) :

```bash
python manage.py extract_new_needs_bj --out new_needs_candidates_bj.json
python manage.py match_candidates_against_db_bj --in new_needs_candidates_bj.json --out new_needs_db_matched_bj.json
python manage.py match_candidates_against_excel_bj --in new_needs_db_matched_bj.json --out new_needs_excel_matched_bj.json --files-dir .
python manage.py apply_capacity_cap_bj --in new_needs_excel_matched_bj.json --out new_needs_capacity_capped_bj.json
python manage.py categorize_candidates_bj --in new_needs_capacity_capped_bj.json --out new_needs_categorized_bj.json
python manage.py build_review_file_bj --in new_needs_categorized_bj.json --out new_needs_review_bj.xlsx
# -> ouvrir new_needs_review_bj.xlsx, arbitrer les lignes CHECK_* restantes
python manage.py lock_in_resolved_needs_bj --review-file new_needs_review_bj.xlsx   # optionnel, verrouille sans écrire en DB
python manage.py import_new_needs_bj --review-file new_needs_review_bj.xlsx --dry-run   # vérifier avant
python manage.py import_new_needs_bj --review-file new_needs_review_bj.xlsx             # exécution réelle, prod uniquement
```

## Le ledger : `config_data/resolved_needs_bj.json`

Fichier commité (non gitignoré, contrairement aux `.xlsx`/`.json`
intermédiaires du dossier de travail). Clé = `no_sql_id` au format
`"<document_id_couchdb>:<sous_composante>:<ranking>"`. Chaque entrée porte
la `decision` finale (`CREATE_FUNDED`, `CREATE_UNFUNDED`, `ALREADY_IN_DB`,
`EXCLUDED_CAPACITY_CAP`, `EXCLUDED_DUPLICATE_RISK`), le titre brut, le
village et la date de résolution.

`extract_new_needs_bj` (étape 1) consulte ce ledger et exclut **tout**
besoin déjà présent dedans — y compris ceux qui n'ont jamais généré
d'Investment (`ALREADY_IN_DB`, `EXCLUDED_*`). C'est ce qui évite de refaire
tout ce travail d'arbitrage à chaque nouveau `synctasks`. Seules les lignes
encore `CHECK_DB_MATCH`/`CHECK_EXCEL_MATCH` au moment du verrouillage
restent hors ledger et pourront ressurgir plus tard si le cas se représente.

`import_new_needs_bj` met aussi à jour ce ledger automatiquement à chaque
exécution réelle (non dry-run) — `lock_in_resolved_needs_bj` permet de le
faire indépendamment, sans toucher la base, par exemple pour verrouiller un
arbitrage avant d'être prêt à lancer l'import en prod.

## Règles de décision retenues (session du 2026-10-08)

- **Clé de position stable** : `(administrative_level, sub_component,
  ranking)` — jamais `title`, qui change lors de l'arbitrage financement.
- **Seuils de similarité texte** (normalisation accents + apostrophes
  systématique) :
  - Contre un Investment déjà existant (étapes 2 et l'écho de l'étape 3) :
    `< 0.4` → pas de rapport, candidat neuf ; `0.4–0.6` → ambigu ;
    `≥ 0.6` → confirmé.
  - Contre une ligne Excel (étape 3, matching direct) : `< 0.35` → pas de
    rapport ; `0.35–0.6` → ambigu ; `≥ 0.6` → confirmé **et** phase du
    sous-projet contenant "réalisation" (sinon juste ambigu — un sous-projet
    en "MOC/MODC cycle futur" n'est pas encore réellement financé).
- **Conflits 1:1 par bucket** : dans un `(village, sous-composante)`, une
  cible existante (DB ou Excel) ne peut être "gagnée" que par le besoin au
  meilleur score ; les autres passent en `CONFLICT`, jamais auto-rejetés ni
  auto-créés.
- **Risque de doublon** (étape 3) : match Excel fort (≥0.6, phase
  confirmée) mais écho DB ambigu (0.4–0.6) avec un Investment existant sous
  un autre nom → exclu (`EXCLUDED_DUPLICATE_RISK`), ni créé ni confirmé déjà
  en base.
- **Capacité max 5 besoins par `(village, sous-composante)`** (reflète les 5
  emplacements du formulaire EPB) :
  - Si `existants + candidats > 5` et qu'il existe des candidats déjà
    ambigus (`CHECK_*`) dans ce bucket → ils sont **tous** reclassés
    `ALREADY_IN_DB` (la contrainte de capacité renforce le signal textuel
    déjà présent, plutôt que de ne lever que le strict excédent).
  - Si tous les candidats sont "propres" (aucun signal de ressemblance) →
    on exclut le `ranking` le plus élevé (le besoin le moins prioritaire
    selon le classement donné par la communauté) jusqu'à revenir à 5.
  - Si le bucket **n'est pas** en sur-capacité, aucun arbitrage n'est
    nécessaire : tout besoin encore `REVIEW`/`CONFLICT` à ce stade (aucun ne
    dépassant un score de ~0.6 dans les données observées, donc loin d'un
    quasi-duplicat) est simplement créé — pas de raison de choisir un
    gagnant s'il y a de la place pour tout le monde.
- **`investment_status`/`project_status` à la création** :
  `SUBPROJECT`/`FUNDED_NOT_STARTED` pour un besoin financé, `PRIORITY`/
  `NOT_FUNDED` pour un besoin non financé — corrige un bug trouvé dans
  `import_new_funded_investments.py` où les créations `TO_CREATE`
  recevaient `PRIORITY` même en étant `FUNDED_NOT_STARTED`.
- **Traçabilité future** : chaque Investment créé reçoit `ranking` et
  `no_sql_id` — jamais renseignés par `2_syncpriorities_bj` historiquement,
  ce qui cassait tout rapprochement fiable après un renommage.

## Limites connues

- Les règles de catégorisation par mots-clés (`categorize_candidates_bj`)
  comparent des sous-chaînes : une phrase à plusieurs thèmes peut mal
  trancher (ex. "pompe" l'emportant sur "éclairage public" dans un même
  intitulé). Les besoins `CREATE_*` avec `categorization_confidence` =
  `medium`/`high` ne sont pas garantis corrects à 100 %, juste
  vraisemblables.
- Les fichiers Excel de suivi COSO n'ont pas de colonne Secteur/Catégorie —
  seulement du texte libre ("Sous-secteur d'activité"). Le secteur assigné
  à un besoin financé (`CREATE_FUNDED`) vient donc toujours de
  `categorize_candidates_bj`, pas de l'Excel lui-même.
- `priority_to_sector_mapping.json` et les règles heuristiques ne couvrent
  pas tous les types de besoins ; "Autre" reste la valeur par défaut légitime
  quand rien ne correspond.
