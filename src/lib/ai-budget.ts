// Daily token budget for the AI assistant (see planning-docs/ai-chat-for-development-partners-brief.md, §6 "Cost").
//
// One platform-wide cap, set by the UCP administrator, on the number of model
// tokens the assistant may consume per calendar day. The day rolls over at
// 00:00 UTC, which is also midnight in Lomé (Togo has no DST). When the cap is
// reached the agent must stop calling the model until the next reset.
//
// Enforcement contract for the agent loop: call `assertBudget` before every
// model call and `recordUsage` after it — or wrap the call with
// `withDailyBudget`, which does both. Because token counts are only known
// after a call completes, the last call of the day may overshoot the cap by
// its own size; `estimatedTokens` lets a caller pre-reserve and stay strictly
// under the cap when that matters.
//
// Storage is behind `BudgetStore` so the same logic runs against an in-memory
// store (tests, mockup), the browser (admin mockup page) or a database (prod).
// This file is dependency-free and runs unchanged under Node's type stripping,
// which is how the tests in tests/ load it.

/** Default cap: ~40 routine questions/day on a Sonnet-class model. Admin-adjustable. */
export const DEFAULT_DAILY_TOKEN_LIMIT = 2_000_000;
/** Upper bound accepted from the admin form: 10 billion tokens/day. */
export const MAX_DAILY_TOKEN_LIMIT = 10_000_000_000;
/** Usage ratio from which the admin UI shows a warning. */
export const WARNING_RATIO = 0.8;

/** Token counts as reported by the model API for one call. All kinds are billed, so all count. */
export type TokenUsage = {
  inputTokens: number;
  outputTokens: number;
  cacheCreationTokens?: number;
  cacheReadTokens?: number;
};

export type BudgetSettings = {
  dailyTokenLimit: number;
  /** ISO timestamp of the last change, null until an admin sets the limit. */
  updatedAt: string | null;
  /** Display name or id of the admin who made the last change. */
  updatedBy: string | null;
};

export type DailyUsage = {
  /** Budget day, `YYYY-MM-DD` in UTC. */
  day: string;
  tokens: number;
  calls: number;
};

export type BudgetStatus = {
  day: string;
  limit: number;
  used: number;
  remaining: number;
  calls: number;
  /** used / limit, 0..1 (capped at 1). */
  ratio: number;
  exhausted: boolean;
  /** ISO timestamp of the next reset (next 00:00 UTC). */
  resetsAt: string;
};

export interface BudgetStore {
  getSettings(): Promise<BudgetSettings>;
  saveSettings(settings: BudgetSettings): Promise<void>;
  getUsage(day: string): Promise<DailyUsage>;
  /** Atomically add one call's tokens to the day's counter and return the new totals. */
  addUsage(day: string, tokens: number): Promise<DailyUsage>;
}

export const DEFAULT_SETTINGS: BudgetSettings = { dailyTokenLimit: DEFAULT_DAILY_TOKEN_LIMIT, updatedAt: null, updatedBy: null };

export function emptyUsage(day: string): DailyUsage {
  return { day, tokens: 0, calls: 0 };
}

/** In-memory store: tests, local development and the mockup. Not shared across processes. */
export class MemoryBudgetStore implements BudgetStore {
  settings: BudgetSettings;
  usage: Map<string, DailyUsage> = new Map();

  constructor(settings: Partial<BudgetSettings> = {}) {
    this.settings = { ...DEFAULT_SETTINGS, ...settings };
  }
  async getSettings(): Promise<BudgetSettings> {
    return { ...this.settings };
  }
  async saveSettings(settings: BudgetSettings): Promise<void> {
    this.settings = { ...settings };
  }
  async getUsage(day: string): Promise<DailyUsage> {
    return { ...(this.usage.get(day) ?? emptyUsage(day)) };
  }
  async addUsage(day: string, tokens: number): Promise<DailyUsage> {
    const current = this.usage.get(day) ?? emptyUsage(day);
    const next = { day, tokens: current.tokens + tokens, calls: current.calls + 1 };
    this.usage.set(day, next);
    return { ...next };
  }
}

/** Budget day for an instant: the UTC calendar date (= Lomé date). */
export function budgetDay(now: Date = new Date()): string {
  return now.toISOString().slice(0, 10);
}

/** Next reset: the first 00:00 UTC strictly after `now`. */
export function nextReset(now: Date = new Date()): Date {
  const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1));
  return d;
}

export function totalTokens(usage: TokenUsage): number {
  const parts = [usage.inputTokens, usage.outputTokens, usage.cacheCreationTokens ?? 0, usage.cacheReadTokens ?? 0];
  for (const p of parts) {
    if (!Number.isFinite(p) || p < 0) throw new TypeError(`Invalid token count: ${p}`);
  }
  return parts.reduce((a, b) => a + b, 0);
}

