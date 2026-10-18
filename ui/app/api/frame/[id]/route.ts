import { screenpipe } from "@/lib/server";

/** Capture d'écran screenpipe (l'API locale exige un token, le navigateur passe par ici). */
export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) return new Response("id invalide", { status: 400 });
  const r = await screenpipe(`/frames/${id}`);
  if (!r.ok) return new Response("capture indisponible", { status: r.status });
  return new Response(r.body, {
    headers: { "Content-Type": r.headers.get("Content-Type") ?? "image/png", "Cache-Control": "max-age=86400" },
  });
}
