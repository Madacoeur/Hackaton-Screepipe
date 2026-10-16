"""Bot qui traite "à la main" le dernier mail reçu dans Gmail, sous les yeux de screenpipe :
ouvre le mail -> Répondre -> ouvre l'Explorateur sur le bon fichier -> drag & drop dans
Gmail avec la souris -> tape une réponse -> envoie.

    python reply_bot.py --login      # 1re fois : ouvre le navigateur, tu te connectes à la main
    python reply_bot.py              # traite le dernier mail de la boîte de réception
    python reply_bot.py --no-send    # tout sauf l'envoi
"""
import argparse
import ctypes
import json
import random
import re
import socket
import subprocess
import time
from datetime import datetime

import pyautogui  # importé en premier : rend le process DPI-aware (coordonnées physiques)
from pywinauto import Desktop
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import BROWSER_PATH, DEBUG_PORT, FILES_DIR, LOG_FILE, PROFILE_DIR, SENDER_EMAIL, SENDER_NAME, SIGNATURE
from phrases import build_reply
from scenarios import SCENARIOS, match_scenario

pyautogui.FAILSAFE = True  # souris dans le coin haut-gauche = arrêt d'urgence
INBOX_URL = "https://mail.google.com/mail/u/0/#inbox"


# ---------------------------------------------------------------- navigateur

def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def get_driver():
    """Lance Brave en mode normal (pas "automatisé", Google accepte la connexion) puis s'y attache."""
    if not port_open(DEBUG_PORT):
        subprocess.Popen([
            BROWSER_PATH,
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={PROFILE_DIR}",
            "--no-first-run",
            "--no-default-browser-check",
            INBOX_URL,
        ])
        for _ in range(40):
            if port_open(DEBUG_PORT):
                break
            time.sleep(0.5)
    options = webdriver.ChromeOptions()
    options.binary_location = BROWSER_PATH
    options.debugger_address = f"127.0.0.1:{DEBUG_PORT}"
    driver = webdriver.Chrome(options=options)
    for handle in driver.window_handles:  # se placer sur l'onglet Gmail s'il existe
        driver.switch_to.window(handle)
        if "mail.google.com" in driver.current_url:
            break
    return driver


def layout_windows(driver):
    """Navigateur sur les 2/3 gauches de l'écran, l'Explorateur ira sur le tiers droit."""
    dpr = driver.execute_script("return window.devicePixelRatio") or 1
    sw, sh = pyautogui.size()
    driver.set_window_rect(0, 0, int(sw * 2 / 3 / dpr), int((sh - 48) / dpr))


def visible(driver, xpath):
    return [e for e in driver.find_elements(By.XPATH, xpath) if e.is_displayed()]


def wait_visible(driver, xpath, timeout=20):
    return WebDriverWait(driver, timeout).until(lambda d: visible(d, xpath) or False)


def viewport_rect(driver):
    """Rectangle écran de la zone de page, lu via Windows : Brave fausse window.screenX/outerHeight
    côté JS (anti-fingerprinting), on ne peut donc pas s'y fier."""
    title = re.escape(driver.title)
    for win in Desktop(backend="win32").windows(class_name="Chrome_WidgetWin_1", title_re=f"^{title}.*"):
        for child in win.descendants(class_name="Chrome_RenderWidgetHostHWND"):
            if child.is_visible():
                return child.rectangle()
    raise RuntimeError("zone de page Brave introuvable")


def screen_center(driver, el):
    """Coordonnées écran (pixels physiques) du centre d'un élément de la page."""
    vp = viewport_rect(driver)
    scale = vp.width() / driver.execute_script("return document.documentElement.clientWidth")
    r = el.rect
    return int(vp.left + (r["x"] + r["width"] / 2) * scale), int(vp.top + (r["y"] + r["height"] / 2) * scale)


# ---------------------------------------------------------------- Gmail

ROW = "//tr[contains(@class,'zA')]"


def open_inbox(driver):
    if not driver.current_url.startswith(INBOX_URL):
        driver.get(INBOX_URL)
    wait_visible(driver, ROW, 60)


