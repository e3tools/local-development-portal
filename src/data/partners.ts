import type { Sector } from "./sectors";

export type Partner = {
  id: string;
  name: string;
  shortName: string;
  type: "Bailleur" | "Agence ONU" | "ONG internationale" | "Agence nationale" | "Coopération bilatérale";
  sectors: Sector[];
  regions: string[];
  commitmentFcfa: number;
  activeProjects: number;
  focalPoint: string;
  positions: { regionId: string; sector: Sector; amountFcfa: number; projects: number }[];
};

const M = 1_000_000;
export const PARTNERS: Partner[] = [
  { id: "ida", name: "Banque mondiale (IDA) – Projet COSO", shortName: "IDA / COSO", type: "Bailleur", sectors: ["Eau & assainissement", "Éducation", "Santé", "Pistes rurales", "Cohésion sociale"], regions: ["savanes", "kara", "centrale"], commitmentFcfa: 36_000 * M, activeProjects: 48, focalPoint: "UCP COSO – Lomé",
    positions: [
      { regionId: "savanes", sector: "Eau & assainissement", amountFcfa: 4200 * M, projects: 9 }, { regionId: "savanes", sector: "Éducation", amountFcfa: 3800 * M, projects: 7 }, { regionId: "savanes", sector: "Pistes rurales", amountFcfa: 5100 * M, projects: 4 }, { regionId: "savanes", sector: "Cohésion sociale", amountFcfa: 900 * M, projects: 6 },
      { regionId: "kara", sector: "Santé", amountFcfa: 2700 * M, projects: 5 }, { regionId: "kara", sector: "Éducation", amountFcfa: 2100 * M, projects: 6 }, { regionId: "kara", sector: "Eau & assainissement", amountFcfa: 1900 * M, projects: 5 },
      { regionId: "centrale", sector: "Pistes rurales", amountFcfa: 3200 * M, projects: 3 }, { regionId: "centrale", sector: "Santé", amountFcfa: 1500 * M, projects: 3 },
    ] },
  { id: "afd", name: "Agence Française de Développement", shortName: "AFD", type: "Bailleur", sectors: ["Agriculture", "Eau & assainissement", "Énergie"], regions: ["savanes", "kara"], commitmentFcfa: 9_800 * M, activeProjects: 11, focalPoint: "Agence AFD Lomé",
    positions: [{ regionId: "savanes", sector: "Agriculture", amountFcfa: 3600 * M, projects: 4 }, { regionId: "savanes", sector: "Eau & assainissement", amountFcfa: 2400 * M, projects: 3 }, { regionId: "kara", sector: "Énergie", amountFcfa: 1800 * M, projects: 2 }, { regionId: "kara", sector: "Agriculture", amountFcfa: 2000 * M, projects: 2 }] },
  { id: "giz", name: "Deutsche Gesellschaft für Internationale Zusammenarbeit", shortName: "GIZ", type: "Coopération bilatérale", sectors: ["Agriculture", "Cohésion sociale", "Environnement"], regions: ["savanes", "kara", "centrale"], commitmentFcfa: 7_200 * M, activeProjects: 9, focalPoint: "Bureau GIZ Kara",
    positions: [{ regionId: "savanes", sector: "Cohésion sociale", amountFcfa: 2100 * M, projects: 3 }, { regionId: "kara", sector: "Agriculture", amountFcfa: 2600 * M, projects: 3 }, { regionId: "centrale", sector: "Environnement", amountFcfa: 1300 * M, projects: 2 }, { regionId: "centrale", sector: "Agriculture", amountFcfa: 1200 * M, projects: 1 }] },
  { id: "pnud", name: "Programme des Nations Unies pour le développement", shortName: "PNUD", type: "Agence ONU", sectors: ["Cohésion sociale", "Énergie", "Environnement"], regions: ["savanes"], commitmentFcfa: 4_100 * M, activeProjects: 6, focalPoint: "PNUD Togo – Dapaong",
    positions: [{ regionId: "savanes", sector: "Cohésion sociale", amountFcfa: 2300 * M, projects: 4 }, { regionId: "savanes", sector: "Énergie", amountFcfa: 1800 * M, projects: 2 }] },
  { id: "unicef", name: "Fonds des Nations Unies pour l'enfance", shortName: "UNICEF", type: "Agence ONU", sectors: ["Éducation", "Eau & assainissement", "Santé"], regions: ["savanes", "kara"], commitmentFcfa: 5_600 * M, activeProjects: 8, focalPoint: "UNICEF Togo – Zone Nord",
    positions: [{ regionId: "savanes", sector: "Éducation", amountFcfa: 1900 * M, projects: 3 }, { regionId: "savanes", sector: "Eau & assainissement", amountFcfa: 1700 * M, projects: 3 }, { regionId: "kara", sector: "Santé", amountFcfa: 2000 * M, projects: 2 }] },
  { id: "pam", name: "Programme alimentaire mondial", shortName: "PAM", type: "Agence ONU", sectors: ["Agriculture", "Éducation"], regions: ["savanes"], commitmentFcfa: 3_300 * M, activeProjects: 4, focalPoint: "PAM Togo",
    positions: [{ regionId: "savanes", sector: "Éducation", amountFcfa: 1800 * M, projects: 2 }, { regionId: "savanes", sector: "Agriculture", amountFcfa: 1500 * M, projects: 2 }] },
  { id: "boad", name: "Banque Ouest Africaine de Développement", shortName: "BOAD", type: "Bailleur", sectors: ["Pistes rurales", "Infrastructures économiques"], regions: ["kara", "centrale"], commitmentFcfa: 8_900 * M, activeProjects: 3, focalPoint: "BOAD – Lomé",
    positions: [{ regionId: "kara", sector: "Pistes rurales", amountFcfa: 4500 * M, projects: 1 }, { regionId: "centrale", sector: "Infrastructures économiques", amountFcfa: 2400 * M, projects: 1 }, { regionId: "centrale", sector: "Pistes rurales", amountFcfa: 2000 * M, projects: 1 }] },
  { id: "anadeb", name: "Agence nationale d'appui au développement à la base", shortName: "ANADEB", type: "Agence nationale", sectors: ["Éducation", "Santé", "Infrastructures économiques"], regions: ["savanes", "kara", "centrale"], commitmentFcfa: 6_400 * M, activeProjects: 22, focalPoint: "ANADEB – Antenne régionale",
    positions: [{ regionId: "savanes", sector: "Éducation", amountFcfa: 1400 * M, projects: 6 }, { regionId: "kara", sector: "Infrastructures économiques", amountFcfa: 1900 * M, projects: 7 }, { regionId: "centrale", sector: "Santé", amountFcfa: 1600 * M, projects: 5 }, { regionId: "centrale", sector: "Éducation", amountFcfa: 1500 * M, projects: 4 }] },
  { id: "plan", name: "Plan International Togo", shortName: "Plan Int.", type: "ONG internationale", sectors: ["Éducation", "Cohésion sociale"], regions: ["centrale", "kara"], commitmentFcfa: 2_100 * M, activeProjects: 5, focalPoint: "Plan International – Sokodé",
    positions: [{ regionId: "centrale", sector: "Éducation", amountFcfa: 1100 * M, projects: 3 }, { regionId: "kara", sector: "Cohésion sociale", amountFcfa: 1000 * M, projects: 2 }] },
  { id: "ue", name: "Union européenne – Programme Sahel/Golfe de Guinée", shortName: "UE", type: "Bailleur", sectors: ["Cohésion sociale", "Agriculture", "Pistes rurales"], regions: ["savanes"], commitmentFcfa: 11_500 * M, activeProjects: 7, focalPoint: "Délégation UE Togo",
    positions: [{ regionId: "savanes", sector: "Cohésion sociale", amountFcfa: 4100 * M, projects: 3 }, { regionId: "savanes", sector: "Agriculture", amountFcfa: 3900 * M, projects: 2 }, { regionId: "savanes", sector: "Pistes rurales", amountFcfa: 3500 * M, projects: 2 }] },
];
export const partnerById = (id: string) => PARTNERS.find((p) => p.id === id);
