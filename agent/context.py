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
    "livraison": ["livraison", "livrer", "délai"],
    "bug": ["bug", "correctif", "corriger", "formulaire"],
    "dispo": ["dispo", "disponible", "se voir", "créneau"],
    "facture": ["facture", "compta", "comptable"],
}
SEARCH = {"prix": ["prix", "HT"], "livraison": ["livraison"], "bug": ["bug"], "dispo": ["dispo", "libre"],
          "facture": ["facture"]}

MONEY = re.compile(r"\d{1,3}(?:[\s  .]\d{3})*(?:,\d+)?\s?(?:€|EUR)(?:\s?HT)?")
MONTHS = "janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre"
DATE = re.compile(rf"(?:(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+)?\d{{1,2}}(?:er)?\s+(?:{MONTHS})"
                  rf"(?:\s+après-midi|\s+matin)?", re.I)
NOISE = ("gmail", "déjà-vu", "localhost:300", "claude")  # le mail lui-même, notre interface, la conversation


DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
AGENDA_WORDS = ["réunion", "reunion", "rdv", "rendez-vous", "heure", "quand", "dispo", "agenda", "planning"] + DAYS


# libellés anglais des sujets, pour l'interface
TOPIC_EN = {"prix": "price", "facture": "invoice", "livraison": "delivery date", "bug": "bug details",
            "dispo": "availability", "jour": "day", "reunion": "meeting"}


def topics_of(text):
    t = text.lower()
    return [k for k, words in TOPICS.items() if any(w in t for w in words)]


def _dedup(lines):
    out = []
    for l in lines:
        if not out or out[-1] != l:
            out.append(l)
    return out


def agenda_context(text, days=7):
    """Questions d'agenda (« à quelle heure la réunion lundi ? ») : relit l'agenda vu à l'écran.
    Renvoie des faits « jour » (ce qui est prévu ce jour-là) et « réunion » (où sont les réunions)."""
    t = text.lower()
    if not any(w in t for w in AGENDA_WORDS):
        return []
    end = datetime.now().astimezone()
    try:
        rows = get("/search", q="Après-midi", content_type="ocr", app_name="brave.exe", limit=10,
                   start_time=(end - timedelta(days=days)).isoformat(), end_time=end.isoformat())["data"]
    except Exception:
        return []
    for r in rows:
        c = r["content"]
        raw = [" ".join(l.split()) for l in (c.get("text") or "").splitlines() if l.strip()]
        if "Après-midi" not in raw:
            continue  # pas le tableau de l'agenda (ex. le lien « Agenda » de Gmail)
        meta = {"frame_id": c.get("frame_id"), "timestamp": c["timestamp"], "app": c.get("app_name"),
                "window": c.get("window_name") or ""}
        day_re = re.compile(rf"^({'|'.join(DAYS)})\s+\d{{1,2}}$", re.I)
        starts = [i for i, l in enumerate(raw) if day_re.match(l)]
        table = {}
        for n, i in enumerate(starts):
            label = raw[i]
            nxt = starts[n + 1] if n + 1 < len(starts) else min(len(raw), i + 6)
            cells = [l for l in raw[i:nxt] if l != label]
            if len(cells) >= 4 and len(cells) % 2 == 0:
                cells = cells[::2]  # chaque case est capturée deux fois (texte + accessibilité)
            cells = _dedup(cells) if len(cells) > 2 else cells
            if len(cells) >= 2:
                table[day_re.match(label).group(1).lower()] = (label, cells[0], cells[1])
        if not table:
            continue
        facts = []
        for day in DAYS:
            if day in t and day in table:
                label, am, pm = table[day]
                facts.append({"topic": "jour", "value": label, "quote": f"{label} : matin {am}, après-midi {pm}", **meta})
        if any(w in t for w in ("dispo", "disponible", "se voir", "se voit", "créneau", "quand")):
            for label, am, pm in table.values():
                for slot, what in (("matin", am), ("après-midi", pm)):
                    if "libre" in what.lower() or "dispo" in what.lower():
                        facts.append({"topic": "dispo", "value": f"{label} {slot}", "quote": f"{label}, {slot} : {what}", **meta})
        if any(w in t for w in ("réunion", "reunion", "rdv", "rendez-vous", "heure")):
            for label, am, pm in table.values():
                for slot, what in (("matin", am), ("après-midi", pm)):
                    if "réunion" in what.lower():
                        facts.append({"topic": "reunion", "value": f"{label} {slot}", "quote": f"{label}, {slot} : {what}", **meta})
        return facts
    return []


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
                # d'abord ce que l'utilisateur a montré exprès (sessions étoilées), puis le navigateur, puis tout
                for app, starred in (("brave.exe", "true"), ("brave.exe", None), (None, None)):
                    try:
                        rows += get("/search", q=q, content_type="ocr", limit=20, app_name=app, starred_only=starred,
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
                            amount = re.sub(r"[^\d,]", "", value).split(",")[0]
                            if topic in ("prix", "facture") and (not amount or int(amount) < 50):
                                continue  # trop petit pour être un prix de prestation (pub, abonnement…)
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
    agenda = agenda_context(f"{subject}\n{body}")
    if agenda:
        wanted = wanted + ["agenda"]
        facts = facts + agenda
        limit += len(agenda)
    return {"asked": wanted, "facts": facts[:limit],
            "missing": [t for t in wanted if t in ("prix", "livraison", "bug", "dispo")
                        and not any(f["topic"] == t for f in facts)
                        and not (t in ("dispo", "livraison") and agenda)]}


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
    jours = [f for f in facts if f["topic"] == "jour"]
    reunions = [f for f in facts if f["topic"] == "reunion"]
    for j in jours:
        day = j["value"]
        same = [r for r in reunions if r["value"].startswith(day)]
        if same:
            parts.append(f"{day}, c'est {same[0]['value'][len(day):].strip()} : {same[0]['quote'].split(' : ', 1)[-1]}.")
        else:
            occupation = j["quote"].split(" : ", 1)[-1]
            parts.append(f"{day}, je n'ai pas de réunion de prévue ({occupation}).")
    others = [r for r in reunions if not any(r["value"].startswith(j["value"]) for j in jours)]
    if others and (jours or not parts):
        r = others[0]
        parts.append(f"La prochaine, c'est {r['quote'].split(' : ', 1)[-1]}, {r['value'].lower()}.")
    return " ".join(parts)


if __name__ == "__main__":
    import json
    print(json.dumps(find_context(*sys.argv[1:4]), ensure_ascii=False, indent=1))
