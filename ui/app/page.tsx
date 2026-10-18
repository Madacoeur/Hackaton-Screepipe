"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { Entry, Frame } from "@/lib/types";

const AUTO_THRESHOLD = 80;

type Workflow = { id: string; title: string };

function statusLabel(e: Entry) {
  if (e.status === "brouillon") return "brouillon prêt";
  return e.status;
}

function isReview(e: Entry) {
  return e.status === "à vérifier" || e.status === "erreur" || !!e.sensitive;
}

function pickFrame(e: Entry | null, app = "brave.exe"): Frame | undefined {
  const frames = e?.evidence?.frames ?? [];
  return frames.find((f) => f.app === app) ?? frames[0];
}

/** Zone utile d'une capture plein écran (1920×1200) : le bot place Brave sur les 2/3 gauches et
 *  l'Explorateur sur le tiers droit, donc la liste des PDF et la pièce jointe Gmail sont toujours au même endroit. */
const FOCUS: Record<string, { x: number; y: number }> = {
  "explorer.exe": { x: 1455, y: 165 }, // liste des PDF, fichier sélectionné
  "brave.exe": { x: 330, y: 470 },     // réponse Gmail avec la pièce jointe
};

function Crop({ frame, w, h, scale, focus, className = "" }: {
  frame: Pick<Frame, "frame_id" | "app"> & { label?: string }; w: number; h: number; scale: number;
  focus?: { x: number; y: number }; className?: string;
}) {
  const f = focus ?? FOCUS[frame.app] ?? { x: 0, y: 0 };
  return (
    <span className={`relative inline-block overflow-hidden bg-soft ${className}`} style={{ width: w, height: h }}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={`/api/frame/${frame.frame_id}`} alt={frame.label}
           style={{ position: "absolute", maxWidth: "none", width: 1920 * scale, left: -f.x * scale, top: -f.y * scale }} />
    </span>
  );
}

