"""Agent mail : traite les mails non lus en rejouant les workflows appris dans screenpipe.

Pour chaque mail non lu :
  1. choisit le playbook dont les mots-clés correspondent (agent/playbooks/*.json) ;
  2. si aucun ne correspond -> ne touche à rien, le signale pour vérification humaine ;
  3. sinon rejoue les étapes observées : ouvrir le mail, Répondre, ouvrir l'Explorateur sur le
     dossier appris, glisser le fichier dans Gmail, rédiger dans le style des réponses observées ;
  4. calcule un score de confiance et cherche dans screenpipe les moments où l'utilisateur a fait
     le même geste (les « sources ») ;
  5. mode « vérification » (défaut, agent/config.json) : brouillon ; mode « auto » : envoie seulement
     si score >= 80 et mail non sensible. --send force l'envoi.

    python agent/run_agent.py                 # selon le mode, 3 mails max
    python agent/run_agent.py --send          # envoie vraiment
    python agent/run_agent.py --max 5 --dry   # liste juste ce qu'il ferait
"""
import argparse
import json
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "training_bot"))

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.common.keys import Keys  # noqa: E402
from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402

import pyautogui  # noqa: E402
from reply_bot import (ROW, attachment_present, click_reply, drag_file_to, focus_browser,  # noqa: E402
                       get_driver, human_type, layout_windows, open_explorer_on, open_inbox,
                       read_open_mail, screen_center, visible, wait_draft_saved)

sys.path.insert(0, str(ROOT / "agent"))
from context import AGENDA_WORDS, fact_sentence, find_context, topics_of  # noqa: E402
from evidence import AUTO_THRESHOLD, SENSITIVE, confidence, past_evidence  # noqa: E402

try:  # clé Anthropic optionnelle, dans training_bot/.env
    from dotenv import load_dotenv
    load_dotenv(ROOT / "training_bot" / ".env")
except ImportError:
    pass

PLAYBOOKS = ROOT / "agent" / "playbooks"
LOG = ROOT / "agent" / "agent_log.jsonl"
CONFIG = ROOT / "agent" / "config.json"


# ------------------------------------------------------------------ décision

def load_playbooks():
    return {p.stem: json.loads(p.read_text(encoding="utf-8"))
            for p in PLAYBOOKS.glob("*.json") if p.name != "index.json"}


def load_mode():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8")).get("mode", "verification")
    except Exception:
        return "verification"


def known_senders(playbooks):
    """Prénoms des interlocuteurs à qui l'utilisateur a déjà répondu (salutation des réponses observées)."""
    names = set()
    for pb in playbooks.values():
        for ex in pb["exemples_de_reponse"]:
            m = re.match(r"^\w+\s+(\S+),", ex)
            if m:
                names.add(m.group(1).lower())
    return names


def choose_playbook(playbooks, text):
    """Playbook dont les mots-clés apparaissent le plus ; None si aucun ou ex aequo (ambigu).
    Renvoie aussi l'écart avec le 2e (marge de certitude)."""
    text = text.lower()
    scores = {k: sum(text.count(kw.lower()) for kw in pb["declencheur"]["mots_cles"]) for k, pb in playbooks.items()}
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    margin = ranked[0][1] - (ranked[1][1] if len(ranked) > 1 else 0) if ranked else 0
    if not ranked or ranked[0][1] == 0 or margin == 0:
        return None, margin
    return ranked[0][0], margin


def write_reply(pb, first_name, subject="", body="", ctx=None):
    """Réponse dans le style observé. Avec ANTHROPIC_API_KEY : Claude rédige à partir des réponses observées
    et des faits retrouvés. Sinon : une réponse réellement envoyée, prénom changé, + la phrase « pour rappel »."""
    facts = (ctx or {}).get("facts", [])
    llm = claude_reply(pb, first_name, subject, body, facts)
    if llm:
        return llm
    example = random.choice(pb["exemples_de_reponse"])
    lines = example.splitlines()
    lines[0] = re.sub(r"^(\w+)\s+\S+,$", lambda m: f"{m.group(1)} {first_name},", lines[0]) if first_name else lines[0]
    rappel = fact_sentence(facts)
    if rappel:
        lines.insert(3 if len(lines) > 3 else len(lines), rappel)  # après la 1re phrase, avant les formules de fin
    return "\n".join(lines)


