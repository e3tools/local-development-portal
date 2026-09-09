import { Card, Kpi, PageHeader, Btn } from "@/components/ui";
import { Distribution } from "@/components/charts";
import { InvestmentsTable, type InvestmentRow } from "@/components/investments-table";
import { INVESTMENTS, APPROVAL_STEPS } from "@/data/investments";
import { REGIONS, villageById, cantonById, regionById } from "@/data/geo";
import { PARTNERS, partnerById } from "@/data/partners";
import { fmtInt, fmtMFcfa, fmtPct } from "@/lib/format";
import { sumBy } from "@/lib/stats";

export const metadata = { title: "Paquets d'investissement" };

export default function Investissements() {
  const rows: InvestmentRow[] = INVESTMENTS.map((i) => {
    const v = villageById(i.villageId)!;
    const cur = i.steps.find((s) => s.status === "En cours" || s.status === "Rejeté");
    return { id: i.id, code: i.code, title: i.title, sector: i.sector, status: i.status, budget: i.budgetFcfa, disbursed: i.disbursedFcfa, progress: i.physicalProgress, village: v.name, villageId: v.id, canton: cantonById(v.cantonId)!.name, region: regionById(v.regionId)!.name, partner: partnerById(i.partnerId)!.shortName, submittedAt: i.submittedAt, currentStep: cur ? cur.label : i.status === "Achevé" ? "Réception définitive" : "Exécution", pendingActor: cur ? cur.actor : i.contractor ?? "" };
  });
  const engaged = INVESTMENTS.filter((i) => ["Approuvé", "En exécution", "Achevé"].includes(i.status));
  const pending = INVESTMENTS.filter((i) => !["Approuvé", "En exécution", "Achevé", "Rejeté"].includes(i.status));
  const stepCounts = APPROVAL_STEPS.map((s) => ({ label: s.label, value: pending.filter((i) => i.steps.find((x) => x.status === "En cours")?.key === s.key).length }));
  const stepColors = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7"];
  return (
    <>
      <PageHeader title="Paquets d'investissement" subtitle="Sous-projets issus des priorités locales, suivis tout au long du circuit d'approbation (CVD → CCD → commune → région → UCP) puis en exécution."
        action={<div className="flex gap-2"><Btn>Exporter</Btn><Btn primary>+ Soumettre un paquet</Btn></div>} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Kpi label="Paquets soumis" value={fmtInt(INVESTMENTS.length)} sub={`${pending.length} en instruction · ${INVESTMENTS.filter((i) => i.status === "Rejeté").length} rejetés`} />
        <Kpi label="Budget engagé" value={fmtMFcfa(sumBy(engaged, (i) => i.budgetFcfa))} sub={`${engaged.length} sous-projets approuvés+`} tone="good" />
        <Kpi label="Taux de décaissement" value={fmtPct((sumBy(engaged, (i) => i.disbursedFcfa) / sumBy(engaged, (i) => i.budgetFcfa)) * 100)} sub={fmtMFcfa(sumBy(engaged, (i) => i.disbursedFcfa)) + " décaissés"} tone="info" />
        <Kpi label="Emplois HIMO créés" value={fmtInt(sumBy(INVESTMENTS, (i) => i.himoJobs))} sub={`${fmtInt(sumBy(engaged, (i) => i.beneficiaries))} bénéficiaires directs`} tone="violet" />
      </div>
      <Card title="Paquets en instruction par étape" subtitle="Où se trouvent les dossiers dans le circuit d'approbation" className="mb-4">
        <Distribution parts={stepCounts.map((s, i) => ({ ...s, color: stepColors[i] }))} />
      </Card>
      <Card>
        <InvestmentsTable rows={rows} regions={REGIONS.map((r) => r.name)} partners={PARTNERS.map((p) => p.shortName)} />
      </Card>
    </>
  );
}
