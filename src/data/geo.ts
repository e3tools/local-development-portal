import { createRng } from "@/lib/rng";
import { FIRST_NAMES, LAST_NAMES, VILLAGE_PREFIX, VILLAGE_SUFFIX } from "./names";

export type Region = { id: string; name: string; chefLieu: string; ethnicGroups: string[]; activities: string[] };
export type Prefecture = { id: string; name: string; regionId: string; chefLieu: string };
export type Canton = {
  id: string;
  name: string;
  prefectureId: string;
  regionId: string;
  chefCanton: string;
  ccdPresident: string;
  ccdCreatedYear: number;
  ccdMembers: number;
  ccdWomen: number;
  hasPdc: boolean; // Plan de développement cantonal
  pdcYear?: number;
};
export type RoadAccess = "Permanente" | "Saisonnière" | "Difficile";
export type Village = {
  id: string;
  name: string;
  cantonId: string;
  prefectureId: string;
  regionId: string;
  population: number;
  households: number;
  womenPct: number;
  youthPct: number;
  distanceKm: number;
  ethnicGroups: string[];
  activities: string[];
  infra: {
    primarySchool: boolean;
    secondarySchool: boolean;
    healthCenter: boolean;
    waterPoints: number;
    functionalWaterPoints: number;
    market: boolean;
    electricity: boolean;
    mobileCoverage: boolean;
    roadAccess: RoadAccess;
  };
  cvd: { president: string; secretary: string; members: number; women: number; youth: number; createdYear: number };
  vulnerabilityScore: number; // 0-100 (higher = more vulnerable)
  displacedHouseholds: number;
  profiledAt: string;
  profiledBy: string;
  gps: { lat: number; lng: number };
};

export const REGIONS: Region[] = [
  { id: "savanes", name: "Savanes", chefLieu: "Dapaong", ethnicGroups: ["Moba", "Gourma", "Tchokossi", "Ngam-Ngam", "Peul"], activities: ["Agriculture (mil, sorgho, maïs)", "Élevage", "Coton", "Commerce transfrontalier", "Maraîchage"] },
  { id: "kara", name: "Kara", chefLieu: "Kara", ethnicGroups: ["Kabyè", "Lamba", "Nawdba", "Tamberma", "Bassar", "Konkomba"], activities: ["Agriculture (igname, maïs)", "Élevage", "Artisanat", "Commerce", "Karité"] },
  { id: "centrale", name: "Centrale", chefLieu: "Sokodé", ethnicGroups: ["Tem", "Kabyè", "Ana-Ifè", "Tchamba", "Peul"], activities: ["Agriculture (maïs, soja)", "Élevage", "Commerce", "Riziculture", "Karité"] },
];

const PREF_RAW: [string, string, string, string][] = [
  ["tone", "Tône", "savanes", "Dapaong"],
  ["cinkasse", "Cinkassé", "savanes", "Cinkassé"],
  ["kpendjal", "Kpendjal", "savanes", "Mandouri"],
  ["oti", "Oti", "savanes", "Sansanné-Mango"],
  ["tandjouare", "Tandjouaré", "savanes", "Tandjouaré"],
  ["kozah", "Kozah", "kara", "Kara"],
  ["binah", "Binah", "kara", "Pagouda"],
  ["doufelgou", "Doufelgou", "kara", "Niamtougou"],
  ["keran", "Kéran", "kara", "Kandé"],
  ["bassar", "Bassar", "kara", "Bassar"],
  ["dankpen", "Dankpen", "kara", "Guérin-Kouka"],
  ["tchaoudjo", "Tchaoudjo", "centrale", "Sokodé"],
  ["tchamba", "Tchamba", "centrale", "Tchamba"],
  ["sotouboua", "Sotouboua", "centrale", "Sotouboua"],
  ["blitta", "Blitta", "centrale", "Blitta"],
  ["mo", "Mô", "centrale", "Djarkpanga"],
];
export const PREFECTURES: Prefecture[] = PREF_RAW.map(([id, name, regionId, chefLieu]) => ({ id, name, regionId, chefLieu }));

const CANTON_RAW: Record<string, string[]> = {
  tone: ["Nano", "Naki-Est", "Korbongou", "Lotogou", "Tami", "Bogou"],
  cinkasse: ["Timbou", "Biankouri", "Gouloungoussi"],
  kpendjal: ["Mandouri", "Borgou", "Koundjoaré", "Ogaro"],
  oti: ["Barkoissi", "Galangashi", "Koumongou", "Takpamba"],
  tandjouare: ["Bombouaka", "Nandoga", "Goundoga", "Lokpano"],
  kozah: ["Pya", "Lassa", "Kouméa", "Landa", "Soumdina", "Sarakawa"],
  binah: ["Kétao", "Boufalé", "Sirka", "Solla"],
  doufelgou: ["Défalé", "Siou", "Koka", "Baga"],
  keran: ["Nadoba", "Atalote", "Hélota", "Natchamba"],
  bassar: ["Kabou", "Bangéli", "Bitchabé", "Dimori"],
  dankpen: ["Nampoch", "Namon", "Natchitikpi"],
  tchaoudjo: ["Kparatao", "Kadambara", "Kémini", "Lama-Tessi", "Tchalo"],
  tchamba: ["Kaboli", "Koussountou", "Balanka", "Goubi", "Larini"],
  sotouboua: ["Adjengré", "Tchébébé", "Fazao", "Kaniamboua"],
  blitta: ["Yélivo", "Pagala", "Langabou", "Yégué"],
  mo: ["Boulohou", "Tindjassi", "Saïbou"],
};

