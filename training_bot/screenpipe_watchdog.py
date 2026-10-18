"""Relance screenpipe s'il tombe ou si sa capture d'écran se fige, pendant l'entraînement.

    python screenpipe_watchdog.py
"""
import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime

APP = os.path.expandvars(r"%LOCALAPPDATA%\screenpipe\screenpipe-app.exe")
HEALTH = "http://localhost:3030/health"


def log(msg):
    print(f"[watchdog {datetime.now():%H:%M:%S}] {msg}", flush=True)


def health():
    try:
        with urllib.request.urlopen(HEALTH, timeout=5) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:  # 503 = "degraded", le corps reste exploitable
        return json.load(e)
    except Exception:
        return None


def running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq screenpipe-app.exe"], capture_output=True, text=True).stdout
    return "screenpipe-app.exe" in out


def restart():
    subprocess.run(["taskkill", "/F", "/IM", "screenpipe-app.exe"], capture_output=True)
    time.sleep(3)
    subprocess.Popen([APP])
    time.sleep(30)  # le temps de démarrer


def main():
    log("surveillance de screenpipe")
    stalled_since = None
    no_answer = 0
    while True:
        h = health()
        no_answer = no_answer + 1 if h is None else 0
        if not running():
            log("screenpipe arrêté -> relance")
            restart()
            stalled_since, no_answer = None, 0
        elif no_answer >= 6:  # occupé != mort : on attend ~1 min 30 sans réponse avant de tuer
            log("screenpipe ne répond plus depuis ~90s -> relance")
            restart()
            stalled_since, no_answer = None, 0
        elif h is None:
            pass
        elif h.get("frame_status") != "ok":
            stalled_since = stalled_since or time.time()
            if time.time() - stalled_since > 60:
                log(f"capture figée ({h.get('vision_reason')}) depuis 60s -> relance")
                restart()
                stalled_since = None
        else:
            stalled_since = None
        time.sleep(15)


if __name__ == "__main__":
    main()
