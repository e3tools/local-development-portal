import { Card, Kpi, PageHeader, Badge, Btn, StatusBadge, Table } from "@/components/ui";
import { USERS, ROLES, PERMISSIONS } from "@/data/users";
import { fmtDate } from "@/lib/format";
import { countBy } from "@/lib/stats";

export const metadata = { title: "Utilisateurs & rôles" };

export default function Utilisateurs() {
  const byRole = countBy(USERS, (u) => u.role);
  const permTone = { Admin: "critical", Validation: "violet", Écriture: "info", Lecture: "neutral" } as const;
  return (
    <>
      <PageHeader title="Utilisateurs & rôles" subtitle="Gestion des comptes et des habilitations par niveau territorial. Les validations du circuit d'approbation sont réservées aux rôles habilités (CCD, point focal communal, coordination régionale, UCP)."
        action={<div className="flex gap-2"><Btn>Journal d'audit</Btn><Btn primary>+ Inviter un utilisateur</Btn></div>} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Kpi label="Comptes" value={USERS.length} sub={`${USERS.filter((u) => u.status === "Actif").length} actifs · ${USERS.filter((u) => u.status === "Invité").length} invitations en attente`} />
        <Kpi label="Authentification à 2 facteurs" value={`${USERS.filter((u) => u.mfa).length} / ${USERS.length}`} sub="Obligatoire pour les rôles de validation" tone={USERS.filter((u) => !u.mfa && ["Coordonnateur régional", "Administrateur UCP"].includes(u.role)).length ? "warning" : "good"} />
        <Kpi label="Comptes suspendus" value={USERS.filter((u) => u.status === "Suspendu").length} sub="Revue trimestrielle des accès" tone="critical" />
        <Kpi label="Partenaires en lecture" value={byRole["Partenaire (lecture seule)"] ?? 0} sub="Accès à la vue partenaires et aux profils" tone="info" />
      </div>
      <Card title="Comptes utilisateurs" className="mb-4">
        <Table head={["Nom", "E-mail", "Rôle", "Périmètre", "2FA", "Dernière connexion", "Statut", ""]}>
          {USERS.map((u) => (
            <tr key={u.id}>
              <td className="pr-4 font-medium">{u.name}</td>
              <td className="pr-4 text-ink-2 text-xs">{u.email}</td>
              <td className="pr-4"><Badge tone={u.role === "Administrateur UCP" ? "critical" : u.role.startsWith("Partenaire") ? "neutral" : u.role === "Coordonnateur régional" ? "violet" : "info"} icon={false}>{u.role}</Badge></td>
              <td className="pr-4 text-ink-2">{u.scope}</td>
              <td className="pr-4">{u.mfa ? <span className="text-green-700">Activée</span> : <span className="text-amber-700">Non</span>}</td>
              <td className="pr-4 text-ink-2">{fmtDate(u.lastLogin)}</td>
              <td className="pr-4"><StatusBadge status={u.status} /></td>
              <td className="pr-0 text-right"><button className="text-xs text-brand-700 hover:underline">Modifier</button></td>
            </tr>
          ))}
        </Table>
      </Card>
      <Card title="Matrice des habilitations" subtitle="Droits par module et par rôle">
        <div className="overflow-x-auto -mx-5 px-5">
          <table className="w-full text-xs">
            <thead><tr className="text-left text-ink-3 border-b border-line"><th className="py-2 pr-3 font-medium">Module</th>{ROLES.map((r) => <th key={r} className="py-2 px-2 font-medium">{r}<div className="text-[10px] font-normal">{byRole[r] ?? 0} compte(s)</div></th>)}</tr></thead>
            <tbody className="divide-y divide-line">
              {PERMISSIONS.map((p) => (
                <tr key={p.module}>
                  <td className="py-2 pr-3 font-medium whitespace-nowrap">{p.module}</td>
                  {ROLES.map((r) => { const v = p.roles[r]; return <td key={r} className="py-2 px-2">{v ? <Badge tone={permTone[v]} icon={false}>{v}</Badge> : <span className="text-ink-3">—</span>}</td>; })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
