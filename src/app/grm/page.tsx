import { Card, Kpi, PageHeader, Btn } from "@/components/ui";
import { Distribution, HBarChart } from "@/components/charts";
import { GrmTable, type GrmRow } from "@/components/grm-table";
import { GRIEVANCES, GRM_CATEGORIES, GRM_CHANNELS } from "@/data/grm";
import { REGIONS, villageById, cantonById, regionById } from "@/data/geo";
import { investmentById } from "@/data/investments";
import { fmtInt, fmtPct } from "@/lib/format";
import { countBy } from "@/lib/stats";

export const metadata = { title: "Mécanisme de gestion des plaintes" };

export default function Grm() {
  const rows: GrmRow[] = GRIEVANCES.map((g) => {
    const v = villageById(g.villageId)!;
    const inv = g.investmentId ? investmentById(g.investmentId) : undefined;
    return { id: g.id, code: g.code, category: g.category, channel: g.channel, status: g.status, level: g.level, severity: g.severity, receivedAt: g.receivedAt, daysOpen: g.daysOpen, slaDays: g.slaDays, summary: g.summary, assignedTo: g.assignedTo, sensitive: g.sensitive, complainant: g.complainant, village: v.name, villageId: v.id, canton: cantonById(v.cantonId)!.name, region: regionById(v.regionId)!.name, investmentCode: inv?.code, investmentId: inv?.id, satisfaction: g.satisfaction };
  });
  const open = GRIEVANCES.filter((g) => !["Résolue", "Clôturée"].includes(g.status));
  const closed = GRIEVANCES.filter((g) => ["Résolue", "Clôturée"].includes(g.status));
  const late = open.filter((g) => g.daysOpen > g.slaDays);
  const avgDays = Math.round(closed.reduce((s, g) => s + g.daysOpen, 0) / closed.length);
  const byCat = countBy(GRIEVANCES, (g) => g.category);
  const byChan = countBy(GRIEVANCES, (g) => g.channel);
  const byStatus = countBy(GRIEVANCES, (g) => g.status);
  const sat = closed.filter((g) => g.satisfaction);
  const women = GRIEVANCES.filter((g) => g.complainant === "Femme").length;
  return (
    <>
      <PageHeader title="Mécanisme de gestion des plaintes (MGP)" subtitle="Tableau de bord des plaintes et réclamations : réception multicanale, recevabilité, traitement par niveau (village, canton/commune, région, UCP) et suivi des délais. Les plaintes sensibles (VBG/EAS/HS) suivent un protocole confidentiel."
        action={<div className="flex gap-2"><Btn>Rapport mensuel</Btn><Btn primary>+ Enregistrer une plainte</Btn></div>} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Kpi label="Plaintes reçues" value={fmtInt(GRIEVANCES.length)} sub={`${fmtPct((women / GRIEVANCES.length) * 100)} déposées par des femmes`} />
        <Kpi label="Ouvertes" value={fmtInt(open.length)} sub={`${late.length} hors délai · ${open.filter((g) => g.status === "Escaladée").length} escaladées`} tone={late.length > 10 ? "critical" : "warning"} />
        <Kpi label="Taux de résolution" value={fmtPct((closed.length / GRIEVANCES.length) * 100)} sub={`Délai moyen de traitement ${avgDays} jours`} tone="good" />
        <Kpi label="Satisfaction" value={sat.length ? `${(sat.reduce((s, g) => s + (g.satisfaction ?? 0), 0) / sat.length).toFixed(1).replace(".", ",")} / 5` : "—"} sub={`${sat.length} plaignants enquêtés · ${GRIEVANCES.filter((g) => g.sensitive).length} plaintes sensibles`} tone="info" />
      </div>
      <div className="grid lg:grid-cols-3 gap-4 mb-4">
        <Card title="Par catégorie">
          <HBarChart data={GRM_CATEGORIES.map((c) => ({ label: c, value: byCat[c] ?? 0 })).sort((a, b) => b.value - a.value)} color="#eb6834" />
        </Card>
        <Card title="Par canal de réception">
          <HBarChart data={GRM_CHANNELS.map((c) => ({ label: c, value: byChan[c] ?? 0 })).sort((a, b) => b.value - a.value)} color="#2a78d6" />
        </Card>
        <Card title="Par statut">
          <Distribution parts={[
            { label: "Reçue", value: byStatus["Reçue"] ?? 0, color: "#9ec5f4" },
            { label: "Recevabilité", value: byStatus["Recevabilité"] ?? 0, color: "#5598e7" },
            { label: "En traitement", value: byStatus["En traitement"] ?? 0, color: "#eda100" },
            { label: "Escaladée", value: byStatus["Escaladée"] ?? 0, color: "#e34948" },
            { label: "Résolue", value: byStatus["Résolue"] ?? 0, color: "#1baf7a" },
            { label: "Clôturée", value: byStatus["Clôturée"] ?? 0, color: "#008300" },
          ]} />
          <div className="mt-5 text-xs font-medium text-ink-2 mb-2">Par région (ouvertes)</div>
          <HBarChart data={REGIONS.map((r) => ({ label: r.name, value: open.filter((g) => villageById(g.villageId)!.regionId === r.id).length }))} color="#e34948" />
        </Card>
      </div>
      <Card>
        <GrmTable rows={rows} regions={REGIONS.map((r) => r.name)} />
      </Card>
    </>
  );
}
