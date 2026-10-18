import type { Metadata } from "next";
import { DM_Mono, Figtree } from "next/font/google";
import "./globals.css";

const figtree = Figtree({ variable: "--font-figtree", subsets: ["latin"], weight: ["400", "500", "600", "700"] });
const dmMono = DM_Mono({ variable: "--font-dm-mono", subsets: ["latin"], weight: ["400", "500"] });

export const metadata: Metadata = {
  title: "Déjà-vu Mail",
  description: "Mail agent that replays the workflows screenpipe learned from you, with proof and confidence",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${figtree.variable} ${dmMono.variable} antialiased`}>{children}</body>
    </html>
  );
}
