export type Resource = {
  id: string;
  title: string;
  type: "Module de formation" | "Guide pratique" | "Vidéo" | "Fiche outil" | "Quiz";
  audience: string;
  durationMin: number;
  languages: string[];
  completions: number;
  target: number;
  offline: boolean;
  updatedAt: string;
};
export const RESOURCES: Resource[] = [
  { id: "r1", title: "Réaliser un profil village avec l'application mobile", type: "Module de formation", audience: "Agents de terrain", durationMin: 45, languages: ["Français", "Kabyè", "Moba"], completions: 61, target: 72, offline: true, updatedAt: "2026-05-12" },
  { id: "r2", title: "Animer une assemblée villageoise de priorisation", type: "Guide pratique", audience: "Animateurs cantonaux, CVD", durationMin: 30, languages: ["Français", "Tem", "Moba"], completions: 118, target: 160, offline: true, updatedAt: "2026-03-02" },
  { id: "r3", title: "Rôle et fonctionnement du CVD", type: "Vidéo", audience: "Membres CVD", durationMin: 12, languages: ["Français", "Kabyè", "Moba", "Tem", "Ewe"], completions: 402, target: 520, offline: true, updatedAt: "2026-01-20" },
  { id: "r4", title: "Circuit d'approbation d'un paquet d'investissement", type: "Module de formation", audience: "Points focaux, CCD", durationMin: 60, languages: ["Français"], completions: 44, target: 58, offline: false, updatedAt: "2026-06-30" },
  { id: "r5", title: "Recevoir et enregistrer une plainte (MGP)", type: "Fiche outil", audience: "Comités GRM", durationMin: 15, languages: ["Français", "Kabyè", "Moba", "Tem"], completions: 233, target: 260, offline: true, updatedAt: "2026-04-15" },
  { id: "r6", title: "Protocole de réponse aux VBG/EAS/HS", type: "Module de formation", audience: "Tous les acteurs", durationMin: 90, languages: ["Français"], completions: 187, target: 330, offline: false, updatedAt: "2026-02-08" },
  { id: "r7", title: "Passation de marchés communautaires", type: "Guide pratique", audience: "CVD, CCD", durationMin: 40, languages: ["Français", "Kabyè"], completions: 76, target: 160, offline: true, updatedAt: "2025-11-04" },
  { id: "r8", title: "Suivi de chantier : check-list qualité", type: "Fiche outil", audience: "Agents de terrain, CVD", durationMin: 20, languages: ["Français", "Tem", "Moba"], completions: 140, target: 232, offline: true, updatedAt: "2026-07-22" },
  { id: "r9", title: "Gestion des travaux HIMO et paie des ouvriers", type: "Vidéo", audience: "CVD, entreprises", durationMin: 18, languages: ["Français", "Moba", "Kabyè"], completions: 95, target: 150, offline: true, updatedAt: "2026-05-30" },
  { id: "r10", title: "Quiz : sauvegardes environnementales et sociales", type: "Quiz", audience: "Agents de terrain", durationMin: 10, languages: ["Français"], completions: 58, target: 72, offline: false, updatedAt: "2026-08-11" },
  { id: "r11", title: "Prévention des conflits agriculteurs-éleveurs", type: "Module de formation", audience: "CCD, chefs traditionnels", durationMin: 75, languages: ["Français", "Moba", "Peul"], completions: 39, target: 96, offline: true, updatedAt: "2026-06-05" },
  { id: "r12", title: "Entretien et maintenance des forages", type: "Guide pratique", audience: "Comités eau", durationMin: 35, languages: ["Français", "Kabyè", "Moba", "Tem"], completions: 84, target: 140, offline: true, updatedAt: "2026-03-18" },
];
