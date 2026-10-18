"""Lanceur Déjà-vu : double-clic, sans aucune fenêtre de terminal.

- vérifie que screenpipe tourne (le démarre sinon) ;
- démarre l'interface (http://localhost:3000) et le service de l'agent, en arrière-plan ;
- ouvre l'interface dans le navigateur.

Relancer ce fichier ne crée pas de doublon. Pour tout arrêter : « python Deja-vu.pyw stop ».
Journaux : dossier logs/.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "logs"
PIDS = LOGS / "pids.json"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SCREENPIPE_APP = Path(os.path.expandvars(r"%LOCALAPPDATA%\screenpipe\screenpipe-app.exe"))
UI_URL = "http://localhost:3000"


def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def screenpipe_ok():
    try:
        with urllib.request.urlopen("http://localhost:3030/health", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def start(name, args, log_name):
    LOGS.mkdir(exist_ok=True)
    out = open(LOGS / log_name, "a", encoding="utf-8")
    p = subprocess.Popen(args, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, creationflags=NO_WINDOW,
                         env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    pids = json.loads(PIDS.read_text()) if PIDS.exists() else {}
    pids[name] = p.pid
    PIDS.write_text(json.dumps(pids))
    return p


def alive(pid):
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, creationflags=NO_WINDOW).stdout
    return str(pid) in out


def stop():
    pids = json.loads(PIDS.read_text()) if PIDS.exists() else {}
    for pid in pids.values():
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, creationflags=NO_WINDOW)
    PIDS.unlink(missing_ok=True)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        stop()
        return
    python = Path(sys.executable).with_name("python.exe")
    pids = json.loads(PIDS.read_text()) if PIDS.exists() else {}

    if not screenpipe_ok() and SCREENPIPE_APP.exists():
        subprocess.Popen([str(SCREENPIPE_APP)], creationflags=NO_WINDOW)
        for _ in range(60):
            if screenpipe_ok():
                break
            time.sleep(1)

    if not port_open(3000):
        npm = "npm.cmd" if os.name == "nt" else "npm"
        start("ui", [npm, "--prefix", "ui", "run", "dev"], "ui.log")
    if not (pids.get("agent") and alive(pids["agent"])):
        start("agent", [str(python), str(ROOT / "agent" / "service.py")], "agent.log")

    for _ in range(90):
        if port_open(3000):
            break
        time.sleep(1)
    webbrowser.open(UI_URL)


if __name__ == "__main__":
    main()
