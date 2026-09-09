export const ROLES = ["Administrateur UCP", "Coordonnateur régional", "Chargé de suivi-évaluation", "Point focal communal", "Animateur cantonal", "Agent de terrain", "Partenaire (lecture seule)"] as const;
export type Role = (typeof ROLES)[number];
export type User = { id: string; name: string; email: string; role: Role; scope: string; status: "Actif" | "Invité" | "Suspendu"; lastLogin?: string; mfa: boolean };

export const PERMISSIONS: { module: string; roles: Partial<Record<Role, "Lecture" | "Écriture" | "Validation" | "Admin">> }[] = [
  { module: "Profils villages / cantons", roles: { "Administrateur UCP": "Admin", "Coordonnateur régional": "Validation", "Chargé de suivi-évaluation": "Lecture", "Point focal communal": "Validation", "Animateur cantonal": "Écriture", "Agent de terrain": "Écriture", "Partenaire (lecture seule)": "Lecture" } },
  { module: "Registre des priorités", roles: { "Administrateur UCP": "Admin", "Coordonnateur régional": "Validation", "Chargé de suivi-évaluation": "Lecture", "Point focal communal": "Validation", "Animateur cantonal": "Écriture", "Agent de terrain": "Écriture", "Partenaire (lecture seule)": "Lecture" } },
  { module: "Paquets d'investissement", roles: { "Administrateur UCP": "Admin", "Coordonnateur régional": "Validation", "Chargé de suivi-évaluation": "Écriture", "Point focal communal": "Validation", "Animateur cantonal": "Écriture", "Partenaire (lecture seule)": "Lecture" } },
  { module: "Mécanisme de gestion des plaintes", roles: { "Administrateur UCP": "Admin", "Coordonnateur régional": "Validation", "Chargé de suivi-évaluation": "Lecture", "Point focal communal": "Écriture", "Animateur cantonal": "Écriture", "Agent de terrain": "Écriture" } },
  { module: "Vue partenaires", roles: { "Administrateur UCP": "Admin", "Coordonnateur régional": "Écriture", "Chargé de suivi-évaluation": "Écriture", "Point focal communal": "Lecture", "Partenaire (lecture seule)": "Lecture" } },
  { module: "Gestion des utilisateurs", roles: { "Administrateur UCP": "Admin", "Coordonnateur régional": "Écriture" } },
];

export const USERS: User[] = [
  { id: "u1", name: "Essohanam Tchagnao", email: "e.tchagnao@coso.tg", role: "Administrateur UCP", scope: "National", status: "Actif", lastLogin: "2026-09-09", mfa: true },
  { id: "u2", name: "Yendoubouam Douti", email: "y.douti@coso.tg", role: "Coordonnateur régional", scope: "Région Savanes", status: "Actif", lastLogin: "2026-09-08", mfa: true },
  { id: "u3", name: "Pyabalo Badjona", email: "p.badjona@coso.tg", role: "Coordonnateur régional", scope: "Région Kara", status: "Actif", lastLogin: "2026-09-09", mfa: true },
  { id: "u4", name: "Sadia Boukari", email: "s.boukari@coso.tg", role: "Coordonnateur régional", scope: "Région Centrale", status: "Actif", lastLogin: "2026-09-05", mfa: false },
  { id: "u5", name: "Akouvi Mensah", email: "a.mensah@coso.tg", role: "Chargé de suivi-évaluation", scope: "National", status: "Actif", lastLogin: "2026-09-09", mfa: true },
  { id: "u6", name: "Abalo Kolani", email: "a.kolani@commune-tone1.tg", role: "Point focal communal", scope: "Commune Tône 1", status: "Actif", lastLogin: "2026-09-07", mfa: false },
  { id: "u7", name: "Mazalo Ouro-Djobo", email: "m.ourodjobo@commune-tchaoudjo2.tg", role: "Point focal communal", scope: "Commune Tchaoudjo 2", status: "Actif", lastLogin: "2026-09-02", mfa: false },
  { id: "u8", name: "Kpatcha Nadjombe", email: "k.nadjombe@coso.tg", role: "Animateur cantonal", scope: "Canton de Nano", status: "Actif", lastLogin: "2026-09-08", mfa: false },
  { id: "u9", name: "Tchilalo Pali", email: "t.pali@coso.tg", role: "Animateur cantonal", scope: "Canton de Pya", status: "Actif", lastLogin: "2026-09-06", mfa: false },
  { id: "u10", name: "Nakpane Lamboni", email: "n.lamboni@coso.tg", role: "Agent de terrain", scope: "Préfecture de Kpendjal", status: "Actif", lastLogin: "2026-09-09", mfa: false },
  { id: "u11", name: "Damigou Kombate", email: "d.kombate@coso.tg", role: "Agent de terrain", scope: "Préfecture de l'Oti", status: "Suspendu", lastLogin: "2026-07-14", mfa: false },
  { id: "u12", name: "Bilame Tchédré", email: "b.tchedre@coso.tg", role: "Agent de terrain", scope: "Préfecture de Bassar", status: "Actif", lastLogin: "2026-09-08", mfa: false },
  { id: "u13", name: "Fousséni Aboudou", email: "f.aboudou@coso.tg", role: "Agent de terrain", scope: "Préfecture de Tchamba", status: "Invité", mfa: false },
  { id: "u14", name: "Claire Moreau", email: "c.moreau@afd.fr", role: "Partenaire (lecture seule)", scope: "AFD – Savanes, Kara", status: "Actif", lastLogin: "2026-08-28", mfa: true },
  { id: "u15", name: "Jonas Weber", email: "j.weber@giz.de", role: "Partenaire (lecture seule)", scope: "GIZ – Toutes régions", status: "Invité", mfa: false },
];
