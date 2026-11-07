"use client";

import { PageHeader } from "@/components/page-header";
import { VideoComparator } from "@/components/video-comparator";
import { BackLink } from "@/components/back-link";

export default function BenchmarkStudioPage() {
  return (
    <>
      <PageHeader
        back={<BackLink href="/dashboard">Dashboard</BackLink>}
        title="Form Comparison Studio"
        subtitle="Side-by-side video kinematics, synchronized inflection scrub, and vector posture twins."
      />
      <VideoComparator />
    </>
  );
}
