import Link from "next/link";
import type { ReactNode } from "react";

export type Tone = "good" | "warning" | "serious" | "critical" | "neutral" | "info" | "violet";
const TONE: Record<Tone, string> = {
  good: "bg-green-50 text-green-800 border-green-200",
  warning: "bg-amber-50 text-amber-800 border-amber-200",
  serious: "bg-orange-50 text-orange-800 border-orange-200",
  critical: "bg-red-50 text-red-800 border-red-200",
  neutral: "bg-gray-100 text-gray-700 border-gray-200",
  info: "bg-blue-50 text-blue-800 border-blue-200",
  violet: "bg-violet-50 text-violet-800 border-violet-200",
};
const ICON: Record<Tone, string> = { good: "●", warning: "▲", serious: "◆", critical: "■", neutral: "○", info: "●", violet: "●" };

export function Badge({ tone = "neutral", children, icon = true }: { tone?: Tone; children: ReactNode; icon?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap ${TONE[tone]}`}>
      {icon && <span aria-hidden className="text-[8px]">{ICON[tone]}</span>}
      {children}
    </span>
  );
}

export const STATUS_TONE: Record<string, Tone> = {
  // priorities
  "Identifiée": "neutral", "Validée CCD": "info", "Intégrée au PDC": "violet", "Financée": "good", "Non retenue": "critical",
  // investments
  "Soumis": "neutral", "Validation CCD": "info", "Revue communale": "info", "Revue régionale": "info", "Approbation UCP": "warning", "Approuvé": "violet", "En exécution": "info", "Achevé": "good", "Rejeté": "critical",
  // steps
  "Terminé": "good", "En cours": "warning", "En attente": "neutral",
  // grm
  "Reçue": "neutral", "Recevabilité": "info", "En traitement": "warning", "Résolue": "good", "Escaladée": "serious", "Clôturée": "good",
  "Faible": "neutral", "Moyenne": "warning", "Élevée": "critical",
  // users
  "Actif": "good", "Invité": "info", "Suspendu": "critical",
};
export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={STATUS_TONE[status] ?? "neutral"}>{status}</Badge>;
}

export function Card({ title, subtitle, action, children, className = "" }: { title?: ReactNode; subtitle?: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`bg-white border border-line rounded-xl ${className}`}>
      {(title || action) && (
        <header className="flex items-start justify-between gap-3 px-5 pt-4 pb-3 border-b border-line">
          <div>
            {title && <h2 className="text-sm font-semibold text-ink">{title}</h2>}
            {subtitle && <p className="text-xs text-ink-3 mt-0.5">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className="px-5 py-4">{children}</div>
    </section>
  );
}

export function Kpi({ label, value, sub, tone }: { label: string; value: ReactNode; sub?: ReactNode; tone?: Tone }) {
  const bar = tone ? { good: "bg-green-600", warning: "bg-amber-500", serious: "bg-orange-500", critical: "bg-red-600", neutral: "bg-gray-400", info: "bg-blue-600", violet: "bg-violet-600" }[tone] : "bg-brand-600";
  return (
    <div className="bg-white border border-line rounded-xl px-4 py-3 flex gap-3">
      <div className={`w-1 rounded-full ${bar}`} />
      <div className="min-w-0">
        <div className="text-[11px] uppercase tracking-wide text-ink-3">{label}</div>
        <div className="text-2xl font-semibold tabular-nums leading-tight mt-0.5">{value}</div>
        {sub && <div className="text-xs text-ink-2 mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

export function Progress({ value, color = "#2a78d6", label }: { value: number; color?: string; label?: string }) {
  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full rounded-full" style={{ width: `${Math.min(100, value)}%`, background: color }} />
      </div>
      <span className="text-xs tabular-nums text-ink-2 w-10 text-right">{label ?? `${Math.round(value)} %`}</span>
    </div>
  );
}

export function PageHeader({ title, subtitle, crumbs, action }: { title: ReactNode; subtitle?: ReactNode; crumbs?: { href?: string; label: string }[]; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        {crumbs && (
          <nav className="text-xs text-ink-3 mb-1 flex flex-wrap gap-1">
            {crumbs.map((c, i) => (
              <span key={i} className="flex gap-1">
                {i > 0 && <span>/</span>}
                {c.href ? <Link className="hover:text-brand-700 hover:underline" href={c.href as never}>{c.label}</Link> : <span className="text-ink-2">{c.label}</span>}
              </span>
            ))}
          </nav>
        )}
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="text-sm text-ink-2 mt-1 max-w-3xl">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function Table({ head, children, dense }: { head: ReactNode[]; children: ReactNode; dense?: boolean }) {
  return (
    <div className="overflow-x-auto -mx-5 px-5">
      <table className={`w-full text-sm ${dense ? "[&_td]:py-1.5 [&_th]:py-1.5" : "[&_td]:py-2.5 [&_th]:py-2"}`}>
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-wide text-ink-3 border-b border-line">
            {head.map((h, i) => <th key={i} className="pr-4 font-medium">{h}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">{children}</tbody>
      </table>
    </div>
  );
}

export function Dl({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-1 gap-y-1 text-sm">
      {items.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-4 border-b border-dashed border-line py-1">
          <dt className="text-ink-3">{k}</dt>
          <dd className="text-right font-medium">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Yes({ v }: { v: boolean }) {
  return v ? <Badge tone="good">Oui</Badge> : <Badge tone="critical">Non</Badge>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="text-sm text-ink-3 italic">{children}</p>;
}

export function Btn({ children, primary, href }: { children: ReactNode; primary?: boolean; href?: string }) {
  const cls = `inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium border ${primary ? "bg-brand-700 border-brand-700 text-white hover:bg-brand-800" : "bg-white border-line text-ink hover:bg-surface"}`;
  return href ? <Link href={href as never} className={cls}>{children}</Link> : <button type="button" className={cls}>{children}</button>;
}
