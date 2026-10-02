import Link from "next/link";
import { Icon } from "@/components/icons";

export function Logo({ href = "/dashboard", compact = false }: { href?: string; compact?: boolean }) {
  return (
    <Link href={href} className="inline-flex items-center gap-3 rounded-full" aria-label="InjuryDetect home">
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand text-brand-dark">
        <Icon name="activity" className="h-5 w-5" />
      </span>
      {!compact && <span className="text-[17px] font-bold tracking-tight text-ink">InjuryDetect</span>}
    </Link>
  );
}
