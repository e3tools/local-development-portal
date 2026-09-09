"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Select, Search } from "./filter-bar";
import { StatusBadge, Table } from "./ui";
import { fmtInt, fmtMFcfa } from "@/lib/format";
import { SECTOR_COLOR, SECTORS, type Sector } from "@/data/sectors";
import { MAX_PRIORITIES_PER_VILLAGE, PRIORITY_STATUSES } from "@/data/priorities";

export type PriorityRow = { id: string; code: string; title: string; sector: Sector; rank: number; status: string; source: string; cost: number; beneficiaries: number; votes: number; village: string; villageId: string; canton: string; prefecture: string; region: string; registeredAt: string };

const RANKS = Array.from({ length: MAX_PRIORITIES_PER_VILLAGE }, (_, i) => String(i + 1));

export function PrioritiesTable({ rows, regions }: { rows: PriorityRow[]; regions: string[] }) {
  const [q, setQ] = useState("");
  const [region, setRegion] = useState("");
  const [sector, setSector] = useState("");
  const [status, setStatus] = useState("");
  const [rank, setRank] = useState("");
  const [sort, setSort] = useState<"votes" | "cost" | "date">("date");
  const filtered = useMemo(() => {
    const t = q.trim().toLowerCase();
    return rows
      .filter((r) => (!region || r.region === region) && (!sector || r.sector === sector) && (!status || r.status === status) && (!rank || String(r.rank) === rank))
      .filter((r) => !t || [r.title, r.village, r.canton, r.prefecture, r.code].some((s) => s.toLowerCase().includes(t)))
      .sort((a, b) => (sort === "votes" ? b.votes - a.votes : sort === "cost" ? b.cost - a.cost : a.registeredAt < b.registeredAt ? 1 : -1));
  }, [rows, q, region, sector, status, rank, sort]);
  const total = filtered.reduce((s, r) => s + r.cost, 0);
  return (
    <div>
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <Search value={q} onChange={setQ} placeholder="Village, canton, intitulé, code…" />
        <Select label="Région" value={region} onChange={setRegion} options={regions} />
        <Select label="Secteur" value={sector} onChange={setSector} options={[...SECTORS]} />
        <Select label="Statut" value={status} onChange={setStatus} options={[...PRIORITY_STATUSES]} />
        <Select label="Rang" value={rank} onChange={setRank} options={RANKS} />
        <label className="text-xs text-ink-2 flex flex-col gap-1">Tri
          <select value={sort} onChange={(e) => setSort(e.target.value as typeof sort)} className="rounded-md border border-line bg-white px-2 py-1.5 text-sm text-ink">
            <option value="date">Plus récentes</option><option value="votes">Plus de voix</option><option value="cost">Coût décroissant</option>
          </select>
        </label>
      </div>
      <div className="text-xs text-ink-2 mb-2">{fmtInt(filtered.length)} priorité(s) · coût estimé cumulé {fmtMFcfa(total)}</div>
      <Table head={["Code", "Priorité", "Secteur", "Rang", "Village · canton · préfecture", "Région", "Source", "Coût estimé", "Bénéf.", "Voix", "Statut"]} dense>
        {filtered.slice(0, 150).map((r) => (
          <tr key={r.id} className="hover:bg-surface">
            <td className="pr-4 font-mono text-xs">{r.code}</td>
            <td className="pr-4 font-medium">{r.title}</td>
            <td className="pr-4"><span className="inline-flex items-center gap-1.5 text-xs whitespace-nowrap"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: SECTOR_COLOR[r.sector] }} />{r.sector}</span></td>
            <td className="pr-4 tabular-nums">#{r.rank}</td>
            <td className="pr-4"><Link href={`/territoires/villages/${r.villageId}`} className="text-brand-700 hover:underline">{r.village}</Link><span className="text-ink-3 text-xs"> · {r.canton} · {r.prefecture}</span></td>
            <td className="pr-4 text-ink-2">{r.region}</td>
            <td className="pr-4 text-ink-2 text-xs">{r.source}</td>
            <td className="pr-4 tabular-nums">{fmtMFcfa(r.cost)}</td>
            <td className="pr-4 tabular-nums">{fmtInt(r.beneficiaries)}</td>
            <td className="pr-4 tabular-nums">{r.votes}</td>
            <td className="pr-4"><StatusBadge status={r.status} /></td>
          </tr>
        ))}
      </Table>
      {filtered.length > 150 && <p className="text-xs text-ink-3 mt-2">Affichage limité aux 150 premières lignes. Affinez les filtres.</p>}
    </div>
  );
}
