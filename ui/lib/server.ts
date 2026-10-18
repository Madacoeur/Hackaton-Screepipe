import { execFile } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

export const ROOT = path.resolve(process.cwd(), "..");
const AGENT = path.join(ROOT, "agent");
const LOG = path.join(AGENT, "agent_log.jsonl");
const STATUS = path.join(AGENT, "status.json");
const CONFIG = path.join(AGENT, "config.json");
export const FILES_DIR = path.join(process.env.USERPROFILE ?? "", "Documents", "Freelance-Demo");
const SCREENPIPE = process.env.SCREENPIPE_LOCAL_API_URL ?? "http://localhost:3030";
const BUN = path.join(process.env.LOCALAPPDATA ?? "", "screenpipe", "bun.exe");

import type { Entry } from "./types";
export type { Entry } from "./types";

export function readEntries(): Entry[] {
  if (!existsSync(LOG)) return [];
  const status = existsSync(STATUS) ? JSON.parse(readFileSync(STATUS, "utf-8")) : {};
  return readFileSync(LOG, "utf-8")
    .split("\n")
    .map((l, i) => [l, i] as const)
    .filter(([l]) => l.trim())
    .map(([l, i]) => {
      const e = JSON.parse(l);
      // les premières lignes du journal datent d'avant les identifiants : id dérivé de leur position
      const id = e.id ?? `L${i}`;
      const s = status[id];
      return { ...e, id, ...(s ? { status: s.status, final_text: s.final_text, decided_at: s.time, error: s.error ?? e.error } : {}) };
    })
    .reverse();
}

export function readMode(): string {
  try {
    return JSON.parse(readFileSync(CONFIG, "utf-8")).mode ?? "verification";
  } catch {
    return "verification";
  }
}

export function writeMode(mode: string) {
  writeFileSync(CONFIG, JSON.stringify({ mode }, null, 2));
}

let token: string | null = null;

/** Token de l'API locale screenpipe, demandé une fois à sa CLI puis gardé en mémoire (jamais écrit). */
async function screenpipeToken(): Promise<string> {
  if (process.env.SCREENPIPE_LOCAL_API_KEY) return process.env.SCREENPIPE_LOCAL_API_KEY;
  if (token) return token;
  const out = await run(BUN, ["x", "screenpipe@latest", "auth", "token"], mkdtempSync(path.join(tmpdir(), "sp-")));
  const t = out.stdout.trim().split(/\r?\n/).pop() ?? "";
  if (t) token = t; // un échec à froid ne doit pas figer un token vide
  return t;
}

export async function screenpipe(pathAndQuery: string, init: RequestInit = {}): Promise<Response> {
  const r = await call(pathAndQuery, init);
  if (r.status === 401 || r.status === 403) {
    token = null; // token périmé ou vide : on en redemande un et on réessaie une fois
    return call(pathAndQuery, init);
  }
  return r;
}

async function call(pathAndQuery: string, init: RequestInit) {
  return fetch(`${SCREENPIPE}${pathAndQuery}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${await screenpipeToken()}`,
      "X-Screenpipe-Client": "api",
      "X-Screenpipe-Agent": "claude",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
    cache: "no-store",
  });
}

export function run(cmd: string, args: string[], cwd = ROOT, timeout = 180_000) {
  return new Promise<{ code: number; stdout: string; stderr: string }>((resolve) => {
    execFile(cmd, args, { cwd, timeout, env: { ...process.env, PYTHONIOENCODING: "utf-8" }, windowsHide: true },
      (err, stdout, stderr) => resolve({ code: err ? (typeof err.code === "number" ? err.code : 1) : 0, stdout, stderr }));
  });
}
