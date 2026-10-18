import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { ROOT, run } from "@/lib/server";

/** Validation humaine : envoie le brouillon (texte éventuellement modifié) ou le rejette. */
export async function POST(req: Request) {
  const { id, text, reject } = await req.json();
  if (typeof id !== "string" || !/^[\w-]+$/.test(id)) return new Response("id invalide", { status: 400 });
  const args = [path.join(ROOT, "agent", "approve_draft.py"), id];
  if (reject) args.push("--reject");
  else if (typeof text === "string") {
    const f = path.join(mkdtempSync(path.join(tmpdir(), "draft-")), "reply.txt");
    writeFileSync(f, text, "utf-8");
    args.push("--text-file", f);
  }
  const r = await run("python", args);
  const message = (r.stdout + r.stderr).trim().split(/\r?\n/).pop() ?? "";
  return Response.json({ ok: r.code === 0, message }, { status: r.code === 0 ? 200 : 500 });
}
