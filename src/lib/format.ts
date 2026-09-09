// Locale-independent formatters (avoid Intl differences between server and client).
export function fmtInt(n: number): string {
  const s = Math.round(Math.abs(n)).toString();
  const grouped = s.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return (n < 0 ? "-" : "") + grouped;
}
export function fmtFcfa(n: number): string {
  return `${fmtInt(n)} FCFA`;
}
export function fmtMFcfa(n: number): string {
  const m = n / 1_000_000;
  if (m >= 10_000) return `${(m / 1000).toFixed(1).replace(".", ",")} Md FCFA`;
  return `${m >= 100 ? fmtInt(m) : m.toFixed(1).replace(".", ",")} M FCFA`;
}
export function fmtPct(n: number, digits = 0): string {
  return `${n.toFixed(digits).replace(".", ",")} %`;
}
export function fmtDate(iso?: string): string {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}
export function daysBetween(a: string, b: string): number {
  const da = new Date(a + "T00:00:00Z").getTime();
  const db = new Date(b + "T00:00:00Z").getTime();
  return Math.round((db - da) / 86_400_000);
}
export function addDays(iso: string, days: number): string {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}
export const TODAY = "2026-09-09";