def claude_reply(pb, first_name, subject, body, facts):
    """Rédaction par Claude (optionnelle). N'utilise QUE les faits retrouvés dans screenpipe."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    sources = "\n".join(f"- {f['topic']} : {f['value']} (vu à l'écran : « {f['quote']} »)" for f in facts) or "- aucun"
    prompt = (f"Tu rédiges la réponse de Table En (freelance, tutoie ses clients) à ce mail.\n"
              f"Mail de {first_name} — {subject} :\n{body}\n\n"
              f"Réponses réellement envoyées par Table En (imite le ton et la longueur) :\n"
              + "\n---\n".join(pb["exemples_de_reponse"][:3])
              + f"\n\nFaits retrouvés dans sa mémoire screenpipe (n'invente rien d'autre) :\n{sources}\n\n"
              f"Le fichier {pb['variables']['fichier']} est joint. Réponds uniquement par le texte du mail, signé « Table En ».")
    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", method="POST",
            data=json.dumps({"model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"), "max_tokens": 400,
                             "messages": [{"role": "user", "content": prompt}]}).encode(),
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r)["content"][0]["text"].strip()
    except Exception as e:
        print(f"[agent] Claude indisponible ({e}), rédaction par modèle de réponse")
        return None


def notify(title, body):
    """Notification dans l'app screenpipe (port 11435, sans auth). Silencieux si indisponible."""
    try:
        req = urllib.request.Request("http://localhost:11435/notify", method="POST",
                                     data=json.dumps({"title": title, "body": body}).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


# ------------------------------------------------------------------ exécution

def already_answered(row):
    """Fil dont le dernier message est de moi ("Karim, moi 3") : la demande a déjà été traitée."""
    senders = row.find_elements(By.CSS_SELECTOR, ".yX")
    names = re.sub(r"\s*\d+$", "", senders[0].text if senders else "").split(",")
    return names[-1].strip().lower() in ("moi", "me")


def unread_rows(driver):
    open_inbox(driver)
    for _ in range(3):
        try:
            return [r for r in visible(driver, ROW)
                    if "zE" in r.get_attribute("class") and not already_answered(r)]
        except StaleElementReferenceException:
            time.sleep(1)
    return []


def run_playbook(driver, pb, row, decide):
    """Rejoue le workflow. `decide(subject, body, first_name, path)` renvoie (send, infos) une fois le mail lu."""
    focus_browser()  # on ne prend la main sur l'écran que s'il y a vraiment un mail à traiter
    layout_windows(driver)
    pyautogui.moveTo(*screen_center(driver, row), duration=0.6)
    row.click()                                                     # ouvrir_mail
    subject, body, first_name = read_open_mail(driver)
    path = Path(pb["variables"]["dossier"]) / pb["variables"]["fichier"]
    send, info = decide(subject, body, first_name, path)
    info.update(subject=subject, body=body, sender=first_name, send=send)
    if not path.exists():
        return info, None, f"fichier introuvable : {path}"

    box = click_reply(driver)                                       # Répondre
    time.sleep(1)
    if not attachment_present(driver, path.name):                   # (brouillon repris : déjà joint)
        _, item = open_explorer_on(path)                            # ouvrir_explorateur + selectionner_fichier
        drag_file_to(item, screen_center(driver, box))              # glisser_fichier_dans_gmail
        focus_browser()                                             # revenir_dans_gmail
    try:                                                            # verifier_piece_jointe
        WebDriverWait(driver, 20).until(lambda d: attachment_present(d, path.name))
    except TimeoutException:
        driver.find_elements(By.XPATH, "//input[@type='file']")[-1].send_keys(str(path))
        WebDriverWait(driver, 20).until(lambda d: attachment_present(d, path.name))

    reply = write_reply(pb, first_name, subject, body, info.get("context"))  # rediger_reponse
    box.click()
    human_type(box, reply)
    time.sleep(2)
    if send:                                                        # envoyer
        box.send_keys(Keys.CONTROL, Keys.ENTER)
        time.sleep(3)
    else:
        wait_draft_saved(driver)
        box.send_keys(Keys.ESCAPE)  # ferme la réponse ; Gmail garde le brouillon
        time.sleep(2)
    return info, reply, None


def clean_preview(text):
    """Aperçu stable d'une rangée Gmail (sans le badge « Nouveau » qui disparaît une fois vu)."""
    return re.sub(r"^(Nouveau|New)\s+", "", " ".join(text.split()))[:90]


def asks_context(text):
    """Le mail pose une question dont la réponse peut être dans ce que l'utilisateur a vu (et il n'est pas sensible)."""
    t = text.lower()
    return (bool(topics_of(t)) or any(w in t for w in AGENDA_WORDS)) and not any(w in t for w in SENSITIVE)


def run_context_reply(driver, row, base, senders):
    """Aucun workflow appris : répond uniquement avec le contexte retrouvé dans screenpipe, sans pièce jointe.
    Toujours en brouillon (pas de geste appris = toujours validé par l'utilisateur)."""
    focus_browser()
    layout_windows(driver)
    pyautogui.moveTo(*screen_center(driver, row), duration=0.6)
    row.click()
    subject, body, first_name = read_open_mail(driver)
    text = f"{subject}\n{body}"
    if any(w in text.lower() for w in SENSITIVE):
        return None
    ctx = find_context(subject, body, first_name)
    sentence = fact_sentence(ctx["facts"])
    if not sentence:
        driver.back()
        return None
    reply = claude_reply_context(first_name, subject, body, ctx["facts"]) or \
        f"Salut {first_name},\n\n{sentence}\n\nBonne journée,\nTable En"
    box = click_reply(driver)
    box.click()
    human_type(box, reply)
    wait_draft_saved(driver)
    box.send_keys(Keys.ESCAPE)  # brouillon
    time.sleep(2)
    known = (first_name or "").lower() in senders
    score = min(70, 30 + 15 * len(ctx["facts"]) + (10 if known else 0))
    reasons = [("+30", "pas de geste appris : réponse construite avec le contexte seul"),
               (f"+{15 * len(ctx['facts'])}", "contexte retrouvé dans screenpipe : "
                + ", ".join(f"{f['topic']} = {f['value']}" for f in ctx["facts"]))]
    reasons.append(("+10", "expéditeur déjà rencontré") if known else ("+0", "expéditeur inconnu"))
    reasons.append(("bloquant", "aucun workflow appris pour ce type de mail : toujours validé par toi"))
    return {**base, "scenario": "contexte", "subject": subject, "sender": first_name, "body": body, "file": None,
            "steps": ["ouvrir_mail", "chercher_contexte", "rediger_reponse"], "reply": reply, "status": "brouillon",
            "error": None, "score": score, "reasons": reasons, "sensitive": False,
            "evidence": {"frames": [], "observations": 0, "memory": None}, "context": ctx}


def claude_reply_context(first_name, subject, body, facts):
    """Variante Claude (optionnelle, ANTHROPIC_API_KEY) pour une réponse fondée uniquement sur le contexte."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    pb = {"exemples_de_reponse": [f"Salut {first_name},\n\n…\n\nBonne journée,\nTable En"],
          "variables": {"fichier": "aucun"}}
    return claude_reply(pb, first_name, subject, body, facts)


def log_entry(entry):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="forcer l'envoi (sinon : selon le mode et la confiance)")
    ap.add_argument("--max", type=int, default=3, help="nombre max de mails traités par exécution")
    ap.add_argument("--dry", action="store_true", help="n'agit pas, affiche seulement les décisions")
    ap.add_argument("--subject", help="rejoue un mail déjà présent dans Gmail (lu ou non), retrouvé par son sujet")
    args = ap.parse_args()

    playbooks = load_playbooks()
    senders = known_senders(playbooks)
    mode = load_mode()
    driver = get_driver()

    done, review = [], []
    # mails déjà signalés « à vérifier » : ils restent non lus dans Gmail, on ne les re-signale pas
    seen = set()
    if LOG.exists():
        for line in LOG.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line).get("status") == "à vérifier":
                seen.add(clean_preview(json.loads(line).get("preview", "")))
    for _ in range(args.max * 3):
        if len(done) >= args.max:
            break
        if args.subject:  # démo : on rejoue un mail de l'historique au lieu d'attendre un nouveau mail
            if done or review:
                break
            driver.get("https://mail.google.com/mail/u/0/#search/" + urllib.parse.quote(f'subject:"{args.subject}"'))
            time.sleep(5)
            candidates = visible(driver, ROW)[:1]
        else:
            candidates = [r for r in unread_rows(driver) if clean_preview(r.text) not in seen]
        if not candidates:
            break
        row = candidates[0]
        preview = clean_preview(row.text)
        seen.add(preview)
        if not preview:  # rangée Gmail en cours de redessin : on la reprendra au prochain passage
            continue
        key, margin = choose_playbook(playbooks, row.text)
        base = {"id": uuid.uuid4().hex[:12], "time": datetime.now().isoformat(timespec="seconds"), "mode": mode}
        if key is None:
            cell = lambda css: " ".join((row.find_elements(By.CSS_SELECTOR, css) or [None])[0].text.split()) \
                if row.find_elements(By.CSS_SELECTOR, css) else ""
            meta = {"sender": cell(".yX"), "subject": cell(".bog"), "body": cell(".y2").lstrip("- ")}
            # pas de geste appris, mais peut-être une question à laquelle screenpipe sait répondre (agenda, prix…)
            if not args.dry and asks_context(preview):
                entry = run_context_reply(driver, row, base, senders)
                if entry:
                    log_entry(entry)
                    done.append(entry)
                    print(f"[agent] {preview}\n        -> réponse par contexte (brouillon, confiance {entry['score']})")
                    continue
            print(f"[agent] À VÉRIFIER (aucun workflow appris ne correspond) : {preview}")
            review.append(preview)
            if not args.dry:
                log_entry({**base, "status": "à vérifier", "preview": preview, "score": 0, **meta,
                           "reasons": [["bloquant", "aucun workflow appris ne correspond à ce mail : je ne réponds pas"]]})
            continue
        pb = playbooks[key]
        print(f"[agent] {preview}\n        -> workflow '{key}' ({pb_file(pb)})")
        if args.dry:
            done.append({"scenario": key, "mail": preview})
            continue

        def decide(subject, body, first_name, path, pb=pb, margin=margin):
            ev = past_evidence(path.name)
            score, reasons, sensitive = confidence(pb, margin, path.exists(),
                                                   (first_name or "").lower() in senders,
                                                   f"{subject}\n{body}", ev)
            ctx = find_context(subject, body, first_name)  # ce que l'utilisateur a vu à ce sujet
            if ctx["facts"]:
                reasons.append(("+0", "contexte retrouvé dans screenpipe : "
                                + ", ".join(f"{f['topic']} = {f['value']}" for f in ctx["facts"])))
            blocked = sensitive or bool(ctx["missing"])
            if ctx["missing"]:
                reasons.append(("bloquant", "on me demande une info que je n'ai pas retrouvée ("
                                + ", ".join(ctx["missing"]) + ") : à toi de compléter"))
            send = args.send or (mode == "auto" and score >= AUTO_THRESHOLD and not blocked)
            return send, {"score": score, "reasons": reasons, "sensitive": sensitive, "evidence": ev, "context": ctx}

        info, reply, error = run_playbook(driver, pb, row, decide)
        status = "erreur" if error else ("envoyé" if info["send"] else "brouillon")
        print(f"        -> {status} (confiance {info['score']}){' : ' + error if error else ''}")
        entry = {**base, "scenario": key, "subject": info["subject"], "sender": info["sender"],
                 "body": info["body"], "file": pb_file(pb),
                 "file_path": str(Path(pb["variables"]["dossier"]) / pb_file(pb)),
                 "steps": [s["action"] for s in pb["etapes"]], "reply": reply, "status": status, "error": error,
                 "score": info["score"], "reasons": info["reasons"], "sensitive": info["sensitive"],
                 "evidence": info["evidence"], "context": info.get("context")}
        log_entry(entry)
        done.append(entry)

    summary = (f"{len(done)} mail(s) traité(s)" + (" (simulation)" if args.dry else "") +
               (f", {len(review)} à vérifier à la main" if review else ""))
    print(f"\n[agent] {summary}")
    if done or review:
        details = "\n".join(f"- **{d.get('subject') or d.get('mail')}** → `{d.get('file', d['scenario'])}`"
                            f" ({d.get('status', 'simulation')})" for d in done)
        details += "".join(f"\n- à vérifier : {r}" for r in review)
        notify("Agent mail : " + summary, details)


def pb_file(pb):
    return pb["variables"]["fichier"]


if __name__ == "__main__":
    main()
