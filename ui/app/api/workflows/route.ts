import { screenpipe } from "@/lib/server";

export const dynamic = "force-dynamic";

/** Catalogue de workflows appris nativement par screenpipe (onglet Workflows de l'app). */
export async function GET() {
  try {
    const r = await screenpipe("/workflows?limit=20");
    if (!r.ok) return Response.json({ workflows: [], error: r.status });
    const d = await r.json();
    return Response.json({ workflows: d.data ?? [], analyzedAt: d.analyzedAt ?? null });
  } catch (e) {
    return Response.json({ workflows: [], error: String(e) });
  }
}
