"""Preuves screenpipe et score de confiance d'une décision de l'agent."""
import json
from datetime import datetime, timedelta
from pathlib import Path

from screenpipe_client import get, search_all

TRAINING_LOG = Path(__file__).resolve().parent.parent / "training_bot" / "scenarios_log.jsonl"

SENSITIVE = ["avocat", "juridique", "litige", "mise en demeure", "résiliation", "résilier", "remboursement",
             "paiement", "virement", "rib", "iban", "urgent", "plainte"]
AUTO_THRESHOLD = 80


def _frames(q, app, start, end, limit=3):
    """Priorité aux sessions étoilées (là où l'utilisateur a montré le geste), sinon tout l'historique."""
    for starred in (True, False):
        d = get("/search", q=q, content_type="ocr", app_name=app, limit=limit, starred_only=str(starred).lower(),
                start_time=start.isoformat(), end_time=end.isoformat())
        rows = [r["content"] for r in d["data"] if r["content"].get("frame_id")]
        if rows:
            break
    return d["pagination"].get("total", len(rows)), [
        {"frame_id": r["frame_id"], "timestamp": r["timestamp"], "app": r.get("app_name"),
         "window": r.get("window_name")} for r in rows]


def shown_examples(file_name):
    """Exécutions de démonstration (journal d'entraînement) qui ont porté sur ce fichier."""
    if not TRAINING_LOG.exists():
        return []
    rows = [json.loads(l) for l in TRAINING_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r for r in rows if r.get("sent") and Path(r["file"]).name == file_name]


def demo_frames(example, stem):
    """Captures précises d'une démonstration : l'Explorateur avec le fichier présélectionné, puis Gmail
    au moment où le fichier y est déposé (app_switch vers Brave portant le nom du fichier)."""
    end = datetime.fromisoformat(example["time"]).astimezone()
    events = search_all(end - timedelta(seconds=90), end + timedelta(seconds=5), max_rows=40, content_type="input")
    explorer = [e["content"] for e in events
                if (e["content"].get("app_name") or "").lower() == "explorer.exe" and e["content"].get("frame_id")]
    dropped = [e["content"] for e in events
               if (e["content"].get("app_name") or "").lower() == "brave.exe"
               and e["content"].get("element_name") in (stem, example["file"]) and e["content"].get("frame_id")]
    out = []
    if explorer:
        c = explorer[-1]
        out.append({"frame_id": c["frame_id"], "timestamp": c["timestamp"], "app": "explorer.exe",
                    "window": c.get("window_title") or "", "label": f"You pick {stem} in File Explorer"})
    if dropped:
        c = dropped[0]
        out.append({"frame_id": c["frame_id"], "timestamp": c["timestamp"], "app": "brave.exe",
                    "window": c.get("window_title") or "", "label": f"You drag it into your reply to “{example['subject']}”"})
    return out


def past_evidence(file_name, days=7):
    """Moments où l'utilisateur a déjà fait ce geste : fichier pris dans l'Explorateur, puis glissé
    dans Gmail. Ce sont les « sources » affichées dans l'interface."""
    stem = file_name.rsplit(".", 1)[0]
    examples = shown_examples(file_name)
    if examples:
        try:
            frames = []
            for ex in reversed(examples[-4:]):  # les démonstrations les plus récentes d'abord
                frames = demo_frames(ex, stem)
                if len(frames) == 2:
                    break
            mem = get("/search", content_type="memory", q=stem, limit=1,
                      start_time=(datetime.now().astimezone() - timedelta(days=days)).isoformat(),
                      end_time=datetime.now().astimezone().isoformat())["data"]
            if frames:
                memory = mem[0]["content"] if mem else None
                return {"frames": frames, "observations": len(examples), "unit": "démonstrations",
                        "memory": {"id": memory.get("id"), "text": (memory.get("content") or memory.get("text") or "")[:500]}
                        if memory else None}
        except Exception:
            pass  # on retombe sur la recherche plein texte ci-dessous
    end = datetime.now().astimezone()
    start = end - timedelta(days=days)
    try:
        n_gmail, gmail = _frames(f'"pièce jointe {file_name}"', "brave.exe", start, end, 2)
        _, explorer = _frames(stem, "explorer.exe", start, end, 1)
        mem = get("/search", content_type="memory", q=stem, limit=1,
                  start_time=start.isoformat(), end_time=end.isoformat())["data"]
    except Exception as e:  # screenpipe indisponible : la décision reste possible, sans preuve
        return {"error": str(e), "frames": [], "observations": 0, "memory": None}
    for f in explorer:
        f["label"] = "You selected this file in File Explorer"
    for f in gmail:
        f["label"] = "You attached it to a Gmail reply"
    memory = mem[0]["content"] if mem else None
    return {"frames": explorer + gmail, "observations": n_gmail,
            "memory": {"id": memory.get("id"), "text": (memory.get("content") or memory.get("text") or "")[:500]}
            if memory else None}


UNIT_EN = {"démonstrations": "demonstrations", "captures": "captures"}
SCENARIO_EN = {"devis": "quote", "facture": "invoice", "contrat": "contract", "planning": "schedule",
               "maquette": "mockup", "cahier": "specs"}


def confidence(pb, margin, file_exists, sender_known, text, evidence):
    """Score 0-100 + raisons lisibles. Règles simples et défendables (cf. plan) ; un mail sensible
    passe toujours en vérification humaine, quel que soit le score."""
    reasons, score = [], 0
    if margin >= 1:
        score += 35
        reasons.append(("+35", f"request type recognised: “{SCENARIO_EN.get(pb['scenario'], pb['scenario'])}” workflow"))
    if file_exists:
        score += 15
        reasons.append(("+15", f"file found: {pb['variables']['fichier']}"))
    n = pb["observations"]["executions_analysees"]
    if n >= 5:
        score += 20
        reasons.append(("+20", f"workflow learned from {n} observed runs"))
    if evidence.get("frames"):
        score += 15
        reasons.append(("+15", f"gesture found in screenpipe ({evidence.get('observations', 0)} "
                               f"{UNIT_EN.get(evidence.get('unit'), 'captures')})"))
    if sender_known:
        score += 15
        reasons.append(("+15", "sender seen before"))
    else:
        reasons.append(("+0", "unknown sender"))
    hits = [w for w in SENSITIVE if w in text.lower()]
    if hits:
        reasons.append(("bloquant", f"sensitive mail ({', '.join(hits)}): always checked by a human"))
    return min(score, 100), reasons, bool(hits)