def wait_for_new_mail(driver, subject=None, timeout=180):
    """Recharge la boîte jusqu'à ce que le 1er mail soit non lu (et ait le bon sujet)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        open_inbox(driver)
        row = visible(driver, ROW)[0]
        unread = "zE" in row.get_attribute("class")
        if unread and (subject is None or subject.split(":")[-1].strip() in row.text):
            return row
        time.sleep(8)
        driver.refresh()
    raise TimeoutException(f"mail '{subject}' pas arrivé après {timeout}s")


def pick_row(driver):
    rows = visible(driver, ROW)
    if SENDER_EMAIL:
        for row in rows:
            if row.find_elements(By.XPATH, f".//span[@email='{SENDER_EMAIL}']"):
                return row
    return rows[0]


def read_open_mail(driver):
    wait_visible(driver, "//h2[contains(@class,'hP')]")
    time.sleep(1.5)
    subject = visible(driver, "//h2[contains(@class,'hP')]")[0].text
    bodies = visible(driver, "//div[contains(@class,'a3s')]")
    body = bodies[-1].text if bodies else ""
    senders = visible(driver, "//span[contains(@class,'gD')]")
    name = (senders[-1].get_attribute("name") or senders[-1].text) if senders else ""
    if name.lower() in ("", "moi", "me"):  # mail envoyé depuis le compte démo lui-même
        name = SENDER_NAME
    return subject, body, name.split()[0]


def click_reply(driver):
    xp = ("//span[@role='link' and (normalize-space()='Répondre' or normalize-space()='Reply')]"
          " | //*[@role='button' and (@aria-label='Répondre' or @aria-label='Reply')]")
    btn = wait_visible(driver, xp)[-1]
    pyautogui.moveTo(*screen_center(driver, btn), duration=0.6)
    btn.click()
    return wait_visible(driver, "//div[@contenteditable='true' and @role='textbox']")[-1]


def human_type(el, text):
    for ch in text:
        el.send_keys(Keys.ENTER if ch == "\n" else ch)
        time.sleep(random.uniform(0.02, 0.09))


# ---------------------------------------------------------------- Explorateur + drag & drop

def open_explorer_on(path):
    criteria = dict(title_re=f".*{re.escape(path.parent.name)}.*", class_name="CabinetWClass")
    for old in Desktop(backend="uia").windows(**criteria):  # pas d'accumulation de fenêtres
        old.close()
    subprocess.Popen(["explorer", f"/select,{path}"])
    win = Desktop(backend="uia").window(**criteria, found_index=0)
    win.wait("visible", timeout=15)
    sw, sh = pyautogui.size()
    hwnd = win.wrapper_object().handle
    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    ctypes.windll.user32.MoveWindow(hwnd, int(sw * 2 / 3), 0, int(sw / 3), sh - 48, True)
    win.set_focus()
    time.sleep(1.5)
    # le nom affiché peut être sans extension selon les réglages de l'Explorateur
    names = f"^({re.escape(path.name)}|{re.escape(path.stem)})$"
    item = win.child_window(title_re=names, control_type="ListItem", found_index=0)
    item.wait("visible", timeout=10)
    return win, item


def drag_file_to(item, target):
    r = item.rectangle()
    sx, sy = r.left + 40, (r.top + r.bottom) // 2  # sur l'icône / le nom, pas les colonnes
    pyautogui.moveTo(sx, sy, duration=0.7)
    pyautogui.mouseDown()
    for i in range(1, 6):  # petit mouvement pour déclencher le drag OLE
        pyautogui.moveTo(sx - 4 * i, sy + 2 * i, duration=0.05)
    pyautogui.moveTo(*target, duration=1.4, tween=pyautogui.easeInOutQuad)
    time.sleep(0.8)  # laisser Gmail afficher "Déposer les fichiers ici"
    pyautogui.moveRel(5, 5, duration=0.2)
    pyautogui.mouseUp()


def attachment_present(driver, filename):
    return bool(driver.find_elements(By.XPATH, f"//*[contains(normalize-space(), '{filename}') and not(*)]"))


# ---------------------------------------------------------------- main

def process_latest(driver, send=True):
    layout_windows(driver)
    open_inbox(driver)
    row = pick_row(driver)
    pyautogui.moveTo(*screen_center(driver, row), duration=0.8)
    row.click()

    subject, body, first_name = read_open_mail(driver)
    key = match_scenario(subject + " " + body)
    if key is None:
        print(f"[bot] aucun fichier ne correspond à '{subject}', on ne répond pas")
        return None
    scenario = SCENARIOS[key]
    path = FILES_DIR / scenario["file"]
    print(f"[bot] '{subject}' -> {path.name}")

    box = click_reply(driver)
    time.sleep(1)

    _, item = open_explorer_on(path)
    drag_file_to(item, screen_center(driver, box))
    try:
        WebDriverWait(driver, 20).until(lambda d: attachment_present(d, path.name))
        print("[bot] pièce jointe ajoutée par drag & drop")
    except TimeoutException:
        print("[bot] drag & drop raté, ajout via le champ fichier de Gmail")
        driver.find_elements(By.XPATH, "//input[@type='file']")[-1].send_keys(str(path))
        WebDriverWait(driver, 20).until(lambda d: attachment_present(d, path.name))

    reply = build_reply(first_name or "", scenario["label"], SIGNATURE)
    pyautogui.moveTo(*screen_center(driver, box), duration=0.5)
    box.click()
    human_type(box, reply)
    time.sleep(2)  # fin d'upload de la PJ

    if send:
        box.send_keys(Keys.CONTROL, Keys.ENTER)
        time.sleep(3)
        print("[bot] réponse envoyée")

    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "scenario": key,
        "subject": subject,
        "file": str(path),
        "reply": reply,
        "sent": send,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", action="store_true", help="ouvrir le navigateur pour se connecter à la main")
    ap.add_argument("--no-send", action="store_true")
    args = ap.parse_args()

    driver = get_driver()
    if args.login:
        driver.get(INBOX_URL)
        input("Connecte-toi au compte démo dans la fenêtre Brave, puis appuie sur Entrée ici...")
        return
    process_latest(driver, send=not args.no_send)


if __name__ == "__main__":
    main()
