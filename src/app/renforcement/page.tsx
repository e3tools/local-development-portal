import { Card, Kpi, PageHeader, Badge, Btn, Progress } from "@/components/ui";
import { HBarChart } from "@/components/charts";
import { RESOURCES } from "@/data/capacity";
import { fmtInt, fmtPct, fmtDate } from "@/lib/format";
import { countBy, sumBy } from "@/lib/stats";

export const metadata = { title: "Renforcement des capacités" };

export default function Renforcement() {
  const completions = sumBy(RESOURCES, (r) => r.completions);
  const target = sumBy(RESOURCES, (r) => r.target);
  const langs = countBy(RESOURCES.flatMap((r) => r.languages), (l) => l);
  const typeTone: Record<string, "info" | "good" | "violet" | "warning" | "neutral"> = { "Module de formation": "info", "Guide pratique": "good", "Vidéo": "violet", "Fiche outil": "warning", "Quiz": "neutral" };
  return (
    <>
      <PageHeader title="Renforcement des capacités" subtitle="Bibliothèque de modules, guides et vidéos pour les CVD, CCD, animateurs et agents de terrain. Consultable hors ligne depuis l'application mobile ; disponible en français et en langues locales."
        action={<div className="flex gap-2"><Btn>Suivi des formations</Btn><Btn primary>+ Publier une ressource</Btn></div>} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Kpi label="Ressources publiées" value={RESOURCES.length} sub={`${RESOURCES.filter((r) => r.offline).length} disponibles hors ligne`} />
        <Kpi label="Parcours complétés" value={fmtInt(completions)} sub={`Objectif ${fmtInt(target)}`} tone="good" />
        <Kpi label="Taux de complétion" value={fmtPct((completions / target) * 100)} sub="Tous publics confondus" tone="info" />
        <Kpi label="Langues" value={Object.keys(langs).length} sub={Object.keys(langs).filter((l) => l !== "Français").join(", ")} tone="violet" />
      </div>
      <div className="grid lg:grid-cols-3 gap-4">
        <Card title="Catalogue" className="lg:col-span-2">
          <ul className="divide-y divide-line">
            {RESOURCES.map((r) => (
              <li key={r.id} className="py-3 grid md:grid-cols-[1fr_200px] gap-3 items-center">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={typeTone[r.type]} icon={false}>{r.type}</Badge>
                    <span className="font-medium text-sm">{r.title}</span>
                    {r.offline && <span className="text-[10px] uppercase tracking-wide text-ink-3 border border-line rounded px-1">hors ligne</span>}
                  </div>
                  <div className="text-xs text-ink-2 mt-1">{r.audience} · {r.durationMin} min · {r.languages.join(", ")} · mis à jour le {fmtDate(r.updatedAt)}</div>
                </div>
                <div>
                  <Progress value={(r.completions / r.target) * 100} color="#1baf7a" />
                  <div className="text-[11px] text-ink-3 text-right">{r.completions} / {r.target} complétés</div>
                </div>
              </li>
            ))}
          </ul>
        </Card>
        <div className="space-y-4">
          <Card title="Complétion par public">
            <HBarChart data={Object.entries(RESOURCES.reduce<Record<string, [number, number]>>((acc, r) => { const k = r.audience.split(",")[0].trim(); acc[k] = [(acc[k]?.[0] ?? 0) + r.completions, (acc[k]?.[1] ?? 0) + r.target]; return acc; }, {})).map(([label, [c, t]]) => ({ label, value: Math.round((c / t) * 100), display: fmtPct((c / t) * 100) })).sort((a, b) => b.value - a.value)} max={100} color="#1baf7a" />
          </Card>
          <Card title="Ressources par langue">
            <HBarChart data={Object.entries(langs).map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value)} color="#4a3aa7" />
          </Card>
        </div>
      </div>
    </>
  );
}
