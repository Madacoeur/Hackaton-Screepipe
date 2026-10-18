import type { Metadata } from "next";
import { DM_Mono, Figtree } from "next/font/google";
import "./globals.css";

const figtree = Figtree({ variable: "--font-figtree", subsets: ["latin"], weight: ["400", "500", "600", "700"] });
const dmMono = DM_Mono({ variable: "--font-dm-mono", subsets: ["latin"], weight: ["400", "500"] });

export const metadata: Metadata = {
  title: "Déjà-vu Mail",
  description: "Agent mail qui rejoue les workflows appris par screenpipe, avec preuves et confiance",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr">
      <body className={`${figtree.variable} ${dmMono.variable} antialiased`}>{children}</body>
    </html>
  );
}
