import Link from "next/link";
import { Logo } from "@/components/logo";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-5 bg-wash px-6 text-center">
      <Logo href="/" />
      <h1 className="mt-4 text-3xl font-bold tracking-tight text-ink">We can&apos;t find that page</h1>
      <p className="max-w-md text-ink-2">The link may be old or mistyped. Let&apos;s get you back on track.</p>
      <Link href="/dashboard" className="btn btn-primary">Go to home</Link>
    </div>
  );
}
