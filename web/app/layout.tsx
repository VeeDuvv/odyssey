import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/sidebar";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Odyssey",
  description: "AI-native enterprise AI & Data architecture navigator",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-[var(--color-bg)] antialiased">
        <Providers>
          <Sidebar />
          <main className="ml-[72px] min-h-screen">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
