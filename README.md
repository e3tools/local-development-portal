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
npm run build   # prérend ~455 pages
```

## Déployer sur Vercel

Le dépôt est prêt tel quel (framework auto-détecté, aucune config requise).

1. Sur https://vercel.com/new, importer `e3tools/local-development-portal`.
2. Choisir la branche `agentic-LDP` (Production Branch dans *Settings → Git* si besoin).
3. Laisser les réglages par défaut (Framework: Next.js, Root Directory: `/`). Deploy.

Ou en ligne de commande :

```bash
npm i -g vercel
vercel --prod
```

## Données fictives

Générées dans `src/data/` à partir d'un PRNG seedé (`src/lib/rng.ts`) : 3 régions, 16 préfectures, 67 cantons, ~210 villages, ~630 priorités, ~160 paquets d'investissement, 96 plaintes, 10 partenaires, 15 utilisateurs, 12 ressources de formation.
Pour changer le jeu de données, modifier les seeds ou les listes de noms dans `src/data/names.ts`.
