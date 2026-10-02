"use client";

import { ErrorState } from "@/components/feedback";

export default function RouteError({ reset }: { error: Error; reset: () => void }) {
  return (
    <ErrorState
      title="This page hit a snag"
      message="Something unexpected happened while showing this page. Your data is safe — try again."
      onRetry={reset}
    />
  );
}
