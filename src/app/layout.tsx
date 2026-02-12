import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Unified Ads Portfolio Dashboard",
  description: "Aggregate performance metrics across ad platforms",
  icons: {
    icon: [
      { url: "/cube_logo.png?v=1" },
      { url: "/cube_logo.png?v=1", media: "(prefers-color-scheme: light)" },
      { url: "/cube_logo.png?v=1", media: "(prefers-color-scheme: dark)" },
    ],
    shortcut: "/cube_logo.png?v=1",
    apple: "/cube_logo.png?v=1",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/cube_logo.png?v=1" />
      </head>
      <body className={`${inter.className} flex h-screen overflow-hidden bg-slate-50`}>
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </body>
    </html>
  );
}
