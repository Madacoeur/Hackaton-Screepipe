import { randomUUID } from "node:crypto";
import { screenpipe } from "@/lib/server";

/** « Montre-moi une fois » : étoile les 10 prochaines minutes dans screenpipe, pour que les
 *  pipes d'apprentissage traitent ce que l'utilisateur va faire comme une démonstration. */
export async function POST() {
  const start = new Date();
  const end = new Date(start.getTime() + 10 * 60_000);
  const r = await screenpipe("/starred-sessions", {
    method: "POST",
    body: JSON.stringify({ id: randomUUID(), start: start.toISOString(), end: end.toISOString(), hd_requested: false, revision: 0 }),
  });
  return Response.json({ ok: r.ok, until: end.toISOString() }, { status: r.ok ? 200 : 502 });
}
