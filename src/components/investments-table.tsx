"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Select, Search } from "./filter-bar";
import { Progress, StatusBadge, Table } from "./ui";
import { fmtMFcfa, fmtDate } from "@/lib/format";
import { SECTOR_COLOR, SECTORS, type Sector } from "@/data/sectors";
import { INVESTMENT_STATUSES } from "@/data/investments";

export type InvestmentRow = { id: string; code: string; title: string; sector: Sector; status: string; budget: number; disbursed: number; progress: number; village: string; villageId: string; canton: string; region: string; partner: string; submittedAt: string; currentStep: string; pendingActor: string };

export function InvestmentsTable({ rows, regions, partners }: { rows: InvestmentRow[]; regions: string[]; partners: string[] }) {
  const [q, setQ] = useState("");
  const [region, setRegion] = useState("");
  const [sector, setSector] = useState("");
  const [status, setStatus] = useState("");
  const [partner, setPartner] = useState("");
  const filtered = useMemo(() => {
    const t = q.trim().toLowerCase();
    return rows.filter((r) => (!region || r.region === region) && (!sector || r.sector === sector) && (!status || r.status === status) && (!partner || r.partner === partner))
      .filter((r) => !t || [r.title, r.village, r.canton, r.code].some((s) => s.toLowerCase().includes(t)));
  }, [rows, q, region, sector, status, partner]);
  return (
    <div>
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <Search value={q} onChange={setQ} placeholder="Code, intitulé, village…" />
        <Select label="Région" value={region} onChange={setRegion} options={regions} />
        <Select label="Secteur" value={sector} onChange={setSector} options={[...SECTORS]} />
        <Select label="Statut" value={status} onChange={setStatus} options={[...INVESTMENT_STATUSES]} />
        <Select label="Partenaire" value={partner} onChange={setPartner} options={partners} />
      </div>
      <div className="text-xs text-ink-2 mb-2">{filtered.length} paquet(s) · budget {fmtMFcfa(filtered.reduce((s, r) => s + r.budget, 0))}</div>
      <Table head={["Code", "Sous-projet", "Secteur", "Village · canton", "Région", "Partenaire", "Budget", "Décaissé", "Avancement", "Étape en cours", "Statut"]} dense>
        {filtered.map((r) => (
          <tr key={r.id} className="hover:bg-surface">
            <td className="pr-4 font-mono text-xs">{r.code}</td>
            <td className="pr-4"><Link href={`/investissements/${r.id}`} className="font-medium text-brand-700 hover:underline">{r.title}</Link><div className="text-[11px] text-ink-3">Soumis le {fmtDate(r.submittedAt)}</div></td>
            <td className="pr-4"><span className="inline-flex items-center gap-1.5 text-xs whitespace-nowrap"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: SECTOR_COLOR[r.sector] }} />{r.sector}</span></td>
            <td className="pr-4"><Link href={`/territoires/villages/${r.villageId}`} className="text-brand-700 hover:underline">{r.village}</Link><span className="text-ink-3 text-xs"> · {r.canton}</span></td>
            <td className="pr-4 text-ink-2">{r.region}</td>
            <td className="pr-4 text-ink-2">{r.partner}</td>
            <td className="pr-4 tabular-nums">{fmtMFcfa(r.budget)}</td>
            <td className="pr-4 tabular-nums">{r.disbursed ? fmtMFcfa(r.disbursed) : "—"}</td>
            <td className="pr-4">{r.progress > 0 ? <Progress value={r.progress} color="#1baf7a" /> : <span className="text-ink-3 text-xs">—</span>}</td>
            <td className="pr-4 text-xs"><div>{r.currentStep}</div><div className="text-ink-3">{r.pendingActor}</div></td>
            <td className="pr-4"><StatusBadge status={r.status} /></td>
          </tr>
        ))}
      </Table>
    </div>
  );
}
