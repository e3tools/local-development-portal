import Link from "next/link";
import { notFound } from "next/navigation";
import { Card, Kpi, PageHeader, Badge, Dl, StatusBadge, Btn, Progress } from "@/components/ui";
import { INVESTMENTS, investmentById } from "@/data/investments";
import { villageById, cantonById, prefectureById, regionById } from "@/data/geo";
import { priorityById } from "@/data/priorities";
import { partnerById } from "@/data/partners";
import { GRIEVANCES } from "@/data/grm";
import { photosOfInvestment } from "@/data/media";
import { Gallery } from "@/components/gallery";
import { SECTOR_COLOR } from "@/data/sectors";
import { fmtInt, fmtFcfa, fmtMFcfa, fmtDate, fmtPct } from "@/lib/format";

export function generateStaticParams() { return INVESTMENTS.map((i) => ({ id: i.id })); }

export default async function InvestmentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const inv = investmentById(id);
  if (!inv) notFound();
  const v = villageById(inv.villageId)!;
  const canton = cantonById(v.cantonId)!;
  const pref = prefectureById(v.prefectureId)!;
  const region = regionById(v.regionId)!;
  const prio = priorityById(inv.priorityId)!;
  const partner = partnerById(inv.partnerId)!;
  const grm = GRIEVANCES.filter((g) => g.investmentId === inv.id);
  const photos = photosOfInvestment(inv.id);
  const current = inv.steps.find((s) => s.status === "En cours");
  const rejected = inv.steps.find((s) => s.status === "Rejeté");
  const executing = inv.status === "En exécution" || inv.status === "Achevé";
  return (
    <>
      <PageHeader crumbs={[{ href: "/investissements", label: "Paquets d'investissement" }, { label: inv.code }]}
        title={<span className="flex flex-wrap items-center gap-3">{inv.code} · {inv.title} <StatusBadge status={inv.status} /></span>}
        subtitle={<>Village de <Link className="text-brand-700 hover:underline" href={`/territoires/villages/${v.id}`}>{v.name}</Link>, canton de <Link className="text-brand-700 hover:underline" href={`/territoires/cantons/${canton.id}`}>{canton.name}</Link>, préfecture de {pref.name}, région {region.name}.</>}
        action={current ? <div className="flex gap-2"><Btn>Demander des compléments</Btn><Btn>Rejeter</Btn><Btn primary>Valider l'étape « {current.label} »</Btn></div> : <Btn>Télécharger le dossier</Btn>} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Kpi label="Budget" value={fmtMFcfa(inv.budgetFcfa)} sub={`Estimation initiale ${fmtMFcfa(prio.estimatedCostFcfa)}`} />
        <Kpi label="Décaissé" value={fmtMFcfa(inv.disbursedFcfa)} sub={inv.budgetFcfa ? fmtPct((inv.disbursedFcfa / inv.budgetFcfa) * 100) + " du budget" : ""} tone="good" />
        <Kpi label="Avancement physique" value={fmtPct(inv.physicalProgress)} sub={executing ? `Fin prévue ${fmtDate(inv.expectedEndDate)}` : "Non démarré"} tone="info" />
        <Kpi label="Bénéficiaires" value={fmtInt(inv.beneficiaries)} sub={`${fmtInt(inv.womenBeneficiaries)} femmes · ${inv.himoJobs} emplois HIMO`} tone="violet" />
      </div>
      <div className="grid lg:grid-cols-3 gap-4 mb-4">
        <Card title="Circuit d'approbation" subtitle="Chaque étape est validée par le rôle habilité ; les commentaires sont tracés." className="lg:col-span-2">
          <ol className="relative border-l border-line ml-3 space-y-5">
            {inv.steps.map((s, i) => {
              const dot = s.status === "Terminé" ? "bg-green-600" : s.status === "En cours" ? "bg-amber-500 ring-4 ring-amber-100" : s.status === "Rejeté" ? "bg-red-600" : "bg-gray-300";
              return (
                <li key={s.key} className="pl-6">
                  <span className={`absolute -left-[7px] mt-1 h-3.5 w-3.5 rounded-full ${dot}`} aria-hidden />
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium">{i + 1}. {s.label}</span>
                    <StatusBadge status={s.status} />
                    {s.date && <span className="text-xs text-ink-3">{fmtDate(s.date)}</span>}
                  </div>
                  <div className="text-xs text-ink-2 mt-0.5">{s.role} · {s.actor}</div>
                  {s.comment && <div className={`mt-1 text-xs rounded-md px-2 py-1 inline-block ${s.status === "Rejeté" ? "bg-red-50 text-red-800" : "bg-surface text-ink-2"}`}>« {s.comment} »</div>}
                </li>
              );
            })}
            {executing && (
              <>
                <li className="pl-6"><span className="absolute -left-[7px] mt-1 h-3.5 w-3.5 rounded-full bg-green-600" aria-hidden /><div className="text-sm font-medium">7. Contractualisation et démarrage</div><div className="text-xs text-ink-2">{inv.contractor} · démarrage {fmtDate(inv.startDate)}</div></li>
                <li className="pl-6"><span className={`absolute -left-[7px] mt-1 h-3.5 w-3.5 rounded-full ${inv.status === "Achevé" ? "bg-green-600" : "bg-amber-500 ring-4 ring-amber-100"}`} aria-hidden /><div className="text-sm font-medium">8. Exécution et réception</div><div className="mt-1 max-w-sm"><Progress value={inv.physicalProgress} color="#1baf7a" /></div></li>
              </>
            )}
          </ol>
          {rejected && <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">Dossier rejeté à l'étape « {rejected.label} ». Le CVD peut soumettre un dossier révisé.</div>}
        </Card>
        <div className="space-y-4">
          <Card title="Fiche du sous-projet">
            <Dl items={[
              ["Secteur", <span key="s" className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: SECTOR_COLOR[inv.sector] }} />{inv.sector}</span>],
              ["Priorité d'origine", <Link key="p" href="/priorites" className="text-brand-700 hover:underline">{prio.code} (rang #{prio.rank})</Link>],
              ["Source de financement", partner.shortName],
              ["Budget", fmtFcfa(inv.budgetFcfa)],
              ["Soumis le", fmtDate(inv.submittedAt)],
              ["Entreprise / prestataire", inv.contractor ?? "—"],
              ["Démarrage", fmtDate(inv.startDate)],
              ["Fin prévue", fmtDate(inv.expectedEndDate)],
            ]} />
          </Card>
          <Card title="Pièces du dossier">
            <ul className="text-sm space-y-1.5">
              {["PV de l'assemblée villageoise", "Fiche de priorisation signée CVD", "Devis estimatif", "Attestation de disponibilité du site", "Fiche de screening environnemental & social", "Plan de gestion / entretien"].map((d, i) => (
                <li key={d} className="flex items-center justify-between gap-2"><span>{d}</span>{i < inv.steps.filter((s) => s.status === "Terminé").length + 2 ? <Badge tone="good" icon={false}>Fourni</Badge> : <Badge tone="warning" icon={false}>Manquant</Badge>}</li>
              ))}
            </ul>
          </Card>
          <Card title="Plaintes liées" subtitle={`${grm.length} plainte(s) rattachée(s)`}>
            {grm.length === 0 ? <p className="text-sm text-ink-3 italic">Aucune plainte liée à ce sous-projet.</p> : (
              <ul className="text-sm space-y-1.5">{grm.map((g) => <li key={g.id} className="flex justify-between gap-2"><span className="font-mono text-xs">{g.code}</span><span className="flex-1 text-ink-2 text-xs">{g.sensitive ? "Plainte sensible" : g.category}</span><StatusBadge status={g.status} /></li>)}</ul>
            )}
          </Card>
        </div>
      </div>
      <Card title="Suivi photographique" subtitle="Photos versées par les agents de terrain aux différentes étapes du sous-projet"
        action={<span className="text-xs text-ink-3">Illustrations de démonstration</span>}>
        <Gallery photos={photos} columns={4} />
      </Card>
    </>
  );
}
