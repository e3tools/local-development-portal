"use client";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Badge, Card, Kpi, Progress, type Tone } from "@/components/ui";
import { fmtDate, fmtInt } from "@/lib/format";
import {
  WARNING_RATIO,
  budgetDay,
  getBudgetStatus,
  groupDigits,
  recordUsage,
  setDailyTokenLimit,
  type BudgetSettings,
  type BudgetStatus,
} from "@/lib/ai-budget";
import { LocalStorageBudgetStore } from "@/lib/ai-budget-browser";

/** Signed-in administrator of the mockup (see the header in src/components/shell.tsx). */
const ADMIN = "Essohanam Tchagnao";
const PRESETS = [500_000, 1_000_000, 2_000_000, 5_000_000];
/** A typical partner question: ~7 tool calls on a Sonnet-class model. Demo only. */
const DEMO_QUESTION = { inputTokens: 38_000, outputTokens: 4_500, cacheReadTokens: 6_000 };

function fmtStamp(iso: string): string {
  return `${fmtDate(iso.slice(0, 10))} à ${iso.slice(11, 16)} UTC`;
}

export function AiBudgetAdmin() {
  const store = useMemo(() => new LocalStorageBudgetStore(), []);
  const [settings, setSettings] = useState<BudgetSettings | null>(null);
  const [status, setStatus] = useState<BudgetStatus | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const load = useCallback(() => Promise.all([store.getSettings(), getBudgetStatus(store)]), [store]);

  const refresh = useCallback(async () => {
    const [s, st] = await load();
    setSettings(s);
    setStatus(st);
    return s;
  }, [load]);

  useEffect(() => {
    let active = true;
    const tick = () =>
      load().then(([s, st]) => {
        if (!active) return;
        setSettings(s);
        setStatus(st);
        setDraft((d) => (d === "" ? groupDigits(s.dailyTokenLimit) : d));
      });
    tick();
    const id = window.setInterval(tick, 60_000); // picks up the midnight rollover
    return () => {
      active = false;
      window.clearInterval(id);
    };
  }, [load]);

  async function onSave(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSavedAt(null);
    try {
      const s = await setDailyTokenLimit(store, draft, ADMIN);
      setDraft(groupDigits(s.dailyTokenLimit));
      await refresh();
      setSavedAt(s.updatedAt);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function simulateQuestion() {
    await recordUsage(store, DEMO_QUESTION);
    await refresh();
  }
  async function resetToday() {
    await store.resetUsage(budgetDay());
    await refresh();
  }

  if (!settings || !status) {
    return <p className="text-sm text-ink-3">Chargement du budget…</p>;
  }

  const tone: Tone = status.exhausted ? "critical" : status.ratio >= WARNING_RATIO ? "warning" : "good";
  const barColor = { good: "#1f7a4d", warning: "#d97706", critical: "#dc2626" }[tone];
  const state = status.exhausted
    ? { label: "Plafond atteint · assistant suspendu jusqu'à la réinitialisation", tone: "critical" as Tone }
    : status.ratio >= WARNING_RATIO
      ? { label: `Alerte · plus de ${Math.round(WARNING_RATIO * 100)} % du budget consommé`, tone: "warning" as Tone }
      : { label: "Disponible", tone: "good" as Tone };
  const dirty = draft.replace(/\s/g, "") !== String(settings.dailyTokenLimit);

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Kpi label="Plafond quotidien" value={fmtInt(status.limit)} sub="jetons par jour, tous types confondus" />
        <Kpi label="Consommé aujourd'hui" value={fmtInt(status.used)} sub={`${status.calls} appel(s) au modèle · ${Math.round(status.ratio * 100)} % du plafond`} tone={tone} />
        <Kpi label="Restant" value={fmtInt(status.remaining)} sub={status.exhausted ? "Aucun appel possible" : "jetons avant suspension"} tone={tone} />
        <Kpi label="Prochaine réinitialisation" value={fmtDate(status.resetsAt.slice(0, 10))} sub="00:00 UTC (heure de Lomé), chaque jour" tone="info" />
      </div>

      <Card title="Consommation du jour" subtitle={`Journée budgétaire ${fmtDate(status.day)} · le compteur revient à zéro à 00:00 UTC`} className="mb-4"
        action={<Badge tone={state.tone}>{state.label}</Badge>}>
        <Progress value={status.ratio * 100} color={barColor} label={`${Math.round(status.ratio * 100)} %`} />
        <p className="text-xs text-ink-2 mt-3">
          {fmtInt(status.used)} / {fmtInt(status.limit)} jetons. Lorsque le plafond est atteint, l'assistant répond «&nbsp;Budget quotidien atteint, réessayez après 00:00&nbsp;» et n'effectue aucun appel au modèle.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-dashed border-line pt-3">
          <span className="text-[11px] uppercase tracking-wide text-ink-3">Démonstration</span>
          <button type="button" onClick={simulateQuestion} className="rounded-md border border-line bg-white px-3 py-1.5 text-sm font-medium hover:bg-surface">
            Simuler une question (~{fmtInt(DEMO_QUESTION.inputTokens + DEMO_QUESTION.outputTokens + DEMO_QUESTION.cacheReadTokens)} jetons)
          </button>
          <button type="button" onClick={resetToday} className="rounded-md border border-line bg-white px-3 py-1.5 text-sm font-medium hover:bg-surface">
            Remettre le compteur à zéro
          </button>
          <span className="text-xs text-ink-3">Maquette : la consommation et le réglage sont conservés dans ce navigateur uniquement.</span>
        </div>
      </Card>

      <Card title="Plafond de jetons par jour" subtitle="Réservé au rôle Administrateur UCP. La modification s'applique immédiatement, y compris à la journée en cours." className="mb-4">
        <form onSubmit={onSave} className="max-w-xl">
          <label htmlFor="daily-limit" className="block text-xs font-medium text-ink-2 mb-1">Nombre maximal de jetons par jour</label>
          <div className="flex flex-wrap gap-2">
            <input id="daily-limit" inputMode="numeric" value={draft} onChange={(e) => setDraft(e.target.value)}
              aria-invalid={error ? true : undefined} aria-describedby={error ? "daily-limit-error" : undefined}
              className="w-56 rounded-md border border-line bg-white px-3 py-1.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-brand-600" />
            <button type="submit" disabled={!dirty}
              className="rounded-md border border-brand-700 bg-brand-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-50">
              Enregistrer
            </button>
          </div>
          {error && <p id="daily-limit-error" role="alert" className="mt-2 text-xs text-red-700">{error}</p>}
          {savedAt && !error && <p className="mt-2 text-xs text-green-700">Plafond enregistré le {fmtStamp(savedAt)}.</p>}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="text-xs text-ink-3">Valeurs usuelles :</span>
            {PRESETS.map((p) => (
              <button key={p} type="button" onClick={() => setDraft(groupDigits(p))}
                className={`rounded-full border px-2.5 py-0.5 text-xs tabular-nums ${p === settings.dailyTokenLimit ? "border-brand-700 bg-brand-50 text-brand-800" : "border-line bg-white text-ink-2 hover:bg-surface"}`}>
                {fmtInt(p)}
              </button>
            ))}
          </div>
          <p className="mt-3 text-xs text-ink-3">
            {settings.updatedAt && settings.updatedBy
              ? `Dernière modification par ${settings.updatedBy} le ${fmtStamp(settings.updatedAt)}.`
              : "Valeur par défaut, jamais modifiée."}
          </p>
        </form>
      </Card>

      <Card title="Règles appliquées" subtitle="Ce que l'agent fait de ce plafond">
        <ul className="list-disc space-y-1 pl-5 text-sm text-ink-2">
          <li>Un seul plafond pour toute la plateforme, exprimé en jetons du modèle (entrée + sortie + cache), donc directement lié à la facture.</li>
          <li>Avant chaque appel au modèle, l'agent vérifie le compteur du jour ; au-delà du plafond, il refuse la question sans appeler le modèle.</li>
          <li>Le compteur est remis à zéro chaque jour à 00:00 UTC, soit minuit à Lomé. Aucune action manuelle n'est nécessaire.</li>
          <li>La taille d'un appel n'est connue qu'après coup : le dernier appel de la journée peut dépasser le plafond de sa propre taille, jamais plus.</li>
          <li>Abaisser le plafond sous la consommation du jour suspend l'assistant immédiatement ; le relever le réactive.</li>
          <li>Chaque modification est tracée (auteur, horodatage). Un plafond par utilisateur est prévu en v2.</li>
        </ul>
      </Card>
    </>
  );
}
