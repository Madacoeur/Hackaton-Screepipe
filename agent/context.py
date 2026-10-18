"""Retrouve dans screenpipe ce que l'utilisateur a VU à propos d'un mail (prix, date, engagement)
et le transforme en faits cités : valeur + phrase d'origine + capture (frame) + heure.

    python agent/context.py "Re: prix du site" "Tu peux me confirmer le prix et la date de livraison ?" Karim
"""
import re
import sys
from datetime import datetime, timedelta

from screenpipe_client import get

# thème de la question -> mots à chercher à l'écran
TOPICS = {
    "prix": ["prix", "tarif", "montant", "combien", "coût", "budget", "devis"],
    "livraison": ["livraison", "livrer", "date", "quand", "délai"],
    "bug": ["bug", "correctif", "corriger", "formulaire"],
    "dispo": ["dispo", "disponible", "se voir", "rendez-vous", "point", "réunion", "créneau"],
    "facture": ["facture", "compta", "comptable"],
}
SEARCH = {"prix": ["prix", "HT"], "livraison": ["livraison"], "bug": ["bug"], "dispo": ["dispo", "libre"],
          "facture": ["facture"]}

MONEY = re.compile(r"\d{1,3}(?:[\s  .]\d{3})*(?:,\d+)?\s?(?:€|EUR)(?:\s?HT)?")
MONTHS = "janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre"
DATE = re.compile(rf"(?:(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+)?\d{{1,2}}(?:er)?\s+(?:{MONTHS})"
                  rf"(?:\s+après-midi|\s+matin)?", re.I)
NOISE = ("gmail", "déjà-vu", "localhost:300", "claude")  # le mail lui-même, notre interface, la conversation


def topics_of(text):
    t = text.lower()
    return [k for k, words in TOPICS.items() if any(w in t for w in words)]


def _sentences(text):
    for part in re.split(r"[\n•]|(?<=[.!?])\s+", text or ""):
        part = " ".join(part.split())
        if 8 <= len(part) <= 220:
            yield part


def find_context(subject, body, sender="", days=7, limit=4):
    """Faits retrouvés à l'écran, du plus pertinent au moins pertinent (une source par valeur)."""
    wanted = topics_of(f"{subject}\n{body}")
    end = datetime.now().astimezone()
    start = end - timedelta(days=days)
    facts, seen = [], set()
    for topic in wanted:
        for word in SEARCH.get(topic, []):
            queries = [f"{sender} {word}".strip(), word] if sender else [word]
            for q in queries:
                rows = []
                # d'abord ce qui a été vu dans le navigateur (notes, PDF), puis partout ailleurs
                for app in ("brave.exe", None):
                    try:
                        rows += get("/search", q=q, content_type="ocr", limit=20, app_name=app,
                                    start_time=start.isoformat(), end_time=end.isoformat())["data"]
                    except Exception:
                        pass
                for r in rows:
                    c = r["content"]
                    where = f"{c.get('app_name', '')} {c.get('window_name', '')}".lower()
                    if not c.get("frame_id") or any(n in where for n in NOISE):
                        continue
                    for sent in _sentences(c.get("text")):
                        if word.lower() not in sent.lower():
                            continue
                        pattern = MONEY if topic in ("prix", "facture") else DATE
                        for m in pattern.finditer(sent):
                            value = " ".join(m.group(0).split())
                            if (topic, value) in seen or any(f["topic"] == topic for f in facts):
                                continue  # un seul fait par sujet : le premier trouvé, le plus pertinent
                            seen.add((topic, value))
                            facts.append({"topic": topic, "value": value, "quote": sent, "frame_id": c["frame_id"],
                                          "timestamp": c["timestamp"], "app": c.get("app_name"),
                                          "window": c.get("window_name") or ""})
                if any(f["topic"] == topic for f in facts):
                    break  # trouvé pour ce mot : inutile d'élargir la requête
            if any(f["topic"] == topic for f in facts):
                break
    return {"asked": wanted, "facts": facts[:limit],
            "missing": [t for t in wanted if t in ("prix", "livraison", "bug", "dispo")
                        and not any(f["topic"] == t for f in facts)]}


def fact_sentence(facts):
    """Phrase « pour rappel » écrite dans le ton de l'utilisateur, à partir des faits retrouvés."""
    by = {}
    for f in facts:
        by.setdefault(f["topic"], f["value"])
    parts = []
    if "prix" in by and "livraison" in by:
        parts.append(f"Pour rappel, on était partis sur {by['prix']} avec une livraison le {by['livraison']}.")
    elif "prix" in by:
        parts.append(f"Pour rappel, on était partis sur {by['prix']}.")
    elif "livraison" in by:
        parts.append(f"Pour rappel, la livraison est prévue le {by['livraison']}.")
    if "bug" in by:
        parts.append(f"Je corrige le bug d'ici {by['bug']}, comme promis.")
    if "dispo" in by:
        parts.append(f"Je suis dispo {by['dispo']} si ça te va.")
    if "facture" in by and "prix" not in by:
        parts.append(f"Le montant est de {by['facture']}.")
    return " ".join(parts)


if __name__ == "__main__":
    import json
    print(json.dumps(find_context(*sys.argv[1:4]), ensure_ascii=False, indent=1))
