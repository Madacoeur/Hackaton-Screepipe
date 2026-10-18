"""Recalcule preuves screenpipe et score de confiance pour les entrées déjà dans agent_log.jsonl
(utile après un changement de evidence.py, ou pour les entrées antérieures au score).

    python agent/backfill_evidence.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "training_bot"))

from evidence import confidence, past_evidence  # noqa: E402
from run_agent import LOG, choose_playbook, known_senders, load_playbooks  # noqa: E402


def main():
    playbooks = load_playbooks()
    senders = known_senders(playbooks)
    lines = LOG.read_text(encoding="utf-8").split("\n")
    cache, out = {}, []
    for i, line in enumerate(lines):
        if not line.strip():
            out.append(line)
            continue
        e = json.loads(line)
        e.setdefault("id", f"L{i}")  # même identifiant que celui déjà affiché par l'interface
        if e.get("file") and e.get("scenario") in playbooks:
            pb = playbooks[e["scenario"]]
            if e["file"] not in cache:
                cache[e["file"]] = past_evidence(e["file"])
            ev = cache[e["file"]]
            text = f"{e.get('subject', '')}\n{e.get('body', '')}"
            _, margin = choose_playbook(playbooks, text)
            score, reasons, sensitive = confidence(pb, max(margin, 1), True,
                                                   (e.get("sender") or "").lower() in senders, text, ev)
            e.update(evidence=ev, score=score, reasons=reasons, sensitive=sensitive,
                     steps=e.get("steps") or [s["action"] for s in pb["etapes"]])
            print(f"{e['id']:14} {e.get('subject', '')[:30]:30} score {score}")
        out.append(json.dumps(e, ensure_ascii=False))
    LOG.write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main()
