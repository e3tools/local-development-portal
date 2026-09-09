export function countBy<T>(arr: T[], key: (t: T) => string): Record<string, number> {
  const out: Record<string, number> = {};
  for (const a of arr) out[key(a)] = (out[key(a)] ?? 0) + 1;
  return out;
}
export function sumBy<T>(arr: T[], key: (t: T) => number): number {
  return arr.reduce((s, a) => s + key(a), 0);
}
