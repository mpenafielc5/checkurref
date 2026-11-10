import { RolePage } from "@/features/auth/components/role-page";
import { BenchmarkPanel } from "@/features/lab/components/benchmark-panel";
import { EngineComparison } from "@/features/lab/components/engine-comparison";
import { LabTabs } from "@/features/lab/components/lab-tabs";
import { PageSection } from "@/shared/components/page-section";

/** Laboratorio de extracción: Comparar y Benchmark (maquetas 17 y 18, HU-12 y HU-13). */
export default function LabPage() {
  return (
    <RolePage allow={["admin"]}>
      <PageSection
        eyebrow="Administración"
        title="Laboratorio de extracción"
        description="Compara AnyStyle y spaCy sobre una referencia o contra el estándar de oro."
      >
        <LabTabs
          tabs={[
            { id: "comparar", label: "Comparar", content: <EngineComparison /> },
            { id: "benchmark", label: "Benchmark", content: <BenchmarkPanel /> },
          ]}
        />
      </PageSection>
    </RolePage>
  );
}