const rng = createRng(20260909);
const personName = () => `${rng.pick(FIRST_NAMES)} ${rng.pick(LAST_NAMES)}`;
const slug = (s: string) =>
  s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

export const CANTONS: Canton[] = [];
for (const pref of PREFECTURES) {
  for (const name of CANTON_RAW[pref.id]) {
    const hasPdc = rng.chance(0.7);
    CANTONS.push({
      id: `${pref.id}-${slug(name)}`,
      name,
      prefectureId: pref.id,
      regionId: pref.regionId,
      chefCanton: personName(),
      ccdPresident: personName(),
      ccdCreatedYear: rng.int(2021, 2024),
      ccdMembers: rng.int(9, 15),
      ccdWomen: rng.int(3, 6),
      hasPdc,
      pdcYear: hasPdc ? rng.int(2023, 2025) : undefined,
    });
  }
}

const REGION_CENTER: Record<string, [number, number]> = { savanes: [10.62, 0.35], kara: [9.65, 1.05], centrale: [8.85, 1.0] };
const AGENTS = ["Agent COSO – Tône", "Agent COSO – Kozah", "Agent COSO – Tchaoudjo", "Agent COSO – Oti", "Agent COSO – Bassar", "Agent COSO – Tchamba", "Agent COSO – Kpendjal", "Agent COSO – Kéran"];

const usedNames = new Set<string>();
function villageName(): string {
  for (;;) {
    const n = rng.pick(VILLAGE_PREFIX) + rng.pick(VILLAGE_SUFFIX);
    if (!usedNames.has(n)) {
      usedNames.add(n);
      return n;
    }
  }
}

export const VILLAGES: Village[] = [];
for (const canton of CANTONS) {
  const region = REGIONS.find((r) => r.id === canton.regionId)!;
  const count = rng.int(2, 4);
  for (let i = 0; i < count; i++) {
    const population = rng.int(350, 4200);
    const households = Math.round(population / rng.int(5, 8));
    const waterPoints = rng.int(0, 6);
    const [lat, lng] = REGION_CENTER[canton.regionId];
    const name = villageName();
    const displaced = canton.regionId === "savanes" ? rng.int(0, 60) : rng.int(0, 8);
    const infra = {
      primarySchool: rng.chance(0.75),
      secondarySchool: rng.chance(0.25),
      healthCenter: rng.chance(0.35),
      waterPoints,
      functionalWaterPoints: waterPoints ? rng.int(0, waterPoints) : 0,
      market: rng.chance(0.3),
      electricity: rng.chance(0.3),
      mobileCoverage: rng.chance(0.8),
      roadAccess: rng.pick(["Permanente", "Saisonnière", "Saisonnière", "Difficile"] as const),
    };
    let vuln = 40;
    if (!infra.primarySchool) vuln += 10;
    if (!infra.healthCenter) vuln += 8;
    if (infra.functionalWaterPoints === 0) vuln += 15;
    if (!infra.electricity) vuln += 5;
    if (infra.roadAccess === "Difficile") vuln += 10;
    if (displaced > 20) vuln += 10;
    vuln += rng.int(-8, 8);
    const members = rng.int(7, 13);
    VILLAGES.push({
      id: `${canton.id}-${slug(name)}`,
      name,
      cantonId: canton.id,
      prefectureId: canton.prefectureId,
      regionId: canton.regionId,
      population,
      households,
      womenPct: rng.int(48, 54),
      youthPct: rng.int(38, 52),
      distanceKm: rng.int(2, 38),
      ethnicGroups: rng.sample(region.ethnicGroups, rng.int(1, 3)),
      activities: rng.sample(region.activities, rng.int(2, 4)),
      infra,
      cvd: { president: personName(), secretary: personName(), members, women: rng.int(2, Math.min(6, members - 2)), youth: rng.int(1, 4), createdYear: rng.int(2021, 2024) },
      vulnerabilityScore: Math.max(10, Math.min(98, vuln)),
      displacedHouseholds: displaced,
      profiledAt: `2025-${String(rng.int(1, 12)).padStart(2, "0")}-${String(rng.int(1, 28)).padStart(2, "0")}`,
      profiledBy: rng.pick(AGENTS),
      gps: { lat: +(lat + (rng.next() - 0.5) * 0.9).toFixed(4), lng: +(lng + (rng.next() - 0.5) * 0.9).toFixed(4) },
    });
  }
}

// Lookups
export const regionById = (id: string) => REGIONS.find((r) => r.id === id);
export const prefectureById = (id: string) => PREFECTURES.find((p) => p.id === id);
export const cantonById = (id: string) => CANTONS.find((c) => c.id === id);
export const villageById = (id: string) => VILLAGES.find((v) => v.id === id);
export const villagesOfCanton = (cantonId: string) => VILLAGES.filter((v) => v.cantonId === cantonId);
export const cantonsOfPrefecture = (prefId: string) => CANTONS.filter((c) => c.prefectureId === prefId);
export const prefecturesOfRegion = (regionId: string) => PREFECTURES.filter((p) => p.regionId === regionId);
export const villagesOfRegion = (regionId: string) => VILLAGES.filter((v) => v.regionId === regionId);
export const villageLabel = (v: Village) => {
  const c = cantonById(v.cantonId)!;
  const p = prefectureById(c.prefectureId)!;
  return `${v.name} · ${c.name} · ${p.name}`;
};
