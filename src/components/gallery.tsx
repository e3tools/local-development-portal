import Image from "next/image";
import type { Photo } from "@/data/media";
import { fmtDate } from "@/lib/format";
import { Empty } from "./ui";

const MOMENT_TONE: Record<string, string> = {
  "Processus communautaire": "bg-brand-50 text-brand-800 border-brand-100",
  "Travaux en cours": "bg-amber-50 text-amber-800 border-amber-200",
  "Ouvrage achevé": "bg-green-50 text-green-800 border-green-200",
};

/**
 * Photo strip for a village profile or a sub-project record. Images are SVG so
 * next/image serves them unoptimized automatically — no optimizer round trip.
 */
export function Gallery({ photos, columns = 3 }: { photos: Photo[]; columns?: 2 | 3 | 4 }) {
  if (photos.length === 0) return <Empty>Aucune photo versée au dossier.</Empty>;
  const cols = { 2: "sm:grid-cols-2", 3: "sm:grid-cols-2 lg:grid-cols-3", 4: "sm:grid-cols-2 lg:grid-cols-4" }[columns];
  return (
    <ul className={`grid grid-cols-1 ${cols} gap-3`}>
      {photos.map((p) => (
        <li key={p.id} className="rounded-lg border border-line overflow-hidden bg-surface">
          <div className="relative aspect-[8/5] bg-line">
            <Image src={p.src} alt={p.alt} fill sizes="(min-width: 1024px) 320px, (min-width: 640px) 45vw, 100vw" className="object-cover" />
          </div>
          <div className="px-3 py-2 bg-white border-t border-line">
            <div className="flex items-start justify-between gap-2">
              <p className="text-xs font-medium text-ink leading-snug">{p.caption}</p>
              <span className={`shrink-0 rounded-full border px-1.5 py-0.5 text-[10px] font-medium whitespace-nowrap ${MOMENT_TONE[p.moment] ?? "bg-gray-100 text-gray-700 border-gray-200"}`}>
                {p.moment}
              </span>
            </div>
            <p className="text-[11px] text-ink-3 mt-1">
              {fmtDate(p.takenAt)} · {p.credit}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
