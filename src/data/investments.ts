import { createRng } from "@/lib/rng";
import { addDays } from "@/lib/format";
import { PRIORITIES } from "./priorities";
import type { Sector } from "./sectors";

export const APPROVAL_STEPS = [
  { key: "cvd", label: "Soumission CVD", role: "Comité villageois de développement" },
  { key: "ccd", label: "Validation CCD", role: "Comité cantonal de développement" },
  { key: "commune", label: "Revue communale", role: "Point focal communal" },
  { key: "region", label: "Revue régionale", role: "Coordonnateur régional" },
  { key: "ucp", label: "Approbation UCP", role: "Unité de coordination du projet" },
  { key: "financement", label: "Mise en place financement", role: "Chargé financier UCP" },
] as const;

export const INVESTMENT_STATUSES = ["Soumis", "Validation CCD", "Revue communale", "Revue régionale", "Approbation UCP", "Approuvé", "En exécution", "Achevé", "Rejeté"] as const;
export type InvestmentStatus = (typeof INVESTMENT_STATUSES)[number];
export type StepStatus = "Terminé" | "En cours" | "En attente" | "Rejeté";
export type ApprovalStep = { key: string; label: string; role: string; actor: string; status: StepStatus; date?: string; comment?: string };

export type Investment = {
  id: string;
  code: string;
  title: string;
  sector: Sector;
  villageId: string;
  priorityId: string;
  budgetFcfa: number;
  disbursedFcfa: number;
  physicalProgress: number;
  status: InvestmentStatus;
  submittedAt: string;
  steps: ApprovalStep[];
  partnerId: string;
  contractor?: string;
  beneficiaries: number;
  womenBeneficiaries: number;
  himoJobs: number; // emplois HIMO créés
  startDate?: string;
  expectedEndDate?: string;
};

const rng = createRng(42);
const CONTRACTORS = ["ETS Nabagou & Fils", "SOTOCO BTP", "Entreprise Lamboni Construction", "GTC Togo", "Coopérative HIMO Savanes", "SAHEL Forages SARL", "ECOBAT Kara", "Solar Togo SA"];
const ACTORS: Record<string, string[]> = {
  cvd: ["Président CVD"],
  ccd: ["Président CCD"],
  commune: ["A. Kolani", "E. Tchagnao", "M. Ouro-Djobo"],
  region: ["Coord. Savanes – Y. Douti", "Coord. Kara – P. Badjona", "Coord. Centrale – S. Boukari"],
  ucp: ["UCP – Direction technique", "UCP – Comité d'approbation"],
  financement: ["UCP – Service financier"],
};
const COMMENTS = ["Dossier complet.", "Devis actualisé demandé.", "Conforme au PDC.", "Site visité, foncier sécurisé.", "Budget ajusté (-5 %).", "Étude environnementale validée.", "Priorité confirmée par l'assemblée."];
const PARTNER_IDS = ["ida", "ida", "ida", "afd", "giz", "pnud", "unicef", "boad"];

// Terminal step index for each status
const STATUS_STEP: Record<InvestmentStatus, number> = {
  Soumis: 0, "Validation CCD": 1, "Revue communale": 2, "Revue régionale": 3, "Approbation UCP": 4, Approuvé: 5, "En exécution": 6, Achevé: 6, Rejeté: -1,
};

export const INVESTMENTS: Investment[] = [];
const candidates = PRIORITIES.filter((p) => p.status === "Financée" || p.status === "Intégrée au PDC");
let seq = 1;
for (const p of candidates) {
  if (p.status === "Intégrée au PDC" && !rng.chance(0.4)) continue;
  const status: InvestmentStatus =
    p.status === "Financée"
      ? rng.pick(["En exécution", "En exécution", "Achevé", "Approuvé", "En exécution"])
      : rng.pick(["Soumis", "Validation CCD", "Revue communale", "Revue régionale", "Approbation UCP", "Rejeté"]);
  const budget = Math.round(p.estimatedCostFcfa * (rng.int(85, 110) / 100));
  const submittedAt = addDays(p.registeredAt, rng.int(20, 90));
  const stepIdx = STATUS_STEP[status];
  const rejectAt = status === "Rejeté" ? rng.int(1, 4) : -1;
  let date = submittedAt;
  const steps: ApprovalStep[] = APPROVAL_STEPS.map((s, i) => {
    const actor = rng.pick(ACTORS[s.key]);
    if (status === "Rejeté") {
      if (i < rejectAt) { date = addDays(date, rng.int(5, 30)); return { ...s, actor, status: "Terminé", date, comment: rng.pick(COMMENTS) }; }
      if (i === rejectAt) { date = addDays(date, rng.int(5, 30)); return { ...s, actor, status: "Rejeté", date, comment: "Non conforme : coût unitaire hors barème / doublon avec un autre partenaire." }; }
      return { ...s, actor, status: "En attente" };
    }
    if (i < stepIdx) { date = addDays(date, rng.int(5, 30)); return { ...s, actor, status: "Terminé", date, comment: rng.chance(0.6) ? rng.pick(COMMENTS) : undefined }; }
    if (i === stepIdx && stepIdx < APPROVAL_STEPS.length) return { ...s, actor, status: "En cours" };
    return { ...s, actor, status: "En attente" };
  });
  const lastDate = steps.filter((s) => s.date).slice(-1)[0]?.date ?? submittedAt;
  const executing = status === "En exécution" || status === "Achevé";
  const progress = status === "Achevé" ? 100 : status === "En exécution" ? rng.int(10, 90) : 0;
  const disbursed = status === "Achevé" ? Math.round(budget * (rng.int(95, 100) / 100)) : status === "En exécution" ? Math.round(budget * (progress / 100) * (rng.int(80, 100) / 100)) : status === "Approuvé" ? Math.round(budget * 0.2) : 0;
  INVESTMENTS.push({
    id: `inv-${seq}`,
    code: `SP-${String(seq).padStart(3, "0")}`,
    title: p.title,
    sector: p.sector,
    villageId: p.villageId,
    priorityId: p.id,
    budgetFcfa: budget,
    disbursedFcfa: disbursed,
    physicalProgress: progress,
    status,
    submittedAt,
    steps,
    partnerId: rng.pick(PARTNER_IDS),
    contractor: executing ? rng.pick(CONTRACTORS) : undefined,
    beneficiaries: p.beneficiaries,
    womenBeneficiaries: Math.round(p.beneficiaries * (rng.int(45, 58) / 100)),
    himoJobs: executing ? rng.int(12, 80) : 0,
    startDate: executing ? addDays(lastDate, rng.int(10, 40)) : undefined,
    expectedEndDate: executing ? addDays(lastDate, rng.int(150, 360)) : undefined,
  });
  seq++;
}
export const investmentById = (id: string) => INVESTMENTS.find((i) => i.id === id);
export const investmentsOfVillage = (villageId: string) => INVESTMENTS.filter((i) => i.villageId === villageId);
