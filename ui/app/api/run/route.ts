import path from "node:path";
import { ROOT, run } from "@/lib/server";

/** « Traiter maintenant » : agent/process_now.py prépare screenpipe et Brave, traite les mails non lus,
 *  puis on renvoie son résumé (une ligne lisible) une fois le passage terminé. */
export async function POST() {
  const r = await run("python", [path.join(ROOT, "agent", "process_now.py"), "--max", "3"], ROOT, 900_000);
  const last = r.stdout.split(/\r?\n/).filter((l) => l.startsWith("[process]")).pop();
  const message = last?.replace("[process] ", "") ?? (r.stderr.trim().split(/\r?\n/).pop() || "the run returned nothing");
  return Response.json({ ok: r.code === 0, message });
}
