import Link from "next/link";
import { notFound } from "next/navigation";
import { Card, Kpi, PageHeader, Table, Badge, Dl, StatusBadge, Yes, Btn, Progress } from "@/components/ui";
import { VILLAGES, villageById, cantonById, prefectureById, regionById } from "@/data/geo";
import { prioritiesOfVillage } from "@/data/priorities";
import { investmentsOfVillage } from "@/data/investments";
import { GRIEVANCES } from "@/data/grm";
import { photosOfVillage } from "@/data/media";
import { Gallery } from "@/components/gallery";
import { SECTOR_COLOR } from "@/data/sectors";
import { fmtInt, fmtMFcfa, fmtDate, fmtPct } from "@/lib/format";

export function generateStaticParams() { return VILLAGES.map((v) => ({ id: v.id })); }

export default async function VillagePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const v = villageById(id);
  if (!v) notFound();
  const canton = cantonById(v.cantonId)!;
  const pref = prefectureById(v.prefectureId)!;
  const region = regionById(v.regionId)!;
  const prios = prioritiesOfVillage(v.id);
  const invs = investmentsOfVillage(v.id);
  const grm = GRIEVANCES.filter((g) => g.villageId === v.id);
  const photos = photosOfVillage(v.id);
  const vulnTone = v.vulnerabilityScore >= 70 ? "critical" : v.vulnerabilityScore >= 55 ? "warning" : "good";
  return (
    <>
      <PageHeader crumbs={[{ href: "/territoires", label: "Territoires" }, { href: `/territoires/regions/${region.id}`, label: region.name }, { label: pref.name }, { href: `/territoires/cantons/${canton.id}`, label: `Canton de ${canton.name}` }, { label: v.name }]}
        title={`Profil du village de ${v.name}`} subtitle={`Canton de ${canton.name}, préfecture de ${pref.name}, région ${region.name}. Profil réalisé le ${fmtDate(v.profiledAt)} par ${v.profiledBy}.`}
        action={<div className="flex gap-2"><Btn>Fiche PDF</Btn><Btn primary>Mettre à jour le profil</Btn></div>} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Kpi label="Population" value={fmtInt(v.population)} sub={`${fmtInt(v.households)} ménages · ${v.womenPct} % femmes · ${v.youthPct} % jeunes`} />
        <Kpi label="Indice de vulnérabilité" value={`${v.vulnerabilityScore}/100`} sub={v.displacedHouseholds ? `${v.displacedHouseholds} ménages déplacés accueillis` : "Aucun ménage déplacé"} tone={vulnTone} />
        <Kpi label="Priorités enregistrées" value={prios.length} sub={`${prios.filter((p) => p.status === "Financée").length} financée(s)`} tone="violet" />
        <Kpi label="Sous-projets" value={invs.length} sub={fmtMFcfa(invs.reduce((s, i) => s + (i.status === "Rejeté" ? 0 : i.budgetFcfa), 0))} tone="info" />
      </div>
      <div className="grid lg:grid-cols-3 gap-4 mb-4">
        <Card title="Identité et contexte">
          <Dl items={[
            ["Coordonnées GPS", <span className="font-mono text-xs" key="gps">{v.gps.lat}, {v.gps.lng}</span>],
            ["Distance au chef-lieu de canton", `${v.distanceKm} km`],
            ["Groupes socio-culturels", v.ethnicGroups.join(", ")],
            ["Activités principales", v.activities.join(", ")],
            ["Accessibilité routière", v.infra.roadAccess],
            ["Couverture mobile", <Yes key="m" v={v.infra.mobileCoverage} />],
          ]} />
        </Card>
        <Card title="Infrastructures et services">
          <Dl items={[
            ["École primaire", <Yes key="a" v={v.infra.primarySchool} />],
            ["Collège / lycée", <Yes key="b" v={v.infra.secondarySchool} />],
            ["Centre de santé (USP)", <Yes key="c" v={v.infra.healthCenter} />],
            ["Points d'eau", `${v.infra.functionalWaterPoints} fonctionnels / ${v.infra.waterPoints}`],
            ["Marché", <Yes key="d" v={v.infra.market} />],
            ["Électricité", <Yes key="e" v={v.infra.electricity} />],
          ]} />
          <div className="mt-3">
            <div className="text-xs text-ink-3 mb-1">Fonctionnalité des points d'eau</div>
            <Progress value={v.infra.waterPoints ? (v.infra.functionalWaterPoints / v.infra.waterPoints) * 100 : 0} color="#2a78d6" label={v.infra.waterPoints ? fmtPct((v.infra.functionalWaterPoints / v.infra.waterPoints) * 100) : "n/a"} />
          </div>
        </Card>
        <Card title="Comité villageois de développement (CVD)">
          <Dl items={[
            ["Président(e)", v.cvd.president],
            ["Secrétaire", v.cvd.secretary],
            ["Installé en", String(v.cvd.createdYear)],
            ["Membres", `${v.cvd.members}`],
            ["Dont femmes", `${v.cvd.women} (${Math.round((v.cvd.women / v.cvd.members) * 100)} %)`],
            ["Dont jeunes", `${v.cvd.youth}`],
          ]} />
          <div className="mt-3 flex flex-wrap gap-1.5">
            <Badge tone={v.cvd.women / v.cvd.members >= 0.3 ? "good" : "warning"}>{v.cvd.women / v.cvd.members >= 0.3 ? "Quota femmes ≥ 30 % atteint" : "Quota femmes < 30 %"}</Badge>
            <Badge tone="info">Formé au MGP</Badge>
          </div>
        </Card>
      </div>
      <Card title="Photothèque du village" subtitle={`${photos.length} photo(s) versées au dossier par les agents de terrain`} className="mb-4"
        action={<span className="text-xs text-ink-3">Illustrations de démonstration</span>}>
        <Gallery photos={photos} columns={4} />
      </Card>
      <Card title="Priorités locales du village" subtitle="Issues de l'assemblée villageoise et des focus groupes · classées par rang" className="mb-4" action={<Link href="/priorites" className="text-xs text-brand-700 hover:underline">Registre complet →</Link>}>
        <Table head={["Rang", "Code", "Priorité", "Secteur", "Source", "Coût estimé", "Bénéficiaires", "Voix", "Statut"]}>
          {prios.map((p) => (
            <tr key={p.id}>
              <td className="pr-4 font-semibold">#{p.rank}</td>
              <td className="pr-4 font-mono text-xs">{p.code}</td>
              <td className="pr-4 font-medium">{p.title}</td>
              <td className="pr-4"><span className="inline-flex items-center gap-1.5 text-xs"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: SECTOR_COLOR[p.sector] }} />{p.sector}</span></td>
              <td className="pr-4 text-ink-2 text-xs">{p.source}</td>
              <td className="pr-4 tabular-nums">{fmtMFcfa(p.estimatedCostFcfa)}</td>
              <td className="pr-4 tabular-nums">{fmtInt(p.beneficiaries)}</td>
              <td className="pr-4 tabular-nums">{p.votes}</td>
              <td className="pr-4"><StatusBadge status={p.status} /></td>
            </tr>
          ))}
        </Table>
      </Card>
      <div className="grid lg:grid-cols-2 gap-4">
        <Card title="Sous-projets">
          {invs.length === 0 ? <p className="text-sm text-ink-3 italic">Aucun sous-projet pour ce village.</p> : (
            <ul className="divide-y divide-line">
              {invs.map((i) => (
                <li key={i.id} className="py-2.5">
                  <div className="flex items-center justify-between gap-3">
                    <Link href={`/investissements/${i.id}`} className="font-medium text-brand-700 hover:underline">{i.code} · {i.title}</Link>
                    <StatusBadge status={i.status} />
                  </div>
                  <div className="text-xs text-ink-3 mt-0.5">Budget {fmtMFcfa(i.budgetFcfa)} · {i.contractor ?? "Entreprise non attribuée"}</div>
                  {i.physicalProgress > 0 && <div className="mt-1.5"><Progress value={i.physicalProgress} color="#1baf7a" /></div>}
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Plaintes liées au village" subtitle={`${grm.length} plainte(s)`}>
          {grm.length === 0 ? <p className="text-sm text-ink-3 italic">Aucune plainte enregistrée.</p> : (
            <Table head={["Code", "Catégorie", "Canal", "Reçue", "Statut"]} dense>
              {grm.map((g) => (
                <tr key={g.id}>
                  <td className="pr-4 font-mono text-xs">{g.code}</td>
                  <td className="pr-4">{g.sensitive ? <span className="text-ink-3">Plainte sensible (confidentiel)</span> : g.category}</td>
                  <td className="pr-4 text-ink-2 text-xs">{g.channel}</td>
                  <td className="pr-4 text-ink-2">{fmtDate(g.receivedAt)}</td>
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
