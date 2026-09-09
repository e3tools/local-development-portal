"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV = [
  { href: "/", label: "Tableau de bord", icon: "▦" },
  { href: "/territoires", label: "Profils territoriaux", icon: "◎", hint: "Régions · cantons · villages" },
  { href: "/priorites", label: "Registre des priorités", icon: "☰" },
  { href: "/investissements", label: "Paquets d'investissement", icon: "◆", hint: "Circuit d'approbation" },
  { href: "/grm", label: "Gestion des plaintes", icon: "⚑", hint: "MGP / GRM" },
  { href: "/partenaires", label: "Vue partenaires", icon: "◫", hint: "Positions d'investissement" },
  { href: "/renforcement", label: "Renforcement des capacités", icon: "✎" },
  { href: "/utilisateurs", label: "Utilisateurs & rôles", icon: "⚙" },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
  return (
    <div className="flex min-h-screen">
      <aside className={`fixed inset-y-0 left-0 z-30 w-72 bg-brand-900 text-white flex flex-col transition-transform lg:static lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="px-5 py-5 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-white/10 grid place-items-center font-bold tracking-tight">TG</div>
            <div>
              <div className="font-semibold leading-tight">COSO-MIS</div>
              <div className="text-xs text-white/70">Portail de développement local · Togo</div>
            </div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto py-3">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} onClick={() => setOpen(false)}
              className={`flex items-start gap-3 px-5 py-2.5 text-sm transition-colors ${isActive(n.href) ? "bg-white/15 text-white border-l-2 border-yellow-400" : "text-white/80 hover:bg-white/10 hover:text-white border-l-2 border-transparent"}`}>
              <span className="w-5 text-center opacity-80">{n.icon}</span>
              <span>
                <span className="block">{n.label}</span>
                {n.hint && <span className="block text-[11px] text-white/50">{n.hint}</span>}
              </span>
            </Link>
          ))}
        </nav>
        <div className="px-5 py-4 text-[11px] text-white/60 border-t border-white/10">
          Projet de cohésion sociale des régions nord du Golfe de Guinée (COSO) · Régions Savanes, Kara, Centrale
        </div>
      </aside>
      {open && <button aria-label="Fermer le menu" className="fixed inset-0 z-20 bg-black/40 lg:hidden" onClick={() => setOpen(false)} />}
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="sticky top-0 z-10 bg-white border-b border-line">
          <div className="flex items-center gap-3 px-4 lg:px-8 h-14">
            <button className="lg:hidden rounded-md border border-line px-2 py-1 text-sm" onClick={() => setOpen(true)} aria-label="Ouvrir le menu">☰</button>
            <div className="text-sm text-ink-2 hidden sm:block">Unité de coordination du projet · Lomé</div>
            <div className="ml-auto flex items-center gap-3">
              <span className="hidden md:inline-flex items-center gap-1.5 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-xs px-2.5 py-1">
                <span aria-hidden>⚠</span> Données de démonstration (fictives)
              </span>
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-full bg-brand-100 text-brand-800 grid place-items-center text-xs font-semibold">ET</div>
                <div className="hidden sm:block leading-tight">
                  <div className="text-sm font-medium">Essohanam Tchagnao</div>
                  <div className="text-[11px] text-ink-3">Administrateur UCP</div>
                </div>
              </div>
            </div>
          </div>
        </header>
        <main className="flex-1 px-4 lg:px-8 py-6 max-w-[1400px] w-full mx-auto">{children}</main>
        <footer className="px-4 lg:px-8 py-4 text-xs text-ink-3 border-t border-line">
          Maquette – toutes les données (villages, personnes, montants, plaintes) sont générées et fictives. Découpage administratif indicatif.
        </footer>
      </div>
    </div>
  );
}
