"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Select, Search } from "./filter-bar";
import { Badge, StatusBadge, Table } from "./ui";
import { fmtDate } from "@/lib/format";
import { GRM_CATEGORIES, GRM_CHANNELS, GRM_STATUSES } from "@/data/grm";

export type GrmRow = { id: string; code: string; category: string; channel: string; status: string; level: string; severity: string; receivedAt: string; daysOpen: number; slaDays: number; summary: string; assignedTo: string; sensitive: boolean; complainant: string; village: string; villageId: string; canton: string; region: string; investmentCode?: string; investmentId?: string; satisfaction?: number };

export function GrmTable({ rows, regions }: { rows: GrmRow[]; regions: string[] }) {
  const [q, setQ] = useState("");
  const [region, setRegion] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [channel, setChannel] = useState("");
  const [onlyLate, setOnlyLate] = useState(false);
  const filtered = useMemo(() => {
    const t = q.trim().toLowerCase();
    return rows.filter((r) => (!region || r.region === region) && (!category || r.category === category) && (!status || r.status === status) && (!channel || r.channel === channel) && (!onlyLate || (r.daysOpen > r.slaDays && !["Résolue", "Clôturée"].includes(r.status))))
      .filter((r) => !t || [r.code, r.village, r.canton, r.summary].some((s) => s.toLowerCase().includes(t)));
  }, [rows, q, region, category, status, channel, onlyLate]);
  return (
    <div>
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <Search value={q} onChange={setQ} placeholder="Code, village, résumé…" />
        <Select label="Région" value={region} onChange={setRegion} options={regions} />
        <Select label="Catégorie" value={category} onChange={setCategory} options={[...GRM_CATEGORIES]} />
        <Select label="Statut" value={status} onChange={setStatus} options={[...GRM_STATUSES]} />
        <Select label="Canal" value={channel} onChange={setChannel} options={[...GRM_CHANNELS]} />
        <label className="text-xs text-ink-2 flex items-center gap-2 pb-2"><input type="checkbox" checked={onlyLate} onChange={(e) => setOnlyLate(e.target.checked)} /> Hors délai uniquement</label>
      </div>
      <div className="text-xs text-ink-2 mb-2">{filtered.length} plainte(s)</div>
      <Table head={["Code", "Reçue", "Catégorie · résumé", "Village · canton", "Canal", "Niveau", "Gravité", "Délai", "Assignée à", "Statut"]} dense>
        {filtered.map((r) => {
          const open = !["Résolue", "Clôturée"].includes(r.status);
          const late = open && r.daysOpen > r.slaDays;
          return (
            <tr key={r.id} className={`hover:bg-surface ${r.sensitive ? "bg-red-50/40" : ""}`}>
              <td className="pr-4 font-mono text-xs">{r.code}</td>
              <td className="pr-4 text-ink-2 whitespace-nowrap">{fmtDate(r.receivedAt)}</td>
              <td className="pr-4 max-w-md">
                <div className="font-medium text-xs">{r.sensitive ? <span className="inline-flex items-center gap-1 text-red-800">🔒 Plainte sensible (VBG/EAS/HS)</span> : r.category}</div>
                <div className="text-xs text-ink-2 truncate">{r.summary}</div>
                {r.investmentId && <Link href={`/investissements/${r.investmentId}`} className="text-[11px] text-brand-700 hover:underline">Lié à {r.investmentCode}</Link>}
              </td>
              <td className="pr-4"><Link href={`/territoires/villages/${r.villageId}`} className="text-brand-700 hover:underline">{r.village}</Link><span className="text-ink-3 text-xs"> · {r.canton}</span></td>
              <td className="pr-4 text-xs text-ink-2">{r.channel}</td>
              <td className="pr-4 text-xs text-ink-2">{r.level}</td>
              <td className="pr-4"><StatusBadge status={r.severity} /></td>
              <td className="pr-4 text-xs tabular-nums">{open ? <span className={late ? "text-red-700 font-medium" : ""}>{r.daysOpen} j / {r.slaDays} j{late && " ⚠"}</span> : <span className="text-ink-3">{r.daysOpen} j</span>}</td>
              <td className="pr-4 text-xs text-ink-2">{r.assignedTo}</td>
              <td className="pr-4"><div className="flex flex-col gap-1 items-start"><StatusBadge status={r.status} />{r.satisfaction && <Badge tone="neutral" icon={false}>Satisf. {r.satisfaction}/5</Badge>}</div></td>
            </tr>
          );
        })}
      </Table>
    </div>
  );
}
