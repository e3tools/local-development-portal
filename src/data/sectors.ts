export const SECTORS = [
  "Eau & assainissement",
  "Éducation",
  "Santé",
  "Pistes rurales",
  "Agriculture",
  "Énergie",
  "Infrastructures économiques",
  "Cohésion sociale",
  "Environnement",
] as const;
export type Sector = (typeof SECTORS)[number];

// Fixed categorical slot per sector (validated palette order, never cycled).
export const SECTOR_COLOR: Record<Sector, string> = {
  "Eau & assainissement": "#2a78d6",
  "Éducation": "#eb6834",
  "Santé": "#1baf7a",
  "Pistes rurales": "#eda100",
  "Agriculture": "#e87ba4",
  "Énergie": "#008300",
  "Infrastructures économiques": "#4a3aa7",
  "Cohésion sociale": "#e34948",
  "Environnement": "#6b6a66", // 9th category folds to neutral
};

export const PRIORITY_TITLES: Record<Sector, string[]> = {
  "Eau & assainissement": ["Forage équipé de pompe à motricité humaine", "Réhabilitation de 2 forages", "Mini-adduction d'eau potable", "Latrines publiques au marché", "Puits pastoral"],
  "Éducation": ["Construction de 3 salles de classe", "Réhabilitation de l'école primaire", "Bloc de latrines scolaires", "Logement pour enseignants", "Cantine scolaire"],
  "Santé": ["Construction d'une USP", "Réhabilitation du dispensaire", "Case de santé communautaire", "Logement infirmier", "Équipement de la maternité"],
  "Pistes rurales": ["Réhabilitation de la piste (8 km)", "Construction d'un dalot", "Radier submersible", "Ouverture de piste vers le marché", "Pont sur le cours d'eau"],
  "Agriculture": ["Magasin de stockage (100 t)", "Aménagement de bas-fond rizicole", "Périmètre maraîcher irrigué", "Unité de transformation du karité", "Parc de vaccination"],
  "Énergie": ["Électrification solaire du centre de santé", "Lampadaires solaires (30 unités)", "Kit solaire pour l'école", "Plateforme multifonctionnelle"],
  "Infrastructures économiques": ["Construction de hangars de marché", "Boutique de fourniture intrants", "Aire d'abattage", "Gare routière aménagée"],
  "Cohésion sociale": ["Centre communautaire polyvalent", "Terrain de sport pour jeunes", "Dialogue intercommunautaire agriculteurs-éleveurs", "Radio communautaire"],
  "Environnement": ["Reboisement communautaire (10 ha)", "Foyers améliorés (200 ménages)", "Protection des berges", "Gestion des déchets"],
};
