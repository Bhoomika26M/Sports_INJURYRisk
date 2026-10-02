"use client";

import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { canManageAthletes } from "@/lib/format";
import type { Athlete } from "@/lib/types";
import { AthleteForm } from "@/components/athlete-forms";
import { BackLink } from "@/components/back-link";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/feedback";
import { useToast } from "@/components/toast";

export default function NewAthletePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { user } = useAuth();

  if (!canManageAthletes(user?.role)) {
    return (
      <>
        <BackLink href="/athletes">Athletes</BackLink>
        <EmptyState icon="users" title="Only coaches can add athletes">Ask a coach to create the profile for you.</EmptyState>
      </>
    );
  }

  return (
    <>
      <PageHeader back={<BackLink href="/athletes">Athletes</BackLink>} title="Add an athlete" subtitle="Just the basics — you can edit these any time." />
      <div className="card p-6 sm:p-9">
        <AthleteForm
          submitLabel="Create athlete"
          onCancel={() => router.push("/athletes")}
          onSubmit={async (body) => {
            const created = await api.post<Athlete>("/athletes", body);
            await queryClient.invalidateQueries({ queryKey: ["athletes"] });
            toast.success("Athlete added.");
            router.replace(`/athletes/${created.id}`);
          }}
        />
      </div>
    </>
  );
}
