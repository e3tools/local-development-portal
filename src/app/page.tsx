import Link from "next/link";
import { Card, Kpi, PageHeader, StatusBadge, Table } from "@/components/ui";
import { Distribution, HBarChart, Sparkline } from "@/components/charts";
import { REGIONS, VILLAGES, CANTONS, PREFECTURES, villageById, cantonById } from "@/data/geo";
import { PRIORITIES } from "@/data/priorities";
import { INVESTMENTS } from "@/data/investments";
import { GRIEVANCES } from "@/data/grm";
import { SECTORS, SECTOR_COLOR } from "@/data/sectors";
import { fmtInt, fmtMFcfa, fmtPct, fmtDate } from "@/lib/format";
import { countBy, sumBy } from "@/lib/stats";

export default function Dashboard() {
  const population = sumBy(VILLAGES, (v) => v.population);
  const engaged = INVESTMENTS.filter((i) => ["Approuvé", "En exécution", "Achevé"].includes(i.status));
  const budget = sumBy(engaged, (i) => i.budgetFcfa);
  const disbursed = sumBy(engaged, (i) => i.disbursedFcfa);
  const openGrm = GRIEVANCES.filter((g) => !["Résolue", "Clôturée"].includes(g.status));
  const closedGrm = GRIEVANCES.filter((g) => ["Résolue", "Clôturée"].includes(g.status));
  const bySector = countBy(PRIORITIES, (p) => p.sector);
  const invStatus = countBy(INVESTMENTS, (i) => i.status);
  const months = Array.from({ length: 12 }, (_, i) => { const d = new Date(Date.UTC(2025, 9 + i, 1)); return d.toISOString().slice(0, 7); });
  const grmByMonth = months.map((m) => GRIEVANCES.filter((g) => g.receivedAt.startsWith(m)).length);
  const recent = [...INVESTMENTS].sort((a, b) => (a.submittedAt < b.submittedAt ? 1 : -1)).slice(0, 6);

  return (
    <>
      <PageHeader title="Tableau de bord" subtitle="Vue consolidée du portail : profils territoriaux, priorités locales, paquets d'investissement, plaintes et positions des partenaires dans les régions Savanes, Kara et Centrale." />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Kpi label="Villages profilés" value={fmtInt(VILLAGES.length)} sub={`${CANTONS.length} cantons · ${PREFECTURES.length} préfectures`} />
        <Kpi label="Population couverte" value={fmtInt(population)} sub={`${fmtInt(sumBy(VILLAGES, (v) => v.households))} ménages`} />
        <Kpi label="Priorités enregistrées" value={fmtInt(PRIORITIES.length)} sub={`${fmtInt(PRIORITIES.filter((p) => p.status === "Financée").length)} financées`} tone="violet" />
        <Kpi label="Sous-projets" value={fmtInt(INVESTMENTS.length)} sub={`${INVESTMENTS.filter((i) => i.status === "En exécution").length} en exécution · ${INVESTMENTS.filter((i) => i.status === "Achevé").length} achevés`} tone="info" />
        <Kpi label="Budget engagé" value={fmtMFcfa(budget)} sub={`${engaged.length} sous-projets approuvés ou plus`} tone="good" />
        <Kpi label="Décaissé" value={fmtMFcfa(disbursed)} sub={`${fmtPct((disbursed / budget) * 100)} du budget engagé`} tone="good" />
        <Kpi label="Plaintes ouvertes" value={fmtInt(openGrm.length)} sub={`${openGrm.filter((g) => g.daysOpen > g.slaDays).length} hors délai`} tone={openGrm.filter((g) => g.daysOpen > g.slaDays).length > 10 ? "critical" : "warning"} />
        <Kpi label="Taux de résolution" value={fmtPct((closedGrm.length / GRIEVANCES.length) * 100)} sub={`${closedGrm.length} / ${GRIEVANCES.length} plaintes`} tone="good" />
      </div>

      <div className="grid lg:grid-cols-3 gap-4 mb-4">
        <Card title="Priorités locales par secteur" subtitle="Toutes priorités enregistrées (rang 1 à 3)" className="lg:col-span-1">
          <HBarChart data={SECTORS.map((s) => ({ label: s, value: bySector[s] ?? 0, color: SECTOR_COLOR[s] })).sort((a, b) => b.value - a.value)} />
        </Card>
        <Card title="Sous-projets par statut" subtitle="Circuit d'approbation et exécution">
          <Distribution parts={[
            { label: "En instruction", value: (invStatus["Soumis"] ?? 0) + (invStatus["Validation CCD"] ?? 0) + (invStatus["Revue communale"] ?? 0) + (invStatus["Revue régionale"] ?? 0) + (invStatus["Approbation UCP"] ?? 0), color: "#2a78d6" },
            { label: "Approuvés", value: invStatus["Approuvé"] ?? 0, color: "#4a3aa7" },
            { label: "En exécution", value: invStatus["En exécution"] ?? 0, color: "#eda100" },
            { label: "Achevés", value: invStatus["Achevé"] ?? 0, color: "#1baf7a" },
            { label: "Rejetés", value: invStatus["Rejeté"] ?? 0, color: "#e34948" },
          ]} />
          <div className="mt-5">
            <div className="text-xs font-medium text-ink-2 mb-2">Budget engagé par région</div>
            <HBarChart data={REGIONS.map((r) => { const s = sumBy(engaged.filter((i) => villageById(i.villageId)!.regionId === r.id), (i) => i.budgetFcfa); return { label: r.name, value: s, display: fmtMFcfa(s) }; })} />
          </div>
        </Card>
        <Card title="Plaintes reçues par mois" subtitle="12 derniers mois · tous canaux">
          <Sparkline points={grmByMonth} labels={months.map((m) => m.slice(5) + "/" + m.slice(2, 4))} color="#eb6834" />
          <div className="mt-4 text-xs font-medium text-ink-2 mb-2">Par catégorie (ouvertes)</div>
          <HBarChart data={Object.entries(countBy(openGrm, (g) => g.category)).map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value).slice(0, 6)} color="#eb6834" />
        </Card>
      </div>

      <div className="grid lg:grid-cols-5 gap-4">
        <Card title="Couverture par région" className="lg:col-span-3" action={<Link href="/territoires" className="text-xs text-brand-700 hover:underline">Voir les territoires →</Link>}>
          <Table head={["Région", "Préfectures", "Cantons", "Villages", "Population", "Priorités", "Sous-projets", "Budget engagé"]}>
            {REGIONS.map((r) => {
              const vs = VILLAGES.filter((v) => v.regionId === r.id);
              const ids = new Set(vs.map((v) => v.id));
              const inv = INVESTMENTS.filter((i) => ids.has(i.villageId));
              return (
                <tr key={r.id}>
                  <td className="pr-4 font-medium"><Link className="hover:underline text-brand-700" href={`/territoires/regions/${r.id}`}>{r.name}</Link></td>
                  <td className="pr-4 tabular-nums">{PREFECTURES.filter((p) => p.regionId === r.id).length}</td>
                  <td className="pr-4 tabular-nums">{CANTONS.filter((c) => c.regionId === r.id).length}</td>
                  <td className="pr-4 tabular-nums">{vs.length}</td>
                  <td className="pr-4 tabular-nums">{fmtInt(sumBy(vs, (v) => v.population))}</td>
                  <td className="pr-4 tabular-nums">{PRIORITIES.filter((p) => ids.has(p.villageId)).length}</td>
                  <td className="pr-4 tabular-nums">{inv.length}</td>
                  <td className="pr-4 tabular-nums">{fmtMFcfa(sumBy(inv.filter((i) => ["Approuvé", "En exécution", "Achevé"].includes(i.status)), (i) => i.budgetFcfa))}</td>
                </tr>
              );
            })}
          </Table>
        </Card>
        <Card title="Derniers paquets soumis" className="lg:col-span-2" action={<Link href="/investissements" className="text-xs text-brand-700 hover:underline">Tout voir →</Link>}>
          <ul className="divide-y divide-line">
            {recent.map((i) => {
              const v = villageById(i.villageId)!;
              return (
                <li key={i.id} className="py-2 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <Link href={`/investissements/${i.id}`} className="text-sm font-medium hover:underline text-brand-700 block truncate">{i.code} · {i.title}</Link>
                    <div className="text-xs text-ink-3">{v.name} · {cantonById(v.cantonId)!.name} · {fmtDate(i.submittedAt)}</div>
                  </div>
                  <StatusBadge status={i.status} />
                </li>
              );
            })}
          </ul>
        </Card>
      </div>
    </>
  );
}
