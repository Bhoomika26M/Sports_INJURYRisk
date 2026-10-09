import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Sports Injury Risk Detection",
  description: "AI-powered Sports Injury Risk Detection Platform",
};

import { GoogleOAuthProvider } from "@react-oauth/google";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Using the actual Google Client ID provided by the user
  const clientId = "596396009211-d7748bp8goqoqpeboc89rcno2od3vtd8.apps.googleusercontent.com";

  return (
    <html lang="en" className={`${inter.variable} antialiased`}>
      <body className="min-h-screen bg-slate-950 text-slate-50 flex flex-col font-sans">
        <GoogleOAuthProvider clientId={clientId}>
          {children}
        </GoogleOAuthProvider>
      </body>
    </html>
  );
}
