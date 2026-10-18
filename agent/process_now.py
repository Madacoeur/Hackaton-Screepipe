"""« Traiter maintenant » : prépare tout ce dont l'agent a besoin, puis traite les mails non lus.

1. screenpipe tourne (démarre l'app sinon) ;
2. le Brave de l'agent est ouvert sur Gmail, lancé hors de tout job screenpipe pour qu'il survive au passage ;
3. run_agent.py traite au plus 3 mails ;
4. le résultat est écrit dans agent/last_run.json (lu par l'interface).

Un verrou empêche deux passages en même temps (clic dans l'interface + passage de la pipe) : ils se
disputeraient la souris. Appelé par l'interface, par agent/service.py et par la pipe mail-autopilot.

    python agent/process_now.py [--max 3]
"""
import argparse
import ctypes
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "agent" / "run.lock"
LAST = ROOT / "agent" / "last_run.json"
RUN_LOG = ROOT / "logs" / "process_now.log"  # sortie complète du dernier passage
SCREENPIPE_APP = Path(os.path.expandvars(r"%LOCALAPPDATA%\screenpipe\screenpipe-app.exe"))
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
sys.path.insert(0, str(ROOT / "training_bot"))


def alive(pid):
    h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
    ctypes.windll.kernel32.CloseHandle(h)
    return code.value == 259  # STILL_ACTIVE


def take_lock():
    try:
        pid = int(LOCK.read_text())
        if pid != os.getpid() and alive(pid):
            return False
    except (OSError, ValueError):
        pass
    LOCK.write_text(str(os.getpid()))
    return True


def screenpipe_ok():
    try:
        with urllib.request.urlopen("http://localhost:3030/health", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def ensure_screenpipe():
    if screenpipe_ok():
        return True
    if SCREENPIPE_APP.exists():
        subprocess.Popen([str(SCREENPIPE_APP)], creationflags=0x00000008 | NO_WINDOW)
        for _ in range(60):
            if screenpipe_ok():
                return True
            time.sleep(1)
    return False


def ensure_gmail():
    """Ouvre (ou retrouve) le Brave de l'agent sur la boîte de réception. Renvoie un message d'erreur ou None."""
    from reply_bot import EMPTY_LIST, INBOX_URL, ROW, focus_browser, get_driver, visible
    driver = get_driver()
    if driver.current_url != INBOX_URL:  # autre page, ou un mail resté ouvert par un passage précédent
        driver.get(INBOX_URL)
    for i in range(60):
        if "accounts.google.com" in driver.current_url:
            return "Gmail is not signed in: run “python training_bot/reply_bot.py --login” once"
        if visible(driver, f"{ROW} | {EMPTY_LIST}"):  # boîte chargée, même vide
            return None
        if i == 10:  # Brave caché derrière d'autres fenêtres : la page est en veille, on le ramène devant
            focus_browser()
        time.sleep(1)
    return "the Gmail inbox does not load in Brave"


def english_summary(lines):
    """Résumé de run_agent (« 2 mail(s) traité(s), 1 à vérifier à la main ») traduit pour l'interface."""
    last = next((l for l in reversed(lines) if "traité" in l), "")
    done = int(re.search(r"(\d+) mail", last).group(1)) if re.search(r"(\d+) mail", last) else 0
    review = int(re.search(r"(\d+) à vérifier", last).group(1)) if re.search(r"(\d+) à vérifier", last) else 0
    if not done and not review:
        return "No new mail to process"
    parts = [f"{done} mail{'s' if done > 1 else ''} handled"] if done else []
    if review:
        parts.append(f"{review} left for you to check")
    return ", ".join(parts)


def finish(ok, message, lines=()):
    LAST.write_text(json.dumps({"time": datetime.now().isoformat(timespec="seconds"), "ok": ok,
                                "message": message, "lines": list(lines)}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    print(f"[process] {message}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=3)
    args = ap.parse_args()

    if not take_lock():
        print("[process] a run is already in progress")
        return 2
    try:
        if not ensure_screenpipe():
            return finish(False, "screenpipe is not responding: open the screenpipe app")
        error = ensure_gmail()
        if error:
            return finish(False, error)
        python = Path(sys.executable).with_name("python.exe")
        r = subprocess.run([str(python), str(ROOT / "agent" / "run_agent.py"), "--max", str(args.max)], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"}, creationflags=NO_WINDOW)
        out = (r.stdout + r.stderr).splitlines()
        print("\n".join(out))
        RUN_LOG.parent.mkdir(exist_ok=True)
        RUN_LOG.write_text(f"{datetime.now():%Y-%m-%d %H:%M:%S}\n" + "\n".join(out), encoding="utf-8")
        lines = [l.strip() for l in out if l.strip().startswith(("[agent]", "->"))]
        if r.returncode != 0:
            # dernière ligne d'exception Python (« XxxError: … »), pas la pile native de chromedriver
            error = next((l for l in reversed(out) if l and not l[0].isspace() and ("Error" in l or "Exception" in l)),
                         f"code {r.returncode}")
            return finish(False, "the agent crashed: " + error[:300], lines + [f"détail : {RUN_LOG}"])
        return finish(True, english_summary(lines), lines)
    except Exception as e:
        return finish(False, f"{type(e).__name__} : {e}")
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
