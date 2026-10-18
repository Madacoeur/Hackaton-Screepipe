"""Entraînement « contexte » : affiche à l'écran les infos qu'un freelance voit dans sa journée
(notes d'appel, agenda, devis, planning) pour que screenpipe les mémorise. L'agent les retrouvera
ensuite pour répondre avec ce que tu sais (« on avait dit quoi pour le prix ? »).

    python context_bot.py --minutes 30
"""
import argparse
import json
import random
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pyautogui

from config import FILES_DIR, ROOT
from reply_bot import focus_browser, get_driver, layout_windows

sys.path.insert(0, str(ROOT.parent / "agent"))
from screenpipe_client import BASE, token  # noqa: E402

CONTEXT = ROOT / "context"
DOCS = [
    CONTEXT / "notes-appel-karim.html",
    CONTEXT / "notes-appel-lea.html",
    CONTEXT / "agenda-semaine.html",
    FILES_DIR / "devis-studio-nova.pdf",
    FILES_DIR / "planning-projet-novembre.pdf",
    FILES_DIR / "facture-octobre-2026.pdf",
]
LOG = ROOT / "context_log.jsonl"


def star(minutes):
    """Étoile la session dans screenpipe : ces moments sont à apprendre."""
    import urllib.error
    import urllib.request
    now = datetime.now().astimezone()
    body = {"id": str(uuid.uuid4()), "start": now.isoformat(), "end": (now + timedelta(minutes=minutes + 2)).isoformat(),
            "hd_requested": False, "revision": 0}
    req = urllib.request.Request(f"{BASE}/starred-sessions", data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json",
                                          "X-Screenpipe-Client": "api", "X-Screenpipe-Agent": "claude"})
    try:
        urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        if e.code != 409:  # 409 : une session étoilée couvre déjà ce moment, elle suffit
            raise
        print("[contexte] session déjà étoilée", flush=True)


def show(driver, doc, dwell):
    driver.switch_to.new_window("tab")
    driver.get(doc.as_uri())
    focus_browser()
    time.sleep(3)
    w, h = pyautogui.size()
    pyautogui.moveTo(w // 3, h // 2, duration=0.5)
    end = time.time() + dwell
    while time.time() < end:  # lecture : petits défilements, comme quelqu'un qui relit
        pyautogui.scroll(random.choice([-3, -2, 2]))
        time.sleep(random.uniform(4, 8))
    driver.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=30)
    args = ap.parse_args()

    driver = get_driver()
    gmail = driver.current_window_handle
    focus_browser()
    layout_windows(driver)
    star(args.minutes)
    print(f"[contexte] session étoilée de {args.minutes:.0f} min", flush=True)

    end = time.time() + args.minutes * 60
    i = 0
    while time.time() < end:
        doc = DOCS[i % len(DOCS)]
        i += 1
        dwell = random.randint(45, 75)
        print(f"[contexte] {datetime.now():%H:%M:%S} affiche {doc.name} ({dwell}s)", flush=True)
        try:
            show(driver, doc, dwell)
        except Exception as e:
            print(f"[contexte] raté : {e}", flush=True)
        finally:
            driver.switch_to.window(gmail)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": datetime.now().isoformat(timespec="seconds"), "doc": doc.name}) + "\n")
        time.sleep(random.randint(5, 15))
    print("[contexte] terminé", flush=True)


if __name__ == "__main__":
    main()
