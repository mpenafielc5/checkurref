import type { Metadata } from "next";
import { AccessCard } from "@/features/auth/components/access-card";
import { Wordmark } from "@/shared/components/ui/wordmark";

export const metadata: Metadata = {
  title: "Ingresar · CheckUrRef",
};

export default function LoginPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 bg-surface px-4 py-12">
      <Wordmark />
      <AccessCard headingLevel="h1" />
    </main>
  );
}
