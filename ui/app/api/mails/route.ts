import { readEntries, readMode } from "@/lib/server";

export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json({ entries: readEntries(), mode: readMode() });
}
