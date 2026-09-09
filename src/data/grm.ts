import { createRng } from "@/lib/rng";
import { addDays, daysBetween, TODAY } from "@/lib/format";
import { VILLAGES } from "./geo";
import { INVESTMENTS } from "./investments";

export const GRM_CATEGORIES = ["Accès à l'information", "Sélection des bénéficiaires", "Qualité des ouvrages", "Conflit foncier", "Paiement HIMO", "Comportement du personnel", "Violence basée sur le genre", "Environnement & nuisances"] as const;
export type GrmCategory = (typeof GRM_CATEGORIES)[number];
export const GRM_CHANNELS = ["Numéro vert", "Boîte à plaintes", "Comité GRM villageois", "Application mobile", "En personne (agent)", "WhatsApp"] as const;
export const GRM_STATUSES = ["Reçue", "Recevabilité", "En traitement", "Résolue", "Escaladée", "Clôturée"] as const;
export type GrmStatus = (typeof GRM_STATUSES)[number];
export const GRM_LEVELS = ["Niveau 1 – Village", "Niveau 2 – Canton/Commune", "Niveau 3 – Région", "Niveau 4 – UCP"] as const;

export type Grievance = {
  id: string;
  code: string;
  villageId: string;
  investmentId?: string;
  category: GrmCategory;
  channel: (typeof GRM_CHANNELS)[number];
  status: GrmStatus;
  level: (typeof GRM_LEVELS)[number];
  severity: "Faible" | "Moyenne" | "Élevée";
  receivedAt: string;
  resolvedAt?: string;
  daysOpen: number;
  slaDays: number;
  summary: string;
  assignedTo: string;
  sensitive: boolean;
  complainant: "Femme" | "Homme" | "Groupe" | "Anonyme";
  satisfaction?: 1 | 2 | 3 | 4 | 5;
};

const rng = createRng(99);
const SUMMARIES: Record<GrmCategory, string[]> = {
  "Accès à l'information": ["Les critères de sélection des sous-projets n'ont pas été affichés au village.", "Aucune restitution après le diagnostic participatif."],
  "Sélection des bénéficiaires": ["Des ménages vulnérables ont été omis de la liste HIMO.", "La liste des bénéficiaires favorise un seul quartier."],
  "Qualité des ouvrages": ["Fissures constatées sur les murs de la salle de classe livrée.", "Le forage débite peu d'eau depuis la réception.", "La latrine n'a pas de porte ni de ventilation."],
  "Conflit foncier": ["Contestation du site retenu pour le magasin de stockage.", "Le propriétaire coutumier réclame une compensation."],
  "Paiement HIMO": ["Retard de 2 mois sur le paiement des travailleurs HIMO.", "Montant payé inférieur au montant annoncé."],
  "Comportement du personnel": ["Propos irrespectueux de l'agent lors de l'assemblée.", "Le chef de chantier refuse de dialoguer avec le CVD."],
  "Violence basée sur le genre": ["Plainte sensible – traitée via le protocole VBG (détails confidentiels)."],
  "Environnement & nuisances": ["Déchets de chantier abandonnés près du point d'eau.", "Abattage d'arbres non prévu sur l'emprise de la piste."],
};
const ASSIGNEES = ["Comité GRM – village", "Point focal GRM – commune", "Spécialiste sauvegardes – région", "Spécialiste VBG – UCP", "Cellule GRM – UCP"];

export const GRIEVANCES: Grievance[] = [];
for (let i = 1; i <= 96; i++) {
  const village = rng.pick(VILLAGES);
  const category = rng.pick(GRM_CATEGORIES);
  const sensitive = category === "Violence basée sur le genre";
  const status = rng.pick(sensitive ? ["En traitement", "Escaladée", "Clôturée"] : ["Reçue", "Recevabilité", "En traitement", "En traitement", "Résolue", "Résolue", "Résolue", "Escaladée", "Clôturée", "Clôturée"]) as GrmStatus;
  const closed = status === "Résolue" || status === "Clôturée";
  // Open complaints are recent; closed ones spread over the project history.
  const receivedAt = closed ? addDays("2025-06-01", rng.int(0, 420)) : addDays(TODAY, -rng.int(1, 60));
  const resolvedAt = closed ? addDays(receivedAt, rng.int(3, 45)) : undefined;
  const level: Grievance["level"] = sensitive ? "Niveau 4 – UCP" : status === "Escaladée" ? rng.pick(["Niveau 2 – Canton/Commune", "Niveau 3 – Région"] as const) : rng.pick(["Niveau 1 – Village", "Niveau 1 – Village", "Niveau 2 – Canton/Commune"] as const);
  const linked = INVESTMENTS.filter((inv) => inv.villageId === village.id);
  const severity: Grievance["severity"] = sensitive ? "Élevée" : rng.pick(["Faible", "Moyenne", "Moyenne", "Élevée"] as const);
  GRIEVANCES.push({
    id: `grm-${i}`,
    code: `PL-${String(i).padStart(4, "0")}`,
    villageId: village.id,
    investmentId: linked.length && rng.chance(0.6) ? rng.pick(linked).id : undefined,
    category,
    channel: rng.pick(GRM_CHANNELS),
    status,
    level,
    severity,
    receivedAt,
    resolvedAt,
    daysOpen: daysBetween(receivedAt, resolvedAt ?? TODAY),
    slaDays: severity === "Élevée" ? 10 : severity === "Moyenne" ? 20 : 30,
    summary: rng.pick(SUMMARIES[category]),
    assignedTo: sensitive ? "Spécialiste VBG – UCP" : rng.pick(ASSIGNEES.slice(0, 3).concat("Cellule GRM – UCP")),
    sensitive,
    complainant: sensitive ? "Anonyme" : rng.pick(["Femme", "Homme", "Homme", "Groupe", "Anonyme"]),
    satisfaction: closed && !sensitive ? (rng.int(2, 5) as 1 | 2 | 3 | 4 | 5) : undefined,
  });
}
GRIEVANCES.sort((a, b) => (a.receivedAt < b.receivedAt ? 1 : -1));
