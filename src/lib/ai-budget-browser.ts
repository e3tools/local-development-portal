// Browser-side BudgetStore for the mockup: settings and daily counters live in
// localStorage so the admin page survives a reload. Production swaps this for a
// database-backed store behind the same interface (see src/lib/ai-budget.ts).
import { DEFAULT_SETTINGS, emptyUsage, type BudgetSettings, type BudgetStore, type DailyUsage } from "@/lib/ai-budget";

const KEY = "ldp.ai-budget.v1";
const KEEP_DAYS = 14;

type Persisted = { settings: BudgetSettings; usage: Record<string, DailyUsage> };

function read(): Persisted {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<Persisted>;
      return { settings: { ...DEFAULT_SETTINGS, ...(parsed.settings ?? {}) }, usage: parsed.usage ?? {} };
    }
  } catch {
    // Private mode, blocked storage or corrupt payload: fall through to defaults.
  }
  return { settings: { ...DEFAULT_SETTINGS }, usage: {} };
}

function write(p: Persisted): void {
  const days = Object.keys(p.usage).sort().slice(-KEEP_DAYS);
  const usage: Record<string, DailyUsage> = {};
  for (const d of days) usage[d] = p.usage[d];
  try {
    window.localStorage.setItem(KEY, JSON.stringify({ settings: p.settings, usage }));
  } catch {
    // Storage unavailable: the page still works for the current visit.
  }
}

export class LocalStorageBudgetStore implements BudgetStore {
  async getSettings(): Promise<BudgetSettings> {
    return read().settings;
  }
  async saveSettings(settings: BudgetSettings): Promise<void> {
    const p = read();
    write({ ...p, settings });
  }
  async getUsage(day: string): Promise<DailyUsage> {
    return read().usage[day] ?? emptyUsage(day);
  }
  async addUsage(day: string, tokens: number): Promise<DailyUsage> {
    const p = read();
    const current = p.usage[day] ?? emptyUsage(day);
    const next = { day, tokens: current.tokens + tokens, calls: current.calls + 1 };
    write({ ...p, usage: { ...p.usage, [day]: next } });
    return next;
  }
  /** Demo helper: clear one day's counter. */
  async resetUsage(day: string): Promise<void> {
    const p = read();
    const usage = { ...p.usage };
    delete usage[day];
    write({ ...p, usage });
  }
}
