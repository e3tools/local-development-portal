import Link from "next/link";
import { Card, PageHeader, Badge } from "@/components/ui";
import { REGIONS, PREFECTURES, CANTONS, VILLAGES } from "@/data/geo";
import { PRIORITIES } from "@/data/priorities";
import { INVESTMENTS } from "@/data/investments";
import { fmtInt } from "@/lib/format";
import { sumBy } from "@/lib/stats";

export const metadata = { title: "Profils territoriaux" };

export default function Territoires() {
  return (
    <>
      <PageHeader title="Profils territoriaux" subtitle="Navigation Région → Préfecture → Canton → Village. Chaque village dispose d'un profil (démographie, infrastructures, CVD, vulnérabilité) et chaque canton d'un profil consolidé." />
      <div className="grid lg:grid-cols-3 gap-4">
        {REGIONS.map((r) => {
          const prefs = PREFECTURES.filter((p) => p.regionId === r.id);
          const vs = VILLAGES.filter((v) => v.regionId === r.id);
          return (
            <Card key={r.id} title={<Link href={`/territoires/regions/${r.id}`} className="hover:underline text-brand-700">Région {r.name}</Link>} subtitle={`Chef-lieu : ${r.chefLieu} · ${prefs.length} préfectures · ${CANTONS.filter((c) => c.regionId === r.id).length} cantons · ${vs.length} villages · ${fmtInt(sumBy(vs, (v) => v.population))} hab.`}>
              <ul className="space-y-2">
                {prefs.map((p) => {
                  const cantons = CANTONS.filter((c) => c.prefectureId === p.id);
                  return (
                    <li key={p.id}>
                      <div className="text-sm font-medium">{p.name} <span className="text-xs text-ink-3 font-normal">· {p.chefLieu}</span></div>
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {cantons.map((c) => {
                          const cv = VILLAGES.filter((v) => v.cantonId === c.id);
                          const ids = new Set(cv.map((v) => v.id));
                          const n = INVESTMENTS.filter((i) => ids.has(i.villageId)).length;
                          return (
                            <Link key={c.id} href={`/territoires/cantons/${c.id}`} className="inline-flex items-center gap-1 rounded-md border border-line bg-surface px-2 py-0.5 text-xs hover:border-brand-600 hover:text-brand-700">
                              {c.name} <span className="text-ink-3">({cv.length})</span>
                              {n > 0 && <span className="rounded-full bg-brand-100 text-brand-800 px-1.5 text-[10px]">{n} SP</span>}
                            </Link>
                          );
                        })}
                      </div>
                    </li>
                  );
                })}
              </ul>
              <div className="mt-3 flex gap-2 text-xs">
                <Badge tone="violet" icon={false}>{PRIORITIES.filter((p) => new Set(vs.map((v) => v.id)).has(p.villageId)).length} priorités</Badge>
                <Badge tone="info" icon={false}>{INVESTMENTS.filter((i) => new Set(vs.map((v) => v.id)).has(i.villageId)).length} sous-projets</Badge>
              </div>
            </Card>
          );
        })}
      </div>
    </>
  );
}
