import Link from "next/link";
import { notFound } from "next/navigation";
import { Card, Kpi, PageHeader, Table, Badge } from "@/components/ui";
import { HBarChart } from "@/components/charts";
import { REGIONS, regionById, prefecturesOfRegion, cantonsOfPrefecture, villagesOfCanton, villagesOfRegion } from "@/data/geo";
import { PRIORITIES } from "@/data/priorities";
import { INVESTMENTS } from "@/data/investments";
import { GRIEVANCES } from "@/data/grm";
import { PARTNERS } from "@/data/partners";
import { SECTORS, SECTOR_COLOR } from "@/data/sectors";
import { fmtInt, fmtMFcfa } from "@/lib/format";
import { countBy, sumBy } from "@/lib/stats";

export function generateStaticParams() { return REGIONS.map((r) => ({ id: r.id })); }

export default async function RegionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const region = regionById(id);
  if (!region) notFound();
  const vs = villagesOfRegion(region.id);
  const ids = new Set(vs.map((v) => v.id));
  const prios = PRIORITIES.filter((p) => ids.has(p.villageId));
  const invs = INVESTMENTS.filter((i) => ids.has(i.villageId));
  const grm = GRIEVANCES.filter((g) => ids.has(g.villageId));
  const bySector = countBy(prios, (p) => p.sector);
  const partners = PARTNERS.filter((p) => p.regions.includes(region.id));
  return (
    <>
      <PageHeader crumbs={[{ href: "/territoires", label: "Territoires" }, { label: `Région ${region.name}` }]} title={`Région ${region.name}`} subtitle={`Chef-lieu ${region.chefLieu}. Groupes socio-culturels : ${region.ethnicGroups.join(", ")}. Activités : ${region.activities.join(", ")}.`} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Kpi label="Villages profilés" value={fmtInt(vs.length)} sub={`${fmtInt(sumBy(vs, (v) => v.population))} habitants`} />
        <Kpi label="Priorités" value={fmtInt(prios.length)} sub={`${prios.filter((p) => p.status === "Financée").length} financées`} tone="violet" />
        <Kpi label="Sous-projets" value={fmtInt(invs.length)} sub={fmtMFcfa(sumBy(invs.filter((i) => i.status !== "Rejeté"), (i) => i.budgetFcfa))} tone="info" />
        <Kpi label="Plaintes" value={fmtInt(grm.length)} sub={`${grm.filter((g) => !["Résolue", "Clôturée"].includes(g.status)).length} ouvertes`} tone="warning" />
      </div>
      <div className="grid lg:grid-cols-3 gap-4 mb-4">
        <Card title="Priorités par secteur" className="lg:col-span-1">
          <HBarChart data={SECTORS.map((s) => ({ label: s, value: bySector[s] ?? 0, color: SECTOR_COLOR[s] })).sort((a, b) => b.value - a.value)} />
        </Card>
        <Card title="Partenaires actifs dans la région" className="lg:col-span-2" action={<Link href="/partenaires" className="text-xs text-brand-700 hover:underline">Vue partenaires →</Link>}>
          <Table head={["Partenaire", "Type", "Secteurs dans la région", "Montant positionné"]} dense>
            {partners.map((p) => {
              const pos = p.positions.filter((x) => x.regionId === region.id);
              return (
                <tr key={p.id}>
                  <td className="pr-4 font-medium">{p.shortName}</td>
                  <td className="pr-4 text-ink-2">{p.type}</td>
                  <td className="pr-4"><div className="flex flex-wrap gap-1">{pos.map((x) => <Badge key={x.sector} icon={false}>{x.sector}</Badge>)}</div></td>
                  <td className="pr-4 tabular-nums">{fmtMFcfa(sumBy(pos, (x) => x.amountFcfa))}</td>
                </tr>
              );
            })}
          </Table>
        </Card>
      </div>
      <Card title="Préfectures et cantons">
        <Table head={["Préfecture", "Canton", "Chef de canton", "PDC", "Villages", "Population", "Priorités", "Sous-projets", "Vulnérabilité moy."]}>
          {prefecturesOfRegion(region.id).flatMap((p) =>
            cantonsOfPrefecture(p.id).map((c, i) => {
              const cv = villagesOfCanton(c.id);
              const cids = new Set(cv.map((v) => v.id));
              const vuln = Math.round(sumBy(cv, (v) => v.vulnerabilityScore) / cv.length);
              return (
                <tr key={c.id}>
                  <td className="pr-4 text-ink-2">{i === 0 ? <span className="font-medium text-ink">{p.name}</span> : ""}</td>
                  <td className="pr-4"><Link href={`/territoires/cantons/${c.id}`} className="font-medium text-brand-700 hover:underline">{c.name}</Link></td>
                  <td className="pr-4 text-ink-2">{c.chefCanton}</td>
                  <td className="pr-4">{c.hasPdc ? <Badge tone="good" icon={false}>PDC {c.pdcYear}</Badge> : <Badge tone="neutral" icon={false}>Sans PDC</Badge>}</td>
                  <td className="pr-4 tabular-nums">{cv.length}</td>
                  <td className="pr-4 tabular-nums">{fmtInt(sumBy(cv, (v) => v.population))}</td>
                  <td className="pr-4 tabular-nums">{PRIORITIES.filter((x) => cids.has(x.villageId)).length}</td>
                  <td className="pr-4 tabular-nums">{INVESTMENTS.filter((x) => cids.has(x.villageId)).length}</td>
                  <td className="pr-4"><Badge tone={vuln >= 70 ? "critical" : vuln >= 55 ? "warning" : "good"}>{vuln}/100</Badge></td>
                </tr>
              );
            }),
          )}
        </Table>
      </Card>
    </>
  );
}
