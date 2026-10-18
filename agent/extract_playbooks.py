"""Relit les sessions d'entraînement enregistrées par screenpipe et en tire un playbook
par type de demande : "quand on me réclame X, voilà ce que je fais".

    python agent/extract_playbooks.py

Entrées : training_bot/scenarios_log.jsonl (vérité terrain : quand, quel mail, quel fichier)
          + l'API screenpipe (ce qui a réellement été fait à l'écran).
Sortie  : agent/playbooks/<scenario>.json + agent/playbooks/index.json
"""
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from screenpipe_client import search_all

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "training_bot" / "scenarios_log.jsonl"
OUT = ROOT / "agent" / "playbooks"
sys.path.insert(0, str(ROOT / "training_bot"))
from scenarios import SCENARIOS  # noqa: E402

BEFORE, AFTER = timedelta(seconds=90), timedelta(seconds=5)


# ------------------------------------------------------------------ trace d'un cycle

def fetch_trace(entry):
    end = datetime.fromisoformat(entry["time"]).astimezone()
    start = end - BEFORE
    events = search_all(start, end + AFTER, content_type="input")
    # écran Gmail juste avant l'envoi : prouve la pièce jointe et le texte tapé
    screens = search_all(end - timedelta(seconds=40), end + AFTER, max_rows=40,
                         content_type="accessibility", app_name="brave.exe")
    return events, screens


def to_steps(entry, events, screens):
    """Transforme les événements bruts en étapes lisibles, sans doublons consécutifs."""
    path = Path(entry["file"])
    subject = entry["subject"]
    steps = []

    def add(action, **kw):
        if not steps or steps[-1]["action"] != action:
            steps.append({"action": action, **kw})

    for r in events:
        c = r["content"]
        kind, app = c.get("event_type"), (c.get("app_name") or "").lower()
        title, elem = c.get("window_title") or "", c.get("element_name") or ""
        ts = c["timestamp"][11:19]
        if app == "brave.exe" and kind == "window_focus":
            if subject and title.startswith(subject):
                seen = any(s["action"] == "ouvrir_mail" for s in steps)
                add("revenir_dans_gmail" if seen else "ouvrir_mail", app="Gmail", at=ts)
            elif "Boîte de réception" in title:
                add("ouvrir_boite_reception", app="Gmail", at=ts)
        if app == "explorer.exe" and kind in ("app_switch", "window_focus") and path.parent.name in title:
            add("ouvrir_explorateur", app="Explorateur", dossier=path.parent.name, at=ts)
        if kind == "click" and app == "explorer.exe":
            add("selectionner_fichier", app="Explorateur", at=ts)
        if app == "brave.exe" and kind == "app_switch" and elem in (path.stem, path.name):
            add("glisser_fichier_dans_gmail", fichier=path.name, at=ts)

    screen_text = "\n".join(r["content"].get("text") or "" for r in screens)
    if path.name in screen_text:
        add("verifier_piece_jointe", fichier=path.name)
    first_line = next((l for l in entry["reply"].splitlines() if l.strip()), "")
    if first_line and first_line in screen_text:
        add("rediger_reponse", ton="tutoiement", exemple=entry["reply"])
    if entry.get("sent"):
        add("envoyer")
    return steps


# ------------------------------------------------------------------ agrégation

MIN_SUPPORT = 0.10  # une étape vue dans moins de 10 % des exécutions est considérée comme du bruit


def build_playbook(key, cycles):
    """Toutes les étapes récurrentes, dans leur ordre habituel, avec leur taux d'observation.
    (Une étape peut manquer d'une trace parce que screenpipe n'a pas capturé l'écran à ce moment-là.)"""
    n = len(cycles)
    seqs = Counter(tuple(s["action"] for s in c["steps"]) for c in cycles)
    freq = seqs.most_common(1)[0][1]
    positions = {}
    for c in cycles:
        acts = [s["action"] for s in c["steps"]]
        for a in set(acts):
            positions.setdefault(a, []).append(acts.index(a) / max(1, len(acts) - 1))
    support = {a: len(p) / n for a, p in positions.items()}
    canonical = sorted((a for a in positions if support[a] >= MIN_SUPPORT),
                       key=lambda a: sorted(positions[a])[len(positions[a]) // 2])
    files = Counter(Path(c["entry"]["file"]).name for c in cycles)
    folder = Path(cycles[0]["entry"]["file"]).parent
    return {
        "scenario": key,
        "declencheur": {
            "type": "mail_entrant",
            "mots_cles": SCENARIOS[key]["keywords"],
            "sujets_observes": sorted({c["entry"]["subject"] for c in cycles}),
        },
        "variables": {
            "expediteur": "prénom de l'expéditeur du mail",
            "fichier": files.most_common(1)[0][0],
            "dossier": str(folder),
        },
        "etapes": [
            {"ordre": i + 1, "action": a, "vu_dans": f"{support[a]:.0%} des exécutions"}
            for i, a in enumerate(canonical)
        ],
        "exemples_de_reponse": [c["entry"]["reply"] for c in cycles[-3:]],
        "observations": {
            "executions_analysees": n,
            "sequence_identique": f"{freq}/{n}",
            "premiere": cycles[0]["entry"]["time"],
            "derniere": cycles[-1]["entry"]["time"],
        },
    }


def main():
    entries = [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    entries = [e for e in entries if e.get("sent")]
    print(f"{len(entries)} exécutions à relire dans screenpipe...")

    by_scenario, skipped = {}, 0
    for i, e in enumerate(entries, 1):
        events, screens = fetch_trace(e)
        steps = to_steps(e, events, screens)
        ok = {"ouvrir_mail", "ouvrir_explorateur", "glisser_fichier_dans_gmail"} <= {s["action"] for s in steps}
        print(f"  [{i:2}/{len(entries)}] {e['time'][11:19]} {e['scenario']:9} {len(events):3} évts -> "
              f"{' > '.join(s['action'] for s in steps) if ok else 'trace incomplète, ignorée'}")
        if ok:
            by_scenario.setdefault(e["scenario"], []).append({"entry": e, "steps": steps})
        else:
            skipped += 1

    OUT.mkdir(parents=True, exist_ok=True)
    index = {}
    for key, cycles in sorted(by_scenario.items()):
        pb = build_playbook(key, cycles)
        (OUT / f"{key}.json").write_text(json.dumps(pb, ensure_ascii=False, indent=2), encoding="utf-8")
        index[key] = {"fichier": pb["variables"]["fichier"], "executions": len(cycles),
                      "etapes": [s["action"] for s in pb["etapes"]]}
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{len(index)} playbooks écrits dans {OUT} ({skipped} traces incomplètes ignorées)")
    for key, v in index.items():
        print(f"  {key:9} ({v['executions']:2} exécutions) : {' > '.join(v['etapes'])}")


if __name__ == "__main__":
    main()
