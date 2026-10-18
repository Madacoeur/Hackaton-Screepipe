"""Validation humaine depuis l'interface : rouvre le brouillon Gmail préparé par l'agent,
remplace éventuellement le texte, puis l'envoie (ou le rejette).

    python agent/approve_draft.py <id>                     # envoie le brouillon tel quel
    python agent/approve_draft.py <id> --text-file f.txt   # remplace le texte puis envoie
    python agent/approve_draft.py <id> --reject            # marque rejeté, n'envoie rien
"""
import argparse
import json
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "training_bot"))

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.common.keys import Keys  # noqa: E402

from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402

from config import FILES_DIR  # noqa: E402
from reply_bot import (ROW, attachment_present, click_reply, focus_browser, get_driver, human_type,  # noqa: E402
                       layout_windows, visible, wait_visible)

LOG = ROOT / "agent" / "agent_log.jsonl"
STATUS = ROOT / "agent" / "status.json"
DRAFTS_URL = "https://mail.google.com/mail/u/0/#drafts"


def find_entry(entry_id):
    """Par id ; les premières lignes du journal (sans id) sont désignées « L<numéro de ligne> »."""
    for i, line in enumerate(LOG.read_text(encoding="utf-8").split("\n")):
        if line.strip():
            e = json.loads(line)
            if e.get("id", f"L{i}") == entry_id:
                return e
    sys.exit(f"entrée {entry_id} introuvable")


def set_status(entry_id, status, **extra):
    data = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    data[entry_id] = {"status": status, "time": datetime.now().isoformat(timespec="seconds"), **extra}
    STATUS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def send_draft(entry, new_text=None):
    driver = get_driver()
    focus_browser()
    layout_windows(driver)
    driver.get(DRAFTS_URL)
    time.sleep(6)
    subject = entry["subject"]
    rows = [r for r in visible(driver, ROW) if subject in r.text]
    if rows:
        rows[0].click()
        box = wait_visible(driver, "//div[@contenteditable='true' and @role='textbox']")[-1]
    else:
        # brouillon perdu (fermé avant d'être enregistré, ou déjà parti) : on rouvre le fil et on réécrit
        driver.get("https://mail.google.com/mail/u/0/#search/" + urllib.parse.quote(f'subject:"{subject}"'))
        time.sleep(5)
        threads = visible(driver, ROW)
        if not threads:
            raise RuntimeError(f"mail « {subject} » introuvable dans Gmail")
        threads[0].click()
        box = click_reply(driver)
        if new_text is None:
            new_text = entry.get("final_text") or entry.get("reply") or ""
        if entry.get("file") and not attachment_present(driver, entry["file"]):
            driver.find_elements(By.XPATH, "//input[@type='file']")[-1].send_keys(entry.get("file_path")
                                                                             or str(FILES_DIR / entry["file"]))
            WebDriverWait(driver, 20).until(lambda d: attachment_present(d, entry["file"]))
    if new_text is not None:
        box.click()
        box.send_keys(Keys.CONTROL, "a")
        box.send_keys(Keys.DELETE)
        human_type(box, new_text)
    if entry.get("file") and not driver.find_elements(By.XPATH, f"//*[contains(normalize-space(), '{entry['file']}') and not(*)]"):
        raise RuntimeError(f"pièce jointe {entry['file']} absente du brouillon, envoi annulé")
    box.send_keys(Keys.CONTROL, Keys.ENTER)
    time.sleep(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--text-file")
    ap.add_argument("--reject", action="store_true")
    args = ap.parse_args()

    entry = find_entry(args.id)
    if args.reject:
        set_status(args.id, "rejeté")
        print("rejeté")
        return
    text = Path(args.text_file).read_text(encoding="utf-8") if args.text_file else None
    try:
        send_draft(entry, text)
    except Exception as e:
        set_status(args.id, "erreur", error=str(e))
        print(f"erreur : {e}")
        sys.exit(1)
    set_status(args.id, "envoyé", edited=text is not None, final_text=text or entry.get("reply"))
    print("envoyé")


if __name__ == "__main__":
    main()