function fmtTime(iso?: string) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export default function Home() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [mode, setMode] = useState("verification");
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    const d = await fetch("/api/mails", { cache: "no-store" }).then((r) => r.json());
    setEntries(d.entries);
    setMode(d.mode);
    setSelected((s) => s ?? d.entries.find((e: Entry) => e.status === "brouillon")?.id ?? d.entries[0]?.id ?? null);
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  useEffect(() => {
    fetch("/api/workflows").then((r) => r.json()).then((d) => setWorkflow(d.workflows?.[0] ?? null)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 5000);
    return () => clearTimeout(t);
  }, [toast]);

  const entry = entries.find((e) => e.id === selected) ?? null;
  const drafts = useMemo(() => entries.filter((e) => e.status === "brouillon").length, [entries]);

  async function switchMode(m: string) {
    setMode(m);
    await fetch("/api/mode", { method: "POST", body: JSON.stringify({ mode: m }) });
    setToast(m === "auto" ? `Auto : j'envoie seul quand je suis sûr à ${AUTO_THRESHOLD}/100` : "Je prépare, tu valides");
  }

  async function runNow() {
    setRunning(true);
    const r = await fetch("/api/run", { method: "POST" });
    setRunning(false);
    setToast(r.ok ? "C'est parti : la souris va bouger quelques secondes" : "Impossible de lancer screenpipe");
  }

  return (
    <div className="flex min-h-dvh flex-col gap-3 p-3">
      <Header entry={entry} drafts={drafts} mode={mode} running={running} workflow={workflow}
              onMode={switchMode} onRun={runNow} />

      <div className="flex flex-wrap items-start gap-3">
        <MailList entries={entries} selected={selected} onSelect={setSelected} />
        <main className="flex min-w-0 flex-[999_1_560px] flex-col gap-3">
          {entry ? (
            isReview(entry)
              ? <Review key={entry.id} entry={entry} onDone={(m) => { setToast(m); load(); }} />
              : <Draft key={entry.id} entry={entry} onDone={(m) => { setToast(m); load(); }} />
          ) : (
            <section className="rv rounded-[28px] bg-card p-10 text-center text-muted">
              Rien à traiter pour l&apos;instant.
            </section>
          )}
        </main>
      </div>

      {toast && (
        <div role="status" className="rv fixed bottom-5 left-1/2 z-50 max-w-[90vw] -translate-x-1/2 rounded-full bg-ink px-5 py-3 text-sm text-white shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}

function Header({ entry, drafts, mode, running, workflow, onMode, onRun }: {
  entry: Entry | null; drafts: number; mode: string; running: boolean; workflow: Workflow | null;
  onMode: (m: string) => void; onRun: () => void;
}) {
  const review = entry && isReview(entry);
  const frame = pickFrame(entry, "explorer.exe");
  return (
    <header className="flex flex-col gap-10 rounded-[28px] bg-ink px-6 pb-9 pt-6 text-white sm:px-8">
      <div className="flex flex-wrap items-center gap-4">
        <span className="text-2xl font-semibold tracking-[-0.04em]">déjà-vu</span>
        {workflow && (
          <span className="hidden max-w-sm truncate text-sm text-white/60 lg:block" title={workflow.title}>
            appris par screenpipe : {workflow.title}
          </span>
        )}
        <div role="group" aria-label="Mode de l'agent" className="ml-auto flex rounded-full bg-white/12 p-1">
          {[["verification", "Je valide"], ["auto", "Auto"]].map(([m, label]) => (
            <button key={m} type="button" aria-pressed={mode === m} onClick={() => onMode(m)}
                    className={`min-h-10 rounded-full px-4 text-sm transition ${mode === m ? "bg-white font-semibold text-ink" : "text-white/80 hover:text-white"}`}>
              {label}
            </button>
          ))}
        </div>
        <button type="button" onClick={onRun} disabled={running}
                className="min-h-12 rounded-full bg-mint px-5 text-[15px] font-semibold text-ink transition hover:brightness-95 disabled:opacity-60">
          {running ? "Lancement…" : "Traiter maintenant"}
        </button>
      </div>

      <div key={entry?.id ?? "vide"}>
        <h1 className="m-0 text-[44px] font-medium leading-none tracking-[-0.045em] sm:text-[72px]">
          {review ? (
            <>
              <span className="word"><span>Celui-là</span></span>{" "}
              <span aria-hidden="true" className="rv d2 wob mx-1 inline-grid h-[46px] w-[76px] place-items-center rounded-2xl bg-blush align-middle text-[34px] font-semibold text-ink sm:h-[60px] sm:w-[100px] sm:text-[44px]">?</span>{" "}
              <span className="word"><span style={{ animationDelay: ".1s" }}>je te le laisse.</span></span>
            </>
          ) : (
            <>
              <span className="word"><span>{drafts} brouillon{drafts > 1 ? "s" : ""}</span></span>{" "}
              {frame && <Crop frame={frame} w={150} h={64} scale={0.75} className="rv d2 mx-1 rounded-2xl align-middle" />}{" "}
              <span className="word"><span style={{ animationDelay: ".1s" }}>{drafts > 1 ? "t'attendent." : "t'attend."}</span></span>
            </>
          )}
        </h1>
        <p className="rv d2 mt-3.5 text-[17px] text-white/70">
          {review ? "Je ne réponds jamais seul à ce que je ne t'ai pas vu faire." : "Je les ai préparés en refaisant ce que screenpipe t'a vu faire."}
        </p>
      </div>
    </header>
  );
}

function MailList({ entries, selected, onSelect }: { entries: Entry[]; selected: string | null; onSelect: (id: string) => void }) {
  return (
    <nav aria-label="Mails" className="rv d1 w-full rounded-[28px] bg-card p-3 md:w-auto md:max-w-[320px] md:flex-[1_1_260px]">
      <ul className="max-h-[34vh] overflow-y-auto md:max-h-[60vh]">
        {entries.map((e) => {
          const active = e.id === selected;
          return (
            <li key={e.id} className="mb-1">
              <button type="button" onClick={() => onSelect(e.id)} aria-current={active}
                      className={`flex w-full items-center justify-between gap-3 rounded-[18px] px-4 py-3.5 text-left transition ${active ? "bg-ink text-white" : "hover:bg-soft"}`}>
                <span className="min-w-0">
                  <span className="block truncate font-semibold">{e.subject ?? e.preview ?? "Mail"}</span>
                  <span className={`block text-[13px] ${active ? "text-white/65" : "text-muted"}`}>
                    {(e.sender || "Inconnu")} · {isReview(e) ? "à vérifier" : statusLabel(e)}
                  </span>
                </span>
                {isReview(e) && <span aria-hidden="true" className="h-2.5 w-2.5 flex-none rounded-full bg-[#FF8A80]" />}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

function MailHeader({ entry, highlight }: { entry: Entry; highlight?: boolean }) {
  const body = (entry.body ?? entry.preview ?? "").trim();
  const quote = body.split("\n").filter((l) => l.trim() && !/^(bonjour|salut|hello|coucou|merci|cordialement|bonne|a\+|karim)\b/i.test(l.trim())).join(" ");
  return (
    <div>
      <div className="text-sm text-muted">{entry.sender ? `${entry.sender}` : "Expéditeur inconnu"}</div>
      <h2 className="mt-1 text-[30px] font-medium leading-[1.1] tracking-[-0.04em] sm:text-4xl">{entry.subject ?? "Mail sans sujet"}</h2>
      {(quote || body) && (
        <p className={`mt-3 rounded-2xl px-[18px] py-3.5 text-body ${highlight ? "bg-blush/50" : "bg-soft"}`}>« {quote || body} »</p>
      )}
    </div>
  );
}

function Draft({ entry, onDone }: { entry: Entry; onDone: (msg: string) => void }) {
  const editable = entry.status === "brouillon";
  const [text, setText] = useState(entry.final_text ?? entry.reply ?? "");
  const [busy, setBusy] = useState<null | "send" | "reject">(null);
  const [zoom, setZoom] = useState(false);
  const frame = pickFrame(entry);
  const ev = entry.evidence;
  const score = entry.score ?? 0;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setZoom(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function act(reject: boolean) {
    setBusy(reject ? "reject" : "send");
    const changed = text !== (entry.reply ?? "");
    const d = await fetch("/api/approve", {
      method: "POST",
      body: JSON.stringify({ id: entry.id, reject, text: !reject && changed ? text : undefined }),
    }).then((r) => r.json());
    setBusy(null);
    onDone(d.ok ? (reject ? "Brouillon rejeté" : "Envoyé depuis Gmail") : `Échec : ${d.message}`);
  }

  return (
    <>
      <section aria-label="Réponse préparée" className="rv d2 flex flex-col gap-5 rounded-[28px] bg-card p-6 sm:px-9 sm:py-8">
        <MailHeader entry={entry} />

        <div>
          <label htmlFor="reply" className="mb-2 block text-sm text-muted">
            {editable ? "Ta réponse" : entry.status === "envoyé" ? `Envoyée${entry.decided_at ? ` le ${fmtTime(entry.decided_at)}` : ""}` : "Réponse"}
          </label>
          <textarea id="reply" value={text} onChange={(e) => setText(e.target.value)} readOnly={!editable} rows={6}
                    className="w-full resize-y rounded-[18px] border border-line bg-card px-5 py-[18px] text-[17px] leading-relaxed outline-none transition focus:border-ink read-only:bg-soft" />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          {entry.file && (
            <a href={`/api/file?name=${encodeURIComponent(entry.file)}`} target="_blank"
               className="flex min-w-0 items-center gap-2.5 rounded-full bg-soft py-2 pl-2 pr-4 text-sm no-underline transition hover:bg-line">
              <span className="rounded-full bg-clay px-2.5 py-1 font-mono text-[11px] text-white">PDF</span>
              <span className="truncate">{entry.file}</span>
            </a>
          )}
          {editable && (
            <div className="flex gap-2">
              <button type="button" onClick={() => act(true)} disabled={!!busy}
                      className="min-h-[52px] rounded-full border border-[#D6D4D0] px-5 text-[15px] transition hover:bg-soft disabled:opacity-50">
                {busy === "reject" ? "…" : "Rejeter"}
              </button>
              <button type="button" onClick={() => act(false)} disabled={!!busy}
                      className="min-h-[52px] rounded-full bg-ink px-7 text-[15px] font-semibold text-white transition hover:bg-[#2a2b2b] disabled:opacity-50">
                {busy === "send" ? "Envoi via Gmail…" : "Envoyer"}
              </button>
            </div>
          )}
        </div>
        {entry.error && <p className="rounded-2xl bg-blush px-4 py-3 text-sm">{entry.error}</p>}
      </section>

      {!!entry.context?.facts?.length && (
        <section aria-label="Ce que je me suis rappelé" className="rv d3 rounded-[28px] bg-card p-6 sm:px-9">
          <h3 className="m-0 text-[22px] font-medium tracking-[-0.035em]">Ce que je me suis rappelé</h3>
          <ul className="mt-4 flex flex-col gap-3">
            {entry.context.facts.map((f) => (
              <li key={`${f.topic}-${f.value}`} className="flex flex-wrap items-center gap-4 rounded-[20px] bg-soft p-3 pr-5">
                <Crop frame={f} w={150} h={84} scale={0.3} focus={{ x: 260, y: 250 }} className="flex-none rounded-2xl" />
                <div className="min-w-0 flex-[1_1_240px]">
                  <span className="rounded-full bg-peach px-3 py-1 text-[15px] font-semibold">{f.value}</span>
                  <p className="mb-0 mt-2 text-[15px] text-body">« {f.quote} »</p>
                  <p className="m-0 mt-1 font-mono text-xs text-muted">vu à l&apos;écran · {f.window.split(" - ")[0] || f.app} · {fmtTime(f.timestamp)}</p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
      {!!entry.context?.missing?.length && (
        <p className="rv d3 rounded-[28px] bg-blush px-7 py-5">
          On me demande {entry.context.missing.join(" et ")}, mais je ne l&apos;ai vu nulle part : complète avant d&apos;envoyer.
        </p>
      )}

      <section aria-label="Pourquoi je suis sûr" className="rv d3 flex flex-wrap items-center gap-6 rounded-[28px] bg-mint p-6">
        {frame && (
          <button type="button" onClick={() => setZoom(true)} aria-label="Agrandir la capture screenpipe"
                  className="flex-none overflow-hidden rounded-2xl transition hover:scale-[1.02]">
            <Crop frame={frame} w={240} h={130} scale={0.5} className="block" />
          </button>
        )}
        <div className="min-w-0 flex-[1_1_260px]">
          <div className="text-[26px] font-medium leading-[1.15] tracking-[-0.035em]">
            {ev?.unit === "démonstrations" && ev.observations
              ? `Tu me l'as montré ${ev.observations} fois.`
              : frame ? "Je t'ai déjà vu faire ça." : "Pas de capture pour celui-là."}
          </div>
          <p className="mb-3.5 mt-1.5 text-[15px]">
            {frame ? `Même demande, même fichier. Capturé par screenpipe le ${fmtTime(frame.timestamp)}.` : "La décision repose sur le workflow appris."}
          </p>
          <div className="flex items-center gap-3">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink/12">
              <div className="bar h-full rounded-full bg-ink" style={{ width: `${score}%` }} />
            </div>
            <span className="font-mono text-sm font-medium">{score}/100</span>
          </div>
          {entry.reasons && (
            <details className="mt-3 text-sm">
              <summary className="cursor-pointer select-none underline underline-offset-2">Le détail</summary>
              <ul className="mt-2 space-y-1">
                {entry.reasons.map(([pts, txt]) => (
                  <li key={txt} className="flex gap-3"><span className="w-14 flex-none text-right font-mono">{pts}</span><span>{txt}</span></li>
                ))}
              </ul>
            </details>
          )}
        </div>
      </section>

      {zoom && frame && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-ink/80 p-4" onClick={() => setZoom(false)} role="dialog" aria-label={frame.label}>
          <figure className="max-h-full max-w-6xl overflow-auto rounded-[28px] bg-card">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`/api/frame/${frame.frame_id}`} alt={frame.label} className="w-full" />
            <figcaption className="px-5 py-4 text-sm">{frame.label} · {fmtTime(frame.timestamp)}</figcaption>
          </figure>
        </div>
      )}
    </>
  );
}

function Review({ entry, onDone }: { entry: Entry; onDone: (msg: string) => void }) {
  const [busy, setBusy] = useState(false);
  const why = entry.sensitive
    ? "Ça parle d'argent ou de juridique : je n'ai rien touché."
    : entry.status === "erreur"
      ? "Quelque chose a coincé pendant que je rejouais ton geste : je n'ai rien envoyé."
      : "Je ne t'ai jamais vu traiter ce genre de mail : je n'ai rien touché.";

  async function teach() {
    setBusy(true);
    const d = await fetch("/api/teach", { method: "POST" }).then((r) => r.json());
    setBusy(false);
    onDone(d.ok ? "screenpipe t'observe pendant 10 min : traite ce mail dans Gmail comme d'habitude" : "screenpipe indisponible");
  }

  async function ignore() {
    const d = await fetch("/api/approve", { method: "POST", body: JSON.stringify({ id: entry.id, reject: true }) }).then((r) => r.json());
    onDone(d.ok ? "Ignoré" : `Échec : ${d.message}`);
  }

  return (
    <>
      <section aria-label="Mail reçu" className="rv d2 rounded-[28px] bg-card p-6 sm:px-9 sm:py-8">
        <MailHeader entry={entry} highlight />
      </section>
      <section aria-label="Décision" className="rv d3 flex flex-col gap-3.5 rounded-[28px] bg-blush p-6 sm:px-9 sm:py-8">
        <h3 className="m-0 text-[30px] font-medium leading-[1.15] tracking-[-0.04em]">Jamais vu. Tu veux me montrer ?</h3>
        <p className="m-0 max-w-[600px]">{why} Traite-le une fois devant screenpipe, je saurai faire la prochaine fois.</p>
        <div className="flex flex-wrap gap-2 pt-1.5">
          <button type="button" onClick={teach} disabled={busy}
                  className="flex min-h-[52px] items-center gap-2.5 rounded-full bg-ink pl-5 pr-6 text-[15px] font-semibold text-white transition hover:bg-[#2a2b2b] disabled:opacity-60">
            <span className="rec h-2.5 w-2.5 rounded-full bg-coral" />
            Montre-moi une fois
          </button>
          <button type="button" onClick={ignore}
                  className="min-h-[52px] rounded-full border border-ink/25 px-[22px] text-[15px] transition hover:bg-white/40">
            Ignorer
          </button>
        </div>
      </section>
    </>
  );
}
