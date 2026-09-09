import { createRng } from "@/lib/rng";
import { addDays } from "@/lib/format";
import { VILLAGES, villageById } from "./geo";
import { INVESTMENTS } from "./investments";
import { prioritiesOfVillage } from "./priorities";
import type { Sector } from "./sectors";

// Sample imagery. The files under public/img are procedurally generated
// illustrations (see scripts/generate-sample-images.mjs) standing in for the
// field photos a real deployment stores on S3 — this build ships fictional data
// only, so it carries no real photographs of real communities.

/** Mirrors the `process_moment` vocabulary of the Attachment model. */
export const PHOTO_MOMENTS = ["Processus communautaire", "Travaux en cours", "Ouvrage achevé"] as const;
export type PhotoMoment = (typeof PHOTO_MOMENTS)[number];

export type Photo = {
  id: string;
  src: string;
  alt: string;
  caption: string;
  moment: PhotoMoment;
  takenAt: string;
  credit: string;
};

const SECTOR_SLUG: Record<Sector, string> = {
  "Eau & assainissement": "eau",
  "Éducation": "education",
  "Santé": "sante",
  "Pistes rurales": "pistes",
  "Agriculture": "agriculture",
  "Énergie": "energie",
  "Infrastructures économiques": "economie",
  "Cohésion sociale": "cohesion",
  "Environnement": "environnement",
};
const SECTOR_VARIANTS = 3;
const VILLAGE_SCENES = 8;

const sectorSrc = (sector: Sector, variant: number) => `/img/secteurs/${SECTOR_SLUG[sector]}-${(variant % SECTOR_VARIANTS) + 1}.svg`;
const villageSrc = (variant: number) => `/img/villages/village-${(variant % VILLAGE_SCENES) + 1}.svg`;

const VILLAGE_CAPTIONS = [
  (v: string) => `Vue d'ensemble de ${v}`,
  (v: string) => `Assemblée villageoise de ${v}`,
  (v: string) => `Concession et greniers, ${v}`,
  (v: string) => `Restitution du diagnostic participatif à ${v}`,
  (v: string) => `Focus groupe femmes, ${v}`,
];
const WORK_CAPTIONS = ["Démarrage du chantier", "Travaux en cours", "Point d'avancement mensuel", "Chantier HIMO en activité", "Visite de supervision"];
const DONE_CAPTIONS = ["Ouvrage réceptionné", "Ouvrage achevé et mis en service", "Réception provisoire des travaux", "Première utilisation par la communauté"];
const COMMUNITY_CAPTIONS = ["Site retenu avant travaux", "Séance de validation communautaire", "Identification du site avec le CVD", "Levée topographique du site"];
const CREDITS = ["Agent COSO – Tône", "Agent COSO – Kozah", "Agent COSO – Tchaoudjo", "Agent COSO – Oti", "Agent COSO – Bassar", "Agent COSO – Tchamba", "Agent COSO – Kpendjal", "Agent COSO – Kéran", "Point focal communal", "Coordination régionale"];

const rng = createRng(2026);

// --- Village galleries: the profile shots plus the top priority's context ----

const villagePhotos = new Map<string, Photo[]>();
for (const v of VILLAGES) {
  const photos: Photo[] = [];
  const base = rng.int(0, VILLAGE_SCENES - 1);
  const shots = rng.int(3, 4);
  for (let i = 0; i < shots; i++) {
    const caption = VILLAGE_CAPTIONS[(base + i) % VILLAGE_CAPTIONS.length](v.name);
    photos.push({
      id: `ph-${v.id}-${i + 1}`,
      src: i === 0 ? villageSrc(base) : i === 1 ? villageSrc(base + 3) : sectorSrc(prioritiesOfVillage(v.id)[i - 2]?.sector ?? "Eau & assainissement", base + i),
      alt: `${caption} — illustration de démonstration`,
      caption,
      moment: "Processus communautaire",
      takenAt: addDays(v.profiledAt, rng.int(-20, 40)),
      credit: rng.pick(CREDITS),
    });
  }
  villagePhotos.set(v.id, photos);
}

// --- Sub-project galleries: one album per step actually reached -------------

const investmentPhotos = new Map<string, Photo[]>();
for (const inv of INVESTMENTS) {
  const v = villageById(inv.villageId);
  const variant = rng.int(0, SECTOR_VARIANTS - 1);
  const moments: PhotoMoment[] =
    inv.status === "Achevé"
      ? ["Processus communautaire", "Travaux en cours", "Ouvrage achevé"]
      : inv.status === "En exécution"
        ? ["Processus communautaire", "Travaux en cours"]
        : ["Processus communautaire"];
  const photos: Photo[] = moments.map((moment, i) => {
    const caption =
      moment === "Ouvrage achevé" ? rng.pick(DONE_CAPTIONS) : moment === "Travaux en cours" ? rng.pick(WORK_CAPTIONS) : rng.pick(COMMUNITY_CAPTIONS);
    return {
      id: `ph-${inv.id}-${i + 1}`,
      src: moment === "Processus communautaire" ? villageSrc(variant + i + 2) : sectorSrc(inv.sector, variant + i),
      alt: `${inv.title} à ${v?.name ?? ""} — ${caption.toLowerCase()} (illustration de démonstration)`,
      caption,
      moment,
      takenAt: addDays(inv.startDate ?? inv.submittedAt, i * rng.int(45, 120)),
      credit: rng.pick(CREDITS),
    };
  });
  // Executing works get one extra progress shot so galleries are not all pairs.
  if (inv.status === "En exécution" && rng.chance(0.5)) {
    photos.push({
      id: `ph-${inv.id}-${photos.length + 1}`,
      src: sectorSrc(inv.sector, variant + 2),
      alt: `${inv.title} à ${v?.name ?? ""} — avancement des travaux (illustration de démonstration)`,
      caption: rng.pick(WORK_CAPTIONS),
      moment: "Travaux en cours",
      takenAt: addDays(inv.startDate ?? inv.submittedAt, rng.int(120, 220)),
      credit: rng.pick(CREDITS),
    });
  }
  investmentPhotos.set(inv.id, photos);
}

export const photosOfVillage = (villageId: string): Photo[] => villagePhotos.get(villageId) ?? [];
export const photosOfInvestment = (investmentId: string): Photo[] => investmentPhotos.get(investmentId) ?? [];

/** Cover shot for a sub-project — the most advanced photo on file. */
export const coverOfInvestment = (investmentId: string): Photo | undefined => {
  const photos = investmentPhotos.get(investmentId);
  return photos?.[photos.length - 1];
};

export const PHOTO_COUNT = [...villagePhotos.values(), ...investmentPhotos.values()].reduce((s, p) => s + p.length, 0);
