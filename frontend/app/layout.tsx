import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Sidebar } from "@/components/layout/Sidebar";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "TokenFlow AI — Enterprise AI FinOps",
  description: "Enterprise AI Cost, Usage & Governance Intelligence Platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased dark`}>
      <body className="min-h-full bg-zinc-950 text-zinc-100 flex">
        <Sidebar />
        <main className="ml-60 flex-1 min-h-screen overflow-auto">{children}</main>
      </body>
    </html>
  );
}
