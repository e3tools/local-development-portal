import { Card, Kpi, PageHeader, Btn } from "@/components/ui";
import { PrioritiesTable, type PriorityRow } from "@/components/priorities-table";
import { PRIORITIES } from "@/data/priorities";
import { REGIONS, villageById, cantonById, prefectureById, regionById } from "@/data/geo";
import { fmtInt, fmtMFcfa } from "@/lib/format";

export const metadata = { title: "Registre des priorités" };

export default function Priorites() {
  const rows: PriorityRow[] = PRIORITIES.map((p) => {
    const v = villageById(p.villageId)!;
    const c = cantonById(v.cantonId)!;
    return { id: p.id, code: p.code, title: p.title, sector: p.sector, rank: p.rank, status: p.status, source: p.source, cost: p.estimatedCostFcfa, beneficiaries: p.beneficiaries, votes: p.votes, village: v.name, villageId: v.id, canton: c.name, prefecture: prefectureById(c.prefectureId)!.name, region: regionById(v.regionId)!.name, registeredAt: p.registeredAt };
  });
  const validated = PRIORITIES.filter((p) => p.status !== "Identifiée" && p.status !== "Non retenue");
  return (
    <>
      <PageHeader title="Registre des priorités locales" subtitle="Registre unique des besoins prioritaires exprimés par les communautés (assemblées villageoises, focus groupes femmes/jeunes). Base d'alimentation des Plans de développement cantonaux et des paquets d'investissement."
        action={<div className="flex gap-2"><Btn>Exporter (Excel)</Btn><Btn primary>+ Nouvelle priorité</Btn></div>} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Kpi label="Priorités enregistrées" value={fmtInt(PRIORITIES.length)} sub={`${fmtInt(new Set(PRIORITIES.map((p) => p.villageId)).size)} villages`} />
        <Kpi label="Validées ou plus" value={fmtInt(validated.length)} sub="Validée CCD, intégrée au PDC ou financée" tone="info" />
        <Kpi label="Financées" value={fmtInt(PRIORITIES.filter((p) => p.status === "Financée").length)} sub={fmtMFcfa(PRIORITIES.filter((p) => p.status === "Financée").reduce((s, p) => s + p.estimatedCostFcfa, 0))} tone="good" />
        <Kpi label="Besoin non couvert" value={fmtMFcfa(PRIORITIES.filter((p) => ["Identifiée", "Validée CCD", "Intégrée au PDC"].includes(p.status)).reduce((s, p) => s + p.estimatedCostFcfa, 0))} sub="Priorités en attente de financement" tone="warning" />
      </div>
      <Card>
        <PrioritiesTable rows={rows} regions={REGIONS.map((r) => r.name)} />
      </Card>
    </>
  );
}
