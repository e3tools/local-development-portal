import Link from "next/link";
import { notFound } from "next/navigation";
import { Card, Kpi, PageHeader, Table, Badge, Dl, StatusBadge, Btn } from "@/components/ui";
import { HBarChart, Distribution } from "@/components/charts";
import { CANTONS, cantonById, prefectureById, regionById, villagesOfCanton } from "@/data/geo";
import { PRIORITIES } from "@/data/priorities";
import { INVESTMENTS } from "@/data/investments";
import { GRIEVANCES } from "@/data/grm";
import { SECTORS, SECTOR_COLOR } from "@/data/sectors";
import { fmtInt, fmtMFcfa, fmtPct } from "@/lib/format";
import { countBy, sumBy } from "@/lib/stats";

export function generateStaticParams() { return CANTONS.map((c) => ({ id: c.id })); }

export default async function CantonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const canton = cantonById(id);
  if (!canton) notFound();
  const pref = prefectureById(canton.prefectureId)!;
  const region = regionById(canton.regionId)!;
  const vs = villagesOfCanton(canton.id);
  const ids = new Set(vs.map((v) => v.id));
  const prios = PRIORITIES.filter((p) => ids.has(p.villageId));
  const invs = INVESTMENTS.filter((i) => ids.has(i.villageId));
  const grm = GRIEVANCES.filter((g) => ids.has(g.villageId));
  const pop = sumBy(vs, (v) => v.population);
  const bySector = countBy(prios, (p) => p.sector);
  const wp = sumBy(vs, (v) => v.infra.waterPoints);
  const fwp = sumBy(vs, (v) => v.infra.functionalWaterPoints);
  return (
    <>
      <PageHeader crumbs={[{ href: "/territoires", label: "Territoires" }, { href: `/territoires/regions/${region.id}`, label: `Région ${region.name}` }, { label: `Préfecture de ${pref.name}` }, { label: `Canton de ${canton.name}` }]}
        title={`Profil du canton de ${canton.name}`} subtitle={`Préfecture de ${pref.name}, région ${region.name}. ${vs.length} villages profilés, ${fmtInt(pop)} habitants.`}
        action={<div className="flex gap-2"><Btn>Exporter le profil (PDF)</Btn><Btn primary>Mettre à jour</Btn></div>} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Kpi label="Population" value={fmtInt(pop)} sub={`${fmtInt(sumBy(vs, (v) => v.households))} ménages · ${vs.length} villages`} />
        <Kpi label="Priorités" value={fmtInt(prios.length)} sub={`${fmtMFcfa(sumBy(prios, (p) => p.estimatedCostFcfa))} estimés`} tone="violet" />
        <Kpi label="Sous-projets" value={fmtInt(invs.length)} sub={`${invs.filter((i) => i.status === "En exécution").length} en exécution · ${invs.filter((i) => i.status === "Achevé").length} achevés`} tone="info" />
        <Kpi label="Points d'eau fonctionnels" value={`${fwp} / ${wp}`} sub={wp ? fmtPct((fwp / wp) * 100) + " de fonctionnalité" : "Aucun point d'eau"} tone={wp && fwp / wp < 0.5 ? "critical" : "good"} />
      </div>
      <div className="grid lg:grid-cols-3 gap-4 mb-4">
        <Card title="Gouvernance locale" subtitle="Chefferie et Comité cantonal de développement (CCD)">
          <Dl items={[
            ["Chef de canton", canton.chefCanton],
            ["Président CCD", canton.ccdPresident],
            ["CCD installé en", String(canton.ccdCreatedYear)],
            ["Membres CCD", `${canton.ccdMembers} dont ${canton.ccdWomen} femmes`],
            ["Plan de développement cantonal", canton.hasPdc ? <Badge tone="good">Adopté ${canton.pdcYear}</Badge> : <Badge tone="warning">En préparation</Badge>],
            ["Communes de rattachement", `${pref.name} 1 / ${pref.name} 2`],
          ]} />
        </Card>
        <Card title="Priorités par secteur" subtitle="Consolidation des priorités villageoises">
          <HBarChart data={SECTORS.map((s) => ({ label: s, value: bySector[s] ?? 0, color: SECTOR_COLOR[s] })).filter((d) => d.value > 0).sort((a, b) => b.value - a.value)} />
        </Card>
        <Card title="Accès aux services de base" subtitle="Part des villages disposant de l'infrastructure">
          <HBarChart max={vs.length} unit={` / ${vs.length}`} data={[
            { label: "École primaire", value: vs.filter((v) => v.infra.primarySchool).length },
            { label: "Collège / lycée", value: vs.filter((v) => v.infra.secondarySchool).length },
            { label: "Centre de santé", value: vs.filter((v) => v.infra.healthCenter).length },
            { label: "Marché", value: vs.filter((v) => v.infra.market).length },
            { label: "Électricité", value: vs.filter((v) => v.infra.electricity).length },
            { label: "Couverture mobile", value: vs.filter((v) => v.infra.mobileCoverage).length },
          ]} color="#1baf7a" />
          <div className="mt-4 text-xs font-medium text-ink-2 mb-2">Accessibilité routière</div>
          <Distribution parts={[
            { label: "Permanente", value: vs.filter((v) => v.infra.roadAccess === "Permanente").length, color: "#1baf7a" },
            { label: "Saisonnière", value: vs.filter((v) => v.infra.roadAccess === "Saisonnière").length, color: "#eda100" },
            { label: "Difficile", value: vs.filter((v) => v.infra.roadAccess === "Difficile").length, color: "#e34948" },
          ]} />
        </Card>
      </div>
      <Card title="Villages du canton" className="mb-4">
        <Table head={["Village", "Population", "Ménages", "Distance chef-lieu", "École", "Santé", "Eau (fonct./total)", "Accès", "Vulnérabilité", "Priorités", "SP", "Profil mis à jour"]}>
          {vs.map((v) => (
            <tr key={v.id}>
              <td className="pr-4"><Link href={`/territoires/villages/${v.id}`} className="font-medium text-brand-700 hover:underline">{v.name}</Link></td>
              <td className="pr-4 tabular-nums">{fmtInt(v.population)}</td>
              <td className="pr-4 tabular-nums">{fmtInt(v.households)}</td>
              <td className="pr-4 tabular-nums">{v.distanceKm} km</td>
              <td className="pr-4">{v.infra.primarySchool ? "Oui" : <span className="text-red-700">Non</span>}</td>
              <td className="pr-4">{v.infra.healthCenter ? "Oui" : <span className="text-red-700">Non</span>}</td>
              <td className="pr-4 tabular-nums">{v.infra.functionalWaterPoints} / {v.infra.waterPoints}</td>
              <td className="pr-4">{v.infra.roadAccess}</td>
              <td className="pr-4"><Badge tone={v.vulnerabilityScore >= 70 ? "critical" : v.vulnerabilityScore >= 55 ? "warning" : "good"}>{v.vulnerabilityScore}</Badge></td>
              <td className="pr-4 tabular-nums">{PRIORITIES.filter((p) => p.villageId === v.id).length}</td>
              <td className="pr-4 tabular-nums">{INVESTMENTS.filter((i) => i.villageId === v.id).length}</td>
              <td className="pr-4 text-ink-2">{v.profiledAt}</td>
            </tr>
          ))}
        </Table>
      </Card>
      <div className="grid lg:grid-cols-2 gap-4">
        <Card title="Sous-projets dans le canton" action={<Link href="/investissements" className="text-xs text-brand-700 hover:underline">Tous les paquets →</Link>}>
          {invs.length === 0 ? <p className="text-sm text-ink-3 italic">Aucun sous-projet.</p> : (
            <Table head={["Code", "Intitulé", "Village", "Budget", "Statut"]} dense>
              {invs.map((i) => (
                <tr key={i.id}>
                  <td className="pr-4 font-mono text-xs">{i.code}</td>
                  <td className="pr-4"><Link href={`/investissements/${i.id}`} className="hover:underline text-brand-700">{i.title}</Link></td>
                  <td className="pr-4 text-ink-2">{vs.find((v) => v.id === i.villageId)?.name}</td>
                  <td className="pr-4 tabular-nums">{fmtMFcfa(i.budgetFcfa)}</td>
                  <td className="pr-4"><StatusBadge status={i.status} /></td>
                </tr>
              ))}
            </Table>
          )}
        </Card>
        <Card title="Plaintes enregistrées" subtitle={`${grm.length} plaintes · ${grm.filter((g) => !["Résolue", "Clôturée"].includes(g.status)).length} ouvertes`} action={<Link href="/grm" className="text-xs text-brand-700 hover:underline">Tableau MGP →</Link>}>
          {grm.length === 0 ? <p className="text-sm text-ink-3 italic">Aucune plainte.</p> : (
            <Table head={["Code", "Catégorie", "Village", "Reçue", "Statut"]} dense>
              {grm.slice(0, 8).map((g) => (
                <tr key={g.id}>
                  <td className="pr-4 font-mono text-xs">{g.code}</td>
                  <td className="pr-4">{g.sensitive ? <span className="text-ink-3">Plainte sensible</span> : g.category}</td>
                  <td className="pr-4 text-ink-2">{vs.find((v) => v.id === g.villageId)?.name}</td>
                  <td className="pr-4 text-ink-2">{g.receivedAt}</td>
                  <td className="pr-4"><StatusBadge status={g.status} /></td>
                </tr>
              ))}
            </Table>
          )}
        </Card>
      </div>
    </>
  );
}
