import Link from "next/link";
import { Icon, type IconName } from "@/components/icons";

/** Dashed launcher card — design.md §4.4 */
export function ActionCard({ href, icon, title, body }: { href: string; icon: IconName; title: string; body: string }) {
  return (
    <Link href={href} className="action-card">
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-wash text-ink"><Icon name={icon} /></span>
      <span className="min-w-0 flex-1">
        <span className="block font-semibold text-ink">{title}</span>
        <span className="block text-sm text-ink-2">{body}</span>
      </span>
      <Icon name="chevron-right" className="chev h-5 w-5 shrink-0 text-ink-3" />
    </Link>
  );
}
