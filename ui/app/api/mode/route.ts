import { readMode, writeMode } from "@/lib/server";

export async function GET() {
  return Response.json({ mode: readMode() });
}

export async function POST(req: Request) {
  const { mode } = await req.json();
  if (mode !== "auto" && mode !== "verification") return new Response("invalid mode", { status: 400 });
  writeMode(mode);
  return Response.json({ mode });
}
