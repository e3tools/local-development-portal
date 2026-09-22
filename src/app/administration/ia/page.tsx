import { PageHeader } from "@/components/ui";
import { AiBudgetAdmin } from "@/components/ai-budget-admin";

export const metadata = { title: "Assistant IA · Budget quotidien" };

export default function AdministrationIa() {
  return (
    <>
      <PageHeader title="Assistant IA · Budget quotidien" crumbs={[{ label: "Administration" }, { label: "Assistant IA" }]}
        subtitle="Plafond journalier de jetons consommés par l'assistant conversationnel (voir le brief « AI chat for development partners »). Fixé par l'administrateur UCP pour maîtriser la dépense ; remis à zéro chaque jour." />
      <AiBudgetAdmin />
    </>
  );
}
