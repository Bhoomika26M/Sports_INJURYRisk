import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";

export const metadata: Metadata = {
  title: {
    default: "InjuryDetect — Sports Biomechanics & Injury Risk Intelligence",
    template: "%s | InjuryDetect",
  },
  description: "AI-powered monocular video biomechanics screening platform for coaches, physiotherapists, and sports scientists. Joint kinematics, symmetry index, and heuristic injury risk flags.",
  keywords: ["biomechanics", "sports injury prevention", "movement screening", "pose estimation", "kinematics", "ACWR", "physiotherapy"],
  authors: [{ name: "InjuryDetect Team" }],
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
    apple: [
      { url: "/logo-icon.svg", type: "image/svg+xml" },
    ],
  },
  openGraph: {
    title: "InjuryDetect — Sports Biomechanics & Injury Risk Intelligence",
    description: "AI-powered monocular video biomechanics screening platform for coaches, physiotherapists, and sports scientists.",
    type: "website",
    locale: "en_US",
    siteName: "InjuryDetect",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-100 text-slate-900 antialiased">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
