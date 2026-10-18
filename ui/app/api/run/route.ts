import { spawn } from "node:child_process";
import path from "node:path";
import { ROOT } from "@/lib/server";

/** « Traiter maintenant » : lance l'agent tout de suite, en arrière-plan et sans fenêtre de terminal. */
export async function POST() {
  const child = spawn("python", [path.join(ROOT, "agent", "run_agent.py"), "--max", "3"], {
    cwd: ROOT,
    env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    windowsHide: true,
    detached: true,
    stdio: "ignore",
  });
  child.unref();
  return Response.json({ ok: true });
}
