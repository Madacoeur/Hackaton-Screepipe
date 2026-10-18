"""Boucle d'entraînement : demande SMTP -> attente du mail -> traitement par le bot.

    python run_training.py -n 10              # 10 cycles, scénarios au hasard
    python run_training.py -n 6 --each        # chaque scénario une fois
    python run_training.py --minutes 120      # tourne 2 h (scénarios en rotation)
"""
import argparse
import random
import time
import traceback

from pyautogui import FailSafeException

from reply_bot import get_driver, process_latest, wait_for_new_mail
from scenarios import SCENARIOS
from send_requests import send_request


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=5, help="nombre de cycles")
    ap.add_argument("--minutes", type=float, help="durée de la session (prioritaire sur -n)")
    ap.add_argument("--each", action="store_true", help="passer chaque scénario dans l'ordre")
    ap.add_argument("--pause", type=int, nargs=2, default=[30, 90], help="pause min/max entre cycles (s)")
    ap.add_argument("--no-send", action="store_true")
    args = ap.parse_args()

    end = time.time() + args.minutes * 60 if args.minutes else None
    keys = list(SCENARIOS)
    driver = get_driver()
    i, ok = 0, 0
    while (time.time() < end) if end else (i < args.n):
        i += 1
        # rotation : chaque scénario revient régulièrement, ordre mélangé à chaque tour
        if (i - 1) % len(keys) == 0:
            random.shuffle(keys)
        key = keys[(i - 1) % len(keys)] if (args.each or end) else None
        print(f"\n=== cycle {i} ({time.strftime('%H:%M:%S')}) ===", flush=True)
        try:
            _, subject = send_request(key)
            wait_for_new_mail(driver, subject)
            if process_latest(driver, send=not args.no_send):
                ok += 1
        except FailSafeException:
            print("[run] arrêt d'urgence (souris dans le coin)")
            break
        except Exception:
            traceback.print_exc()
            print("[run] cycle raté, on continue")
            try:
                driver = get_driver()
            except Exception:
                traceback.print_exc()
        pause = random.randint(*args.pause)
        print(f"[run] {ok}/{i} cycles réussis, pause {pause}s", flush=True)
        time.sleep(pause)


if __name__ == "__main__":
    main()
