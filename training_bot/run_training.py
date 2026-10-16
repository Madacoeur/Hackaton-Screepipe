"""Boucle d'entraînement : demande SMTP -> attente du mail -> traitement par le bot.

    python run_training.py -n 10              # 10 cycles, scénarios au hasard
    python run_training.py -n 6 --each        # chaque scénario une fois
"""
import argparse
import random
import time

from reply_bot import get_driver, process_latest, wait_for_new_mail
from scenarios import SCENARIOS
from send_requests import send_request


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=5, help="nombre de cycles")
    ap.add_argument("--each", action="store_true", help="passer chaque scénario dans l'ordre")
    ap.add_argument("--pause", type=int, nargs=2, default=[30, 90], help="pause min/max entre cycles (s)")
    ap.add_argument("--no-send", action="store_true")
    args = ap.parse_args()

    keys = list(SCENARIOS) if args.each else [None] * args.n
    driver = get_driver()
    for i, key in enumerate(keys[: args.n], 1):
        print(f"\n=== cycle {i}/{args.n} ===")
        _, subject = send_request(key)
        wait_for_new_mail(driver, subject)
        process_latest(driver, send=not args.no_send)
        if i < args.n:
            pause = random.randint(*args.pause)
            print(f"[run] pause {pause}s")
            time.sleep(pause)


if __name__ == "__main__":
    main()
