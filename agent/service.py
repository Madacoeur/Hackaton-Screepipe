"""Service de l'agent : relance run_agent.py à intervalle régulier, en arrière-plan et sans console.
Remplace la pipe screenpipe « mail-autopilot » (qui ouvrait une fenêtre de terminal à chaque passage).

Réglage dans agent/config.json : {"mode": "verification", "every_minutes": 15}  (0 = pas d'automatique)
Lancé par Deja-vu.pyw ; journal dans logs/agent_service.log.
"""
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "agent" / "config.json"
LOG = ROOT / "logs" / "agent_service.log"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def every_minutes():
    try:
        return float(json.loads(CONFIG.read_text(encoding="utf-8")).get("every_minutes", 15))
    except Exception:
        return 15.0


def log(msg):
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")


def run_once():
    python = Path(sys.executable).with_name("python.exe")  # même interpréteur que pythonw, mais sans console grâce au flag
    r = subprocess.run([str(python), str(ROOT / "agent" / "run_agent.py"), "--max", "3"], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}, creationflags=NO_WINDOW)
    lines = [l for l in (r.stdout + r.stderr).splitlines() if "[agent]" in l or "Error" in l]
    log(" | ".join(lines[-4:]) or f"terminé (code {r.returncode})")


def main():
    log("service démarré")
    while True:
        minutes = every_minutes()
        if minutes > 0:
            try:
                run_once()
            except Exception as e:  # le service ne s'arrête jamais sur une erreur de passage
                log(f"erreur : {e}")
        time.sleep(max(60.0, minutes * 60) if minutes > 0 else 60.0)


if __name__ == "__main__":
    main()
