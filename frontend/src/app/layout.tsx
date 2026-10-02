import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/lib/providers";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "InjuryDetect · Movement screening made simple",
  description: "Movement screening, joint kinematics, and heuristic risk flags for athletes and coaches.",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#ffffff" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} antialiased`}>
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
