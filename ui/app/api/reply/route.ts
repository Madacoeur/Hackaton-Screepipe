import path from "node:path";
import { ROOT, readEntries, run, setStatus } from "@/lib/server";

/** « Chercher dans ma mémoire et répondre » : relance l'agent sur ce mail précis. Il cherche le contexte
 *  dans screenpipe et prépare un brouillon s'il trouve de quoi répondre (jamais d'envoi). */
export async function POST(req: Request) {
  const { id } = await req.json();
  const entry = readEntries().find((e) => e.id === id);
  if (!entry?.subject) return Response.json({ ok: false, message: "mail introuvable" }, { status: 404 });
  const before = readEntries().length;
  const r = await run("python", [path.join(ROOT, "agent", "run_agent.py"), "--subject", entry.subject], ROOT, 240_000);
  const created = readEntries().slice(0, readEntries().length - before).find((e) => e.status === "brouillon");
  if (created) {
    setStatus(id, "remplacé"); // l'ancienne entrée « à vérifier » laisse la place au brouillon
    return Response.json({ ok: true, id: created.id });
  }
  const line = (r.stdout + r.stderr).split(/\r?\n/).filter((l) => l.includes("[agent]")).pop() ?? "";
  return Response.json({ ok: false, message: line.includes("VÉRIFIER") ? "rien trouvé dans ta mémoire pour répondre" : line || "échec" });
}