export function buildStatus(settings: BudgetSettings, usage: DailyUsage, now: Date): BudgetStatus {
  const limit = settings.dailyTokenLimit;
  const used = usage.tokens;
  return {
    day: usage.day,
    limit,
    used,
    remaining: Math.max(0, limit - used),
    calls: usage.calls,
    ratio: limit > 0 ? Math.min(1, used / limit) : 1,
    exhausted: used >= limit,
    resetsAt: nextReset(now).toISOString(),
  };
}

export async function getBudgetStatus(store: BudgetStore, now: Date = new Date()): Promise<BudgetStatus> {
  const day = budgetDay(now);
  const [settings, usage] = await Promise.all([store.getSettings(), store.getUsage(day)]);
  return buildStatus(settings, usage, now);
}

export class DailyTokenLimitExceededError extends Error {
  status: BudgetStatus;
  constructor(status: BudgetStatus) {
    super(`Daily AI token limit reached (${status.used} / ${status.limit} tokens used on ${status.day}); resets at ${status.resetsAt}`);
    this.name = "DailyTokenLimitExceededError";
    this.status = status;
  }
}

/**
 * Gate to run before every model call. Resolves with the current status when
 * the call may proceed; throws `DailyTokenLimitExceededError` when the day's
 * cap is reached, or when `estimatedTokens` would push usage past it.
 */
export async function assertBudget(store: BudgetStore, opts: { estimatedTokens?: number; now?: Date } = {}): Promise<BudgetStatus> {
  const status = await getBudgetStatus(store, opts.now);
  const estimated = opts.estimatedTokens ?? 0;
  if (status.exhausted || status.used + estimated > status.limit) throw new DailyTokenLimitExceededError(status);
  return status;
}

/** Book one completed model call against today's budget. */
export async function recordUsage(store: BudgetStore, usage: TokenUsage, now: Date = new Date()): Promise<BudgetStatus> {
  const day = budgetDay(now);
  const [settings, updated] = await Promise.all([store.getSettings(), store.addUsage(day, totalTokens(usage))]);
  return buildStatus(settings, updated, now);
}

/** Check → call → record. `call` must return the model API's usage for the request it made. */
export async function withDailyBudget<T extends { usage: TokenUsage }>(
  store: BudgetStore,
  call: () => Promise<T>,
  opts: { estimatedTokens?: number; now?: () => Date } = {},
): Promise<T> {
  const clock = opts.now ?? (() => new Date());
  await assertBudget(store, { estimatedTokens: opts.estimatedTokens, now: clock() });
  const result = await call();
  await recordUsage(store, result.usage, clock());
  return result;
}

export type LimitValidation = { ok: true; value: number } | { ok: false; reason: string };

/** `1234567` → `1 234 567`. Locale-independent, like src/lib/format.ts. */
export function groupDigits(n: number): string {
  return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

/** Validate an admin-supplied limit. Accepts numbers or digit strings with optional spaces/underscores. */
export function validateDailyTokenLimit(input: unknown): LimitValidation {
  let value: number;
  if (typeof input === "string") {
    const cleaned = input.replace(/[\s_  ]/g, "");
    if (!/^\d+$/.test(cleaned)) return { ok: false, reason: "Le plafond doit être un nombre entier de jetons." };
    value = Number(cleaned);
  } else if (typeof input === "number") {
    value = input;
  } else {
    return { ok: false, reason: "Le plafond doit être un nombre entier de jetons." };
  }
  if (!Number.isSafeInteger(value)) return { ok: false, reason: "Le plafond doit être un nombre entier de jetons." };
  if (value < 1) return { ok: false, reason: "Le plafond doit être d'au moins 1 jeton par jour." };
  if (value > MAX_DAILY_TOKEN_LIMIT) return { ok: false, reason: `Le plafond ne peut pas dépasser ${groupDigits(MAX_DAILY_TOKEN_LIMIT)} jetons par jour.` };
  return { ok: true, value };
}

/** Admin action: set the daily cap. Takes effect immediately, including for the current day. */
export async function setDailyTokenLimit(store: BudgetStore, input: unknown, updatedBy: string, now: Date = new Date()): Promise<BudgetSettings> {
  const check = validateDailyTokenLimit(input);
  if (!check.ok) throw new RangeError(check.reason);
  const settings: BudgetSettings = { dailyTokenLimit: check.value, updatedAt: now.toISOString(), updatedBy };
  await store.saveSettings(settings);
  return settings;
}
