import Link from "next/link";
import { Icon } from "@/components/icons";

export function BackLink({ href, children }: { href: string; children: string }) {
  return (
    <Link href={href} className="-ml-1 inline-flex w-fit items-center gap-1 rounded-full py-1 pr-3 text-sm font-medium text-ink-3 hover:text-ink">
      <Icon name="chevron-left" className="h-4 w-4" /> {children}
    </Link>
  );
}
