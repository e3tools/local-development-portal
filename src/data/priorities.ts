import { createRng } from "@/lib/rng";
import { VILLAGES } from "./geo";
import { PRIORITY_TITLES, SECTORS, type Sector } from "./sectors";

export const PRIORITY_STATUSES = ["Identifiée", "Validée CCD", "Intégrée au PDC", "Financée", "Non retenue"] as const;
export type PriorityStatus = (typeof PRIORITY_STATUSES)[number];
export const PRIORITY_SOURCES = ["Assemblée villageoise", "Focus groupe femmes", "Focus groupe jeunes", "Diagnostic participatif"] as const;

// Villages register between MIN and MAX priorities each, ranked by the village
// assembly. Rank 1 is always carried forward, so every village has at least one
// sub-project attached to it (see data/investments.ts).
export const MIN_PRIORITIES_PER_VILLAGE = 4;
export const MAX_PRIORITIES_PER_VILLAGE = 6;

export type Priority = {
  id: string;
  code: string;
  villageId: string;
  rank: number;
  sector: Sector;
  title: string;
  estimatedCostFcfa: number;
  beneficiaries: number;
  status: PriorityStatus;
  source: (typeof PRIORITY_SOURCES)[number];
  registeredAt: string;
  votes: number;
};

const rng = createRng(7);
const COST: Record<Sector, [number, number]> = {
  "Eau & assainissement": [8, 45],
  "Éducation": [25, 70],
  "Santé": [30, 90],
  "Pistes rurales": [40, 160],
  "Agriculture": [15, 60],
  "Énergie": [10, 35],
  "Infrastructures économiques": [20, 55],
  "Cohésion sociale": [5, 30],
  "Environnement": [4, 20],
};

export const PRIORITIES: Priority[] = [];
let seq = 1;
for (const v of VILLAGES) {
  const sectors = rng.sample(SECTORS, rng.int(MIN_PRIORITIES_PER_VILLAGE, MAX_PRIORITIES_PER_VILLAGE));
  sectors.forEach((sector, i) => {
    const [lo, hi] = COST[sector];
    // Rank 1 always reaches the PDC so the village has a sub-project to show;
    // the tail of the list spreads across the rest of the funnel.
    const status: PriorityStatus =
      i === 0
        ? rng.pick(["Financée", "Financée", "Financée", "Intégrée au PDC"])
        : i === 1
          ? rng.pick(["Validée CCD", "Intégrée au PDC", "Financée", "Identifiée"])
          : rng.pick(["Identifiée", "Validée CCD", "Intégrée au PDC", "Non retenue", "Identifiée"]);
    PRIORITIES.push({
      id: `prio-${seq}`,
      code: `LP-${String(seq).padStart(4, "0")}`,
      villageId: v.id,
      rank: i + 1,
      sector,
      title: rng.pick(PRIORITY_TITLES[sector]),
      estimatedCostFcfa: rng.int(lo, hi) * 1_000_000,
      beneficiaries: Math.round(v.population * (rng.int(40, 100) / 100)),
      status,
      source: rng.pick(PRIORITY_SOURCES),
      registeredAt: `2025-${String(rng.int(2, 12)).padStart(2, "0")}-${String(rng.int(1, 28)).padStart(2, "0")}`,
      votes: rng.int(40, 320),
    });
    seq++;
  });
}
export const priorityById = (id: string) => PRIORITIES.find((p) => p.id === id);
export const prioritiesOfVillage = (villageId: string) => PRIORITIES.filter((p) => p.villageId === villageId);
