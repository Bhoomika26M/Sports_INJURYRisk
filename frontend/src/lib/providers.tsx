"use client";

import { useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApiError } from "@/lib/api-client";
import { AuthProvider } from "@/lib/auth-context";
import { ToastProvider } from "@/components/toast";

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            // Don't hammer the API for errors that retrying can't fix (auth, not found, validation).
            retry: (count, err) =>
              !(err instanceof ApiError && err.status >= 400 && err.status < 500) && count < 2,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      <ToastProvider>
        <AuthProvider>{children}</AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
  );
}
