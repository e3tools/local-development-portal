# COSO-MIS · Portail de développement local (Togo) — maquette

Maquette navigable du **Local Development Portal** avec **données fictives** générées pour les régions COSO du Togo (Savanes, Kara, Centrale).
Toutes les données (villages, personnes, montants, plaintes) sont synthétiques et déterministes (seed fixe) ; le découpage administratif est indicatif.

## Modules

| Route | Module (cf. *Design Links and Resources*) |
|---|---|
| `/` | Tableau de bord consolidé |
| `/territoires`, `/territoires/regions/[id]`, `/territoires/cantons/[id]`, `/territoires/villages/[id]` | Village profile / Canton profile |
| `/priorites` | Investment / Local priorities registry |
| `/investissements`, `/investissements/[id]` | Investment package: approval flow |
| `/grm` | GRM customization dashboard |
| `/partenaires` | Competitive view: partners & investment positions |
| `/renforcement` | Capacity-building interfaces |
| `/utilisateurs` | User management & roles |

## Stack

Next.js 16 (App Router, 100 % statique via `generateStaticParams`), React 19, Tailwind CSS 4, TypeScript. Aucune base de données, aucune variable d'environnement.

```bash
npm install
npm run dev     # http://localhost:3000
npm run build   # prérend ~625 pages
```

## Déploiement Vercel (CI)

Chaque merge dans `agentic-LDP` déclenche `.github/workflows/deploy-vercel.yml`,
qui lint, type-check, vérifie que `public/img` correspond bien au générateur,
puis construit et publie en production via la CLI Vercel.
L'intégration Git native de Vercel est désactivée (`github.enabled: false` dans
`vercel.json`) pour que ce workflow reste le seul chemin de déploiement — sinon
chaque push déploierait deux fois.

Les pull requests vers `agentic-LDP` passent par `.github/workflows/ci.yml`
(mêmes contrôles + `next build`, sans déploiement).

### Mise en service (une seule fois)

1. Créer le projet Vercel et le lier au dépôt :

   ```bash
   npm i -g vercel
   vercel link          # choisir/créer le projet, Framework: Next.js, Root Directory: /
   cat .vercel/project.json   # -> orgId et projectId
   ```

2. Créer un token sur https://vercel.com/account/settings/tokens.

3. Ajouter les trois secrets dans *Settings → Secrets and variables → Actions*
   du dépôt GitHub :

   | Secret | Valeur |
   |---|---|
   | `VERCEL_TOKEN` | le token créé à l'étape 2 |
   | `VERCEL_ORG_ID` | `orgId` de `.vercel/project.json` |
   | `VERCEL_PROJECT_ID` | `projectId` de `.vercel/project.json` |

4. Merger dans `agentic-LDP` (ou lancer le workflow à la main via
   *Actions → Deploy to Vercel → Run workflow*). L'URL de production est
   affichée dans le résumé du job.

Aucune variable d'environnement applicative n'est nécessaire : le portail est
entièrement statique et ne lit aucune base de données.

## Données fictives

Générées dans `src/data/` à partir d'un PRNG seedé (`src/lib/rng.ts`) : 3 régions,
16 préfectures, 67 cantons, **211 villages**, **1 045 priorités locales**
(4 à 6 par village, classées par rang), **334 sous-projets** (au moins un par
village), **1 300 photos**, 96 plaintes, 10 partenaires, 15 utilisateurs et
12 ressources de formation.

Invariants tenus par les générateurs :

- chaque village enregistre entre 4 et 6 priorités (`MIN/MAX_PRIORITIES_PER_VILLAGE`) ;
- la priorité de rang 1 est toujours reprise en sous-projet, donc aucun village
  n'a une fiche vide ;
- chaque village et chaque sous-projet a une photothèque, calée sur le
  vocabulaire `process_moment` du modèle `Attachment` de l'application Django
  (*Processus communautaire*, *Travaux en cours*, *Ouvrage achevé*).

Pour changer le jeu de données, modifier les seeds ou les listes de noms dans
`src/data/names.ts`.

## Images d'illustration

`public/img/` est **généré**, pas édité à la main :

```bash
npm run images   # node scripts/generate-sample-images.mjs
```

Le script dessine 35 scènes SVG (9 secteurs × 3 variantes + 8 vues de village)
de façon déterministe : relancer le générateur produit un arbre identique, et la
CI échoue si `public/img` diverge du script. Ce sont des illustrations, pas des
photographies : le portail ne contient aucune donnée ni image réelle.
