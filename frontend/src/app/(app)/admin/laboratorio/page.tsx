import { RolePage } from "@/features/auth/components/role-page";
import { BenchmarkPanel } from "@/features/lab/components/benchmark-panel";
import { EngineComparison } from "@/features/lab/components/engine-comparison";
import { LabTabs } from "@/features/lab/components/lab-tabs";
import {
  SAMPLE_AGREEMENT,
  SAMPLE_BENCHMARK,
  SAMPLE_ENGINES,
  SAMPLE_REFERENCE,
} from "@/features/lab/sample-data";
import { PageSection } from "@/shared/components/page-section";
import { SampleDataNotice } from "@/shared/components/ui/sample-data-notice";

/** Laboratorio de extracción: Comparar y Benchmark (maquetas 17 y 18). */
export default function LabPage() {
  return (
    <RolePage allow={["admin"]}>
      <PageSection
        eyebrow="Administración"
        title="Laboratorio de extracción"
        description="Compara AnyStyle y spaCy sobre una referencia o contra el conjunto de oro."
      >
        <SampleDataNotice story="la HU-12 y la HU-13" />
        <LabTabs
          tabs={[
            {
              id: "comparar",
              label: "Comparar",
              content: (
                <EngineComparison
                  reference={SAMPLE_REFERENCE}
                  engines={SAMPLE_ENGINES}
                  agreement={SAMPLE_AGREEMENT}
                />
              ),
            },
            {
              id: "benchmark",
              label: "Benchmark",
              content: <BenchmarkPanel benchmark={SAMPLE_BENCHMARK} />,
            },
          ]}
        />
      </PageSection>
    </RolePage>
  );
}
