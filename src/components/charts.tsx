import { fmtInt } from "@/lib/format";

export type BarDatum = { label: string; value: number; color?: string; display?: string };

/** Horizontal bar chart: thin rounded marks, direct labels, native tooltips on hover. */
export function HBarChart({ data, color = "#2a78d6", max, unit = "" }: { data: BarDatum[]; color?: string; max?: number; unit?: string }) {
  const m = max ?? Math.max(1, ...data.map((d) => d.value));
  return (
    <div className="space-y-2">
      {data.map((d) => (
        <div key={d.label} className="grid grid-cols-[minmax(110px,1fr)_3fr_auto] items-center gap-3 text-sm group" title={`${d.label} : ${d.display ?? fmtInt(d.value) + unit}`}>
          <div className="truncate text-ink-2 text-xs">{d.label}</div>
          <div className="h-3 bg-gray-100 rounded-sm">
            <div className="h-full rounded-r-[4px] group-hover:opacity-80 transition-opacity" style={{ width: `${(d.value / m) * 100}%`, background: d.color ?? color, minWidth: d.value > 0 ? 2 : 0 }} />
          </div>
          <div className="text-xs tabular-nums text-ink-2 w-20 text-right">{d.display ?? fmtInt(d.value) + unit}</div>
        </div>
      ))}
    </div>
  );
}

/** 100% stacked distribution with 2px gaps and a legend (identity never color-alone). */
export function Distribution({ parts }: { parts: { label: string; value: number; color: string }[] }) {
  const total = parts.reduce((s, p) => s + p.value, 0) || 1;
  return (
    <div>
      <div className="flex h-4 rounded-md overflow-hidden gap-[2px] bg-white">
        {parts.filter((p) => p.value > 0).map((p) => (
          <div key={p.label} title={`${p.label} : ${fmtInt(p.value)} (${Math.round((p.value / total) * 100)} %)`} style={{ width: `${(p.value / total) * 100}%`, background: p.color }} className="hover:opacity-80" />
        ))}
      </div>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
        {parts.map((p) => (
          <li key={p.label} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: p.color }} />
            {p.label} <span className="tabular-nums text-ink-3">{fmtInt(p.value)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Small SVG line chart (single series: no legend needed). */
export function Sparkline({ points, color = "#2a78d6", height = 56, labels }: { points: number[]; color?: string; height?: number; labels?: string[] }) {
  const w = 320;
  const max = Math.max(1, ...points);
  const step = w / Math.max(1, points.length - 1);
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${(i * step).toFixed(1)},${(height - 4 - (p / max) * (height - 8)).toFixed(1)}`).join(" ");
  return (
    <div>
      <svg viewBox={`0 0 ${w} ${height}`} className="w-full h-auto" role="img" aria-label="Évolution">
        <path d={path} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" />
        {points.map((p, i) => (
          <circle key={i} cx={i * step} cy={height - 4 - (p / max) * (height - 8)} r={4} fill={color} stroke="#fff" strokeWidth={2}>
            <title>{labels?.[i] ? `${labels[i]} : ${p}` : String(p)}</title>
          </circle>
        ))}
      </svg>
      {labels && (
        <div className="flex justify-between text-[10px] text-ink-3 mt-1">
          <span>{labels[0]}</span><span>{labels[labels.length - 1]}</span>
        </div>
      )}
    </div>
  );
}
