"use client";
export function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <label className="text-xs text-ink-2 flex flex-col gap-1">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)} className="rounded-md border border-line bg-white px-2 py-1.5 text-sm text-ink min-w-[160px]">
        <option value="">Tous</option>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  );
}
export function Search({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <label className="text-xs text-ink-2 flex flex-col gap-1 flex-1 min-w-[200px]">
      Recherche
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className="rounded-md border border-line bg-white px-2 py-1.5 text-sm" />
    </label>
  );
}
