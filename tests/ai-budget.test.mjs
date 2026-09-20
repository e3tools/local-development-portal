// Runs with `npm test` (node --test, TypeScript loaded through Node's type stripping).
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_DAILY_TOKEN_LIMIT,
  MAX_DAILY_TOKEN_LIMIT,
  MemoryBudgetStore,
  DailyTokenLimitExceededError,
  assertBudget,
  budgetDay,
  getBudgetStatus,
  nextReset,
  recordUsage,
  setDailyTokenLimit,
  totalTokens,
  validateDailyTokenLimit,
  withDailyBudget,
} from "../src/lib/ai-budget.ts";

const T = (iso) => new Date(iso);

test("budget day is the UTC calendar date and resets at the next 00:00 UTC", () => {
  assert.equal(budgetDay(T("2026-09-20T23:59:59.999Z")), "2026-09-20");
  assert.equal(budgetDay(T("2026-09-21T00:00:00.000Z")), "2026-09-21");
  assert.equal(nextReset(T("2026-09-20T10:15:00Z")).toISOString(), "2026-09-21T00:00:00.000Z");
  assert.equal(nextReset(T("2026-09-20T00:00:00Z")).toISOString(), "2026-09-21T00:00:00.000Z");
  assert.equal(nextReset(T("2026-12-31T18:00:00Z")).toISOString(), "2027-01-01T00:00:00.000Z");
});

test("every billed token kind counts toward the cap", () => {
  assert.equal(totalTokens({ inputTokens: 100, outputTokens: 50 }), 150);
  assert.equal(totalTokens({ inputTokens: 100, outputTokens: 50, cacheCreationTokens: 20, cacheReadTokens: 30 }), 200);
  assert.throws(() => totalTokens({ inputTokens: -1, outputTokens: 0 }), TypeError);
  assert.throws(() => totalTokens({ inputTokens: NaN, outputTokens: 0 }), TypeError);
});

test("status reflects the default limit and an empty day", async () => {
  const store = new MemoryBudgetStore();
  const s = await getBudgetStatus(store, T("2026-09-20T08:00:00Z"));
  assert.equal(s.limit, DEFAULT_DAILY_TOKEN_LIMIT);
  assert.equal(s.used, 0);
  assert.equal(s.remaining, DEFAULT_DAILY_TOKEN_LIMIT);
  assert.equal(s.calls, 0);
  assert.equal(s.ratio, 0);
  assert.equal(s.exhausted, false);
  assert.equal(s.resetsAt, "2026-09-21T00:00:00.000Z");
});

test("usage accumulates within the day and blocks calls once the cap is reached", async () => {
  const store = new MemoryBudgetStore({ dailyTokenLimit: 1000 });
  const now = T("2026-09-20T09:00:00Z");

  let s = await recordUsage(store, { inputTokens: 400, outputTokens: 200 }, now);
  assert.equal(s.used, 600);
  assert.equal(s.remaining, 400);
  assert.equal(s.calls, 1);
  assert.equal(s.exhausted, false);
  await assert.doesNotReject(assertBudget(store, { now }));

  s = await recordUsage(store, { inputTokens: 300, outputTokens: 200 }, now); // overshoots: 1100
  assert.equal(s.used, 1100);
  assert.equal(s.remaining, 0);
  assert.equal(s.ratio, 1);
  assert.equal(s.exhausted, true);

  await assert.rejects(assertBudget(store, { now }), (err) => {
    assert.ok(err instanceof DailyTokenLimitExceededError);
    assert.equal(err.status.used, 1100);
    assert.equal(err.status.resetsAt, "2026-09-21T00:00:00.000Z");
    return true;
  });
});

test("an estimated call size can pre-reserve budget and be refused before the call", async () => {
  const store = new MemoryBudgetStore({ dailyTokenLimit: 1000 });
  const now = T("2026-09-20T09:00:00Z");
  await recordUsage(store, { inputTokens: 900, outputTokens: 0 }, now);
  await assert.doesNotReject(assertBudget(store, { now, estimatedTokens: 100 }));
  await assert.rejects(assertBudget(store, { now, estimatedTokens: 101 }), DailyTokenLimitExceededError);
});

