import { screenpipe } from "@/lib/server";

/** « Traiter maintenant » : lance la pipe screenpipe mail-autopilot sans attendre son créneau de 15 min. */
export async function POST() {
  const r = await screenpipe("/pipes/mail-autopilot/run", { method: "POST", body: "{}" });
  return Response.json({ ok: r.ok, detail: await r.text() }, { status: r.ok ? 200 : 502 });
}
