import Link from "next/link";
export default function NotFound() {
  return (
    <div className="py-20 text-center">
      <h1 className="text-2xl font-semibold">Page introuvable</h1>
      <p className="text-ink-2 mt-2">L'élément demandé n'existe pas dans les données de démonstration.</p>
      <Link href="/" className="inline-block mt-4 text-brand-700 hover:underline">← Retour au tableau de bord</Link>
    </div>
  );
}
