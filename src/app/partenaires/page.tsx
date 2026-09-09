import { Card, Kpi, PageHeader, Badge, Btn, Table } from "@/components/ui";
import { HBarChart } from "@/components/charts";
import { PARTNERS } from "@/data/partners";
import { REGIONS } from "@/data/geo";
import { SECTORS, SECTOR_COLOR } from "@/data/sectors";
import { fmtInt, fmtMFcfa } from "@/lib/format";
import { sumBy } from "@/lib/stats";

export const metadata = { title: "Vue partenaires" };

export default function Partenaires() {
  const positions = PARTNERS.flatMap((p) => p.positions.map((x) => ({ ...x, partner: p })));
  const total = sumBy(positions, (x) => x.amountFcfa);
  const cell = (regionId: string, sector: string) => positions.filter((x) => x.regionId === regionId && x.sector === sector);
  const maxCell = Math.max(...REGIONS.flatMap((r) => SECTORS.map((s) => sumBy(cell(r.id, s), (x) => x.amountFcfa))));
  const shade = (v: number) => (v === 0 ? "#ffffff" : v / maxCell < 0.2 ? "#cde2fb" : v / maxCell < 0.4 ? "#9ec5f4" : v / maxCell < 0.6 ? "#6da7ec" : v / maxCell < 0.8 ? "#3987e5" : "#1c5cab");
  const ink = (v: number) => (v / maxCell >= 0.6 ? "#fff" : "#16201b");
  return (
    <>
      <PageHeader title="Vue partenaires et positions d'investissement" subtitle="Cartographie des bailleurs, agences et ONG intervenant dans les régions COSO : qui finance quoi, où, pour combien. Sert à éviter les doublons et à orienter les priorités non couvertes vers les bons guichets."
        action={<div className="flex gap-2"><Btn>Exporter la matrice</Btn><Btn primary>+ Ajouter un partenaire</Btn></div>} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Kpi label="Partenaires actifs" value={PARTNERS.length} sub={`${PARTNERS.filter((p) => p.type === "Bailleur").length} bailleurs · ${PARTNERS.filter((p) => p.type === "Agence ONU").length} agences ONU`} />
        <Kpi label="Engagements cumulés" value={fmtMFcfa(sumBy(PARTNERS, (p) => p.commitmentFcfa))} sub="Toutes régions COSO" tone="good" />
        <Kpi label="Positions renseignées" value={fmtMFcfa(total)} sub={`${positions.length} positions région × secteur`} tone="info" />
        <Kpi label="Projets actifs" value={fmtInt(sumBy(PARTNERS, (p) => p.activeProjects))} sub="Déclarés par les partenaires" tone="violet" />
      </div>
      <Card title="Matrice des positions d'investissement" subtitle="Montants positionnés par région et secteur (toutes sources). Teinte proportionnelle au montant ; survolez pour le détail." className="mb-4">
        <div className="overflow-x-auto -mx-5 px-5">
          <table className="w-full text-xs border-separate border-spacing-[2px]">
            <thead>
              <tr>
                <th className="text-left font-medium text-ink-3 pr-2 py-1">Secteur</th>
                {REGIONS.map((r) => <th key={r.id} className="text-left font-medium text-ink-3 px-2 py-1">{r.name}</th>)}
                <th className="text-right font-medium text-ink-3 px-2 py-1">Total</th>
              </tr>
            </thead>
            <tbody>
              {SECTORS.map((s) => {
                const row = REGIONS.map((r) => cell(r.id, s));
                const rowTotal = sumBy(row.flat(), (x) => x.amountFcfa);
                return (
                  <tr key={s}>
                    <td className="pr-2 py-1 whitespace-nowrap"><span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: SECTOR_COLOR[s] }} />{s}</span></td>
                    {row.map((c, i) => {
                      const v = sumBy(c, (x) => x.amountFcfa);
                      return (
                        <td key={i} className="px-2 py-2 rounded-sm align-top" style={{ background: shade(v), color: ink(v) }} title={c.length ? c.map((x) => `${x.partner.shortName} : ${fmtMFcfa(x.amountFcfa)} (${x.projects} projets)`).join("\n") : "Aucune position"}>
                          {v > 0 ? (<><div className="font-semibold tabular-nums">{fmtMFcfa(v)}</div><div className="opacity-80">{c.map((x) => x.partner.shortName).join(", ")}</div></>) : <span className="text-ink-3">—</span>}
                        </td>
                      );
                    })}
                    <td className="px-2 py-2 text-right font-semibold tabular-nums">{rowTotal ? fmtMFcfa(rowTotal) : "—"}</td>
                  </tr>
                );
              })}
              <tr>
                <td className="pr-2 py-1 font-semibold">Total</td>
                {REGIONS.map((r) => <td key={r.id} className="px-2 py-2 font-semibold tabular-nums">{fmtMFcfa(sumBy(positions.filter((x) => x.regionId === r.id), (x) => x.amountFcfa))}</td>)}
                <td className="px-2 py-2 text-right font-semibold tabular-nums">{fmtMFcfa(total)}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-xs text-ink-3 mt-3">Lecture : les cases vides signalent des secteurs sans partenaire positionné dans la région — à rapprocher du besoin non couvert du registre des priorités.</p>
      </Card>
      <div className="grid lg:grid-cols-3 gap-4">
        <Card title="Engagements par partenaire">
          <HBarChart data={[...PARTNERS].sort((a, b) => b.commitmentFcfa - a.commitmentFcfa).map((p) => ({ label: p.shortName, value: p.commitmentFcfa, display: fmtMFcfa(p.commitmentFcfa) }))} />
        </Card>
        <Card title="Liste des partenaires" className="lg:col-span-2">
          <Table head={["Partenaire", "Type", "Régions", "Secteurs", "Engagement", "Projets", "Point focal"]} dense>
            {PARTNERS.map((p) => (
              <tr key={p.id}>
                <td className="pr-4"><div className="font-medium">{p.shortName}</div><div className="text-[11px] text-ink-3">{p.name}</div></td>
                <td className="pr-4 text-ink-2">{p.type}</td>
                <td className="pr-4 text-ink-2">{p.regions.map((r) => REGIONS.find((x) => x.id === r)!.name).join(", ")}</td>
                <td className="pr-4"><div className="flex flex-wrap gap-1">{p.sectors.map((s) => <Badge key={s} icon={false}>{s}</Badge>)}</div></td>
                <td className="pr-4 tabular-nums">{fmtMFcfa(p.commitmentFcfa)}</td>
                <td className="pr-4 tabular-nums">{p.activeProjects}</td>
                <td className="pr-4 text-ink-2 text-xs">{p.focalPoint}</td>
              </tr>
            ))}
          </Table>
        </Card>
      </div>
    </>
  );
}
