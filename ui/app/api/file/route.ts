import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { FILES_DIR } from "@/lib/server";

/** Aperçu de la pièce jointe — limité au dossier Freelance-Demo. */
export async function GET(req: Request) {
  const name = new URL(req.url).searchParams.get("name") ?? "";
  const p = path.join(FILES_DIR, path.basename(name));
  if (!name.endsWith(".pdf") || !existsSync(p)) return new Response("fichier introuvable", { status: 404 });
  return new Response(readFileSync(p), { headers: { "Content-Type": "application/pdf" } });
}