test("the counter resets on the next UTC day", async () => {
  const store = new MemoryBudgetStore({ dailyTokenLimit: 1000 });
  await recordUsage(store, { inputTokens: 1000, outputTokens: 0 }, T("2026-09-20T23:30:00Z"));
  await assert.rejects(assertBudget(store, { now: T("2026-09-20T23:59:59Z") }), DailyTokenLimitExceededError);

  const s = await getBudgetStatus(store, T("2026-09-21T00:00:00Z"));
  assert.equal(s.day, "2026-09-21");
  assert.equal(s.used, 0);
  assert.equal(s.exhausted, false);
  await assert.doesNotReject(assertBudget(store, { now: T("2026-09-21T00:00:00Z") }));
});

test("withDailyBudget checks before and records after the model call", async () => {
  const store = new MemoryBudgetStore({ dailyTokenLimit: 500 });
  let clock = T("2026-09-20T10:00:00Z");
  const opts = { now: () => clock };
  let calls = 0;
  const model = async () => {
    calls += 1;
    return { text: "ok", usage: { inputTokens: 200, outputTokens: 100 } };
  };

  const r1 = await withDailyBudget(store, model, opts);
  assert.equal(r1.text, "ok");
  const r2 = await withDailyBudget(store, model, opts); // 600 > 500 after this one
  assert.equal(r2.text, "ok");
  await assert.rejects(withDailyBudget(store, model, opts), DailyTokenLimitExceededError);
  assert.equal(calls, 2, "the model is not called once the cap is reached");

  clock = T("2026-09-21T00:00:01Z");
  await assert.doesNotReject(withDailyBudget(store, model, opts));
  assert.equal(calls, 3);
});

test("a failed model call books nothing", async () => {
  const store = new MemoryBudgetStore({ dailyTokenLimit: 500 });
  const now = T("2026-09-20T10:00:00Z");
  await assert.rejects(withDailyBudget(store, async () => { throw new Error("upstream"); }, { now: () => now }), /upstream/);
  assert.equal((await getBudgetStatus(store, now)).used, 0);
});

test("validateDailyTokenLimit accepts integers and formatted strings, rejects the rest", () => {
  assert.deepEqual(validateDailyTokenLimit(2_000_000), { ok: true, value: 2_000_000 });
  assert.deepEqual(validateDailyTokenLimit("2 000 000"), { ok: true, value: 2_000_000 });
  assert.deepEqual(validateDailyTokenLimit("2 000 000"), { ok: true, value: 2_000_000 });
  assert.deepEqual(validateDailyTokenLimit("1"), { ok: true, value: 1 });
  assert.deepEqual(validateDailyTokenLimit(String(MAX_DAILY_TOKEN_LIMIT)), { ok: true, value: MAX_DAILY_TOKEN_LIMIT });
  for (const bad of [0, -5, 1.5, NaN, Infinity, "", "abc", "1e6", "-3", "2,5", null, undefined, {}, MAX_DAILY_TOKEN_LIMIT + 1]) {
    const v = validateDailyTokenLimit(bad);
    assert.equal(v.ok, false, `expected ${String(bad)} to be rejected`);
    assert.ok(v.reason.length > 0);
  }
});

test("the admin sets the limit, it is audited and applies to the current day at once", async () => {
  const store = new MemoryBudgetStore();
  const now = T("2026-09-20T11:00:00Z");
  await recordUsage(store, { inputTokens: 700, outputTokens: 0 }, now);

  const saved = await setDailyTokenLimit(store, "1 000", "Essohanam Tchagnao", now);
  assert.equal(saved.dailyTokenLimit, 1000);
  assert.equal(saved.updatedBy, "Essohanam Tchagnao");
  assert.equal(saved.updatedAt, now.toISOString());
  assert.deepEqual(await store.getSettings(), saved);

  let s = await getBudgetStatus(store, now);
  assert.equal(s.remaining, 300);
  assert.equal(s.exhausted, false);

  // Lowering below today's usage cuts the assistant off immediately.
  await setDailyTokenLimit(store, 500, "Essohanam Tchagnao", now);
  s = await getBudgetStatus(store, now);
  assert.equal(s.exhausted, true);
  await assert.rejects(assertBudget(store, { now }), DailyTokenLimitExceededError);

  await assert.rejects(setDailyTokenLimit(store, 0, "x", now), RangeError);
  assert.equal((await store.getSettings()).dailyTokenLimit, 500, "an invalid value leaves the setting untouched");
});
