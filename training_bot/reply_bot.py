"""Bot qui traite "à la main" le dernier mail reçu dans Gmail, sous les yeux de screenpipe :
ouvre le mail -> Répondre -> ouvre l'Explorateur sur le bon fichier -> drag & drop dans
Gmail avec la souris -> tape une réponse -> envoie.

    python reply_bot.py --login      # 1re fois : ouvre le navigateur, tu te connectes à la main
    python reply_bot.py              # traite le dernier mail de la boîte de réception
    python reply_bot.py --no-send    # tout sauf l'envoi
"""
import argparse
import ctypes
import ctypes.wintypes
import json
import random
import re
import socket
import subprocess
import time
from datetime import datetime

import pyautogui  # importé en premier : rend le process DPI-aware (coordonnées physiques)
from pywinauto import Desktop
from pywinauto.win32structures import RECT
from selenium import webdriver
from selenium.common.exceptions import (ElementClickInterceptedException, StaleElementReferenceException,
                                        TimeoutException)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import (BROWSER_PATH, DEBUG_PORT, DEMO_EMAIL, FILES_DIR, LOG_FILE, PROFILE_DIR, SENDER_EMAIL, SENDER_NAME,
                    SIGNATURE)
from phrases import build_reply
from scenarios import SCENARIOS, match_scenario

pyautogui.FAILSAFE = True  # souris dans le coin haut-gauche = arrêt d'urgence
INBOX_URL = "https://mail.google.com/mail/u/0/#inbox"


# ---------------------------------------------------------------- navigateur

def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW


def launch_brave():
    """Démarre le Brave de l'agent via WMI : le processus n'appartient ni à ce script ni au job d'une
    pipe screenpipe, qui tue tous ses processus enfants à la fin du passage (Brave « crashait »)."""
    args = [BROWSER_PATH, f"--remote-debugging-port={DEBUG_PORT}", f"--user-data-dir={PROFILE_DIR}",
            "--no-first-run", "--no-default-browser-check",
            # Gmail doit continuer à se charger même quand Brave est caché derrière d'autres fenêtres
            "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding",
            "--disable-background-timer-throttling", INBOX_URL]
    cmd = subprocess.list2cmdline(args).replace("'", "''")
    ps = f"(Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{{CommandLine='{cmd}'}}).ReturnValue"
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                         creationflags=NO_WINDOW)
    if out.stdout.strip() != "0":  # WMI indisponible : lancement détaché classique
        subprocess.Popen(args, creationflags=0x00000008 | 0x01000000)  # DETACHED_PROCESS | BREAKAWAY_FROM_JOB


def debug_brave_pid():
    """PID du Brave de l'agent : celui qui écoute sur le port de debug (pas le Brave perso)."""
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, encoding="oem",
                         errors="replace", creationflags=NO_WINDOW).stdout
    for line in out.splitlines():
        parts = line.split()
        # socket en écoute = adresse distante 0.0.0.0:0 (indépendant de la langue de Windows)
        if len(parts) >= 5 and parts[1].endswith(f":{DEBUG_PORT}") and parts[2] in ("0.0.0.0:0", "[::]:0"):
            return int(parts[4])
    return None


def get_driver():
    """Lance Brave en mode normal (pas "automatisé", Google accepte la connexion) puis s'y attache."""
    if not port_open(DEBUG_PORT):
        launch_brave()
        for _ in range(40):
            if port_open(DEBUG_PORT):
                break
            time.sleep(0.5)
        time.sleep(2)  # laisse la fenêtre apparaître
    options = webdriver.ChromeOptions()
    options.binary_location = BROWSER_PATH
    options.debugger_address = f"127.0.0.1:{DEBUG_PORT}"
    driver = webdriver.Chrome(options=options)
    # un seul onglet Gmail, au premier plan : après une restauration de session Brave en rouvre parfois
    # plusieurs, et un onglet en arrière-plan n'affiche pas la liste des mails
    gmail = []
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if "mail.google.com" in driver.current_url:
            gmail.append((driver.execute_script("return document.visibilityState") != "visible", handle))
    if gmail:
        gmail.sort()
        for _, handle in gmail[1:]:
            driver.switch_to.window(handle)
            driver.close()
        driver.switch_to.window(gmail[0][1])
        driver.execute_cdp_cmd("Page.bringToFront", {})
    return driver


def layout_windows(driver):
    """Navigateur sur les 2/3 gauches de l'écran, l'Explorateur ira sur le tiers droit."""
    dpr = driver.execute_script("return window.devicePixelRatio") or 1
    sw, sh = pyautogui.size()
    driver.set_window_rect(0, 0, int(sw * 2 / 3 / dpr), int((sh - 48) / dpr))


def visible(driver, xpath):
    out = []
    for e in driver.find_elements(By.XPATH, xpath):
        try:
            if e.is_displayed():
                out.append(e)
        except StaleElementReferenceException:  # Gmail a redessiné l'élément entre-temps
            pass
    return out


def wait_visible(driver, xpath, timeout=20):
    return WebDriverWait(driver, timeout).until(lambda d: visible(d, xpath) or False)


def brave_window():
    """Fenêtre du Brave de l'agent. Filtrée par PID : un Brave perso ouvert sur Gmail ne doit pas être pris."""
    pid = debug_brave_pid()
    wins = [w for w in Desktop(backend="win32").windows(class_name="Chrome_WidgetWin_1", title_re=".* Brave$")
            if pid is None or w.process_id() == pid]
    # le titre bouge (compteur de non lus) : on préfère l'onglet Gmail, sinon n'importe quelle fenêtre de l'agent
    for win in sorted(wins, key=lambda w: "Gmail" not in w.window_text()):
        return win
    raise RuntimeError("fenêtre Brave introuvable")


def focus_browser():
    """Ramène Brave au premier plan (si l'utilisateur a cliqué ailleurs ou l'a réduit)."""
    hwnd = brave_window().handle
    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    pyautogui.press("alt")  # autorise SetForegroundWindow depuis un process en arrière-plan
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)


def viewport_rect(driver):
    """Rectangle écran de la zone de page, lu via Windows : Brave fausse window.screenX/outerHeight
    côté JS (anti-fingerprinting), on ne peut donc pas s'y fier."""
    for _ in range(2):
        for child in brave_window().descendants(class_name="Chrome_RenderWidgetHostHWND"):
            if child.is_visible():
                return child.rectangle()
        focus_browser()
    # repli : bas de la zone cliente de la fenêtre, hauteur = innerHeight (barres d'onglets/adresse au-dessus)
    win = brave_window()
    rect, pt = ctypes.wintypes.RECT(), ctypes.wintypes.POINT(0, 0)
    ctypes.windll.user32.GetClientRect(win.handle, ctypes.byref(rect))
    ctypes.windll.user32.ClientToScreen(win.handle, ctypes.byref(pt))
    dpr = driver.execute_script("return window.devicePixelRatio") or 1
    height = int(driver.execute_script("return window.innerHeight") * dpr)
    bottom = pt.y + rect.bottom
    return RECT(pt.x, bottom - height, pt.x + rect.right, bottom)


def screen_center(driver, el):
    """Coordonnées écran (pixels physiques) du centre d'un élément de la page."""
    vp = viewport_rect(driver)
    scale = vp.width() / driver.execute_script("return document.documentElement.clientWidth")
    r = el.rect
    return int(vp.left + (r["x"] + r["width"] / 2) * scale), int(vp.top + (r["y"] + r["height"] / 2) * scale)


# ---------------------------------------------------------------- Gmail

ROW = "//tr[contains(@class,'zA')]"


EMPTY_LIST = "//div[@role='main']//div[contains(@class,'aRs')]"  # « Votre onglet Principale est vide »


def open_inbox(driver):
    """Boîte de réception chargée : des rangées, ou le message de liste vide."""
    if driver.current_url != INBOX_URL:  # un mail ouvert = #inbox/<id>
        driver.get(INBOX_URL)
    wait_visible(driver, f"{ROW} | {EMPTY_LIST}", 60)


def wait_for_new_mail(driver, subject=None, timeout=180):
    """Recharge la boîte jusqu'à ce que le 1er mail soit non lu (et ait le bon sujet)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        open_inbox(driver)
        try:
            row = visible(driver, ROW)[0]
            unread = "zE" in row.get_attribute("class")
            if unread and (subject is None or subject.split(":")[-1].strip() in row.text):
                return row
        except StaleElementReferenceException:  # Gmail a redessiné la liste entre-temps
            continue
        time.sleep(8)
        driver.refresh()
    raise TimeoutException(f"mail '{subject}' pas arrivé après {timeout}s")


def pick_row(driver):
    rows = visible(driver, ROW)
    unread = [r for r in rows if "zE" in r.get_attribute("class")]
    if unread:  # le plus récent non lu = la demande qu'on vient de recevoir
        return unread[0]
    if SENDER_EMAIL:
        for row in rows:
            if row.find_elements(By.XPATH, f".//span[@email='{SENDER_EMAIL}']"):
                return row
    return rows[0]


def read_open_mail(driver):
    wait_visible(driver, "//h2[contains(@class,'hP')]")
    time.sleep(1.5)
    subject = visible(driver, "//h2[contains(@class,'hP')]")[0].text
    # dans un fil, on lit le dernier message REÇU (pas notre propre réponse) ; on le déplie au besoin
    mine = (DEMO_EMAIL or "").lower()
    received = [s for s in visible(driver, "//span[contains(@class,'gD')]")
                if (s.get_attribute("email") or "").lower() != mine]
    body, name = "", ""
    if received:
        sender = received[-1]
        name = sender.get_attribute("name") or sender.text
        msg = sender.find_elements(By.XPATH, "./ancestor::div[contains(@class,'adn')][1]")
        if msg and not [b for b in msg[0].find_elements(By.CSS_SELECTOR, "div.a3s") if b.is_displayed()]:
            sender.click()  # message replié : on l'ouvre
            time.sleep(1.5)
        if msg:
            texts = [b.text for b in msg[0].find_elements(By.CSS_SELECTOR, "div.a3s") if b.is_displayed()]
            body = texts[0] if texts else ""
    if not body:
        bodies = visible(driver, "//div[contains(@class,'a3s')]")
        body = bodies[-1].text if bodies else ""
    if name.lower() in ("", "moi", "me"):  # mail envoyé depuis le compte démo lui-même
        name = SENDER_NAME
    return subject, body, name.split()[0]


def click_reply(driver):
    xp = ("//span[@role='link' and (normalize-space()='Répondre' or normalize-space()='Reply')]"
          " | //*[@role='button' and (@aria-label='Répondre' or @aria-label='Reply')]")
    box_xp = "//div[@contenteditable='true' and @role='textbox']"
    try:
        btn = wait_visible(driver, xp, timeout=6)[-1]
    except TimeoutException:
        # un brouillon est déjà ouvert dans ce fil : on le reprend et on efface son texte
        box = wait_visible(driver, box_xp)[-1]
        box.click()
        box.send_keys(Keys.CONTROL, "a")
        box.send_keys(Keys.DELETE)
        return box
    # au milieu de l'écran : le bandeau "notifications" de Gmail peut couvrir le bas de page
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'})", btn)
    time.sleep(0.4)
    pyautogui.moveTo(*screen_center(driver, btn), duration=0.6)
    try:
        btn.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click()", btn)
    return wait_visible(driver, "//div[@contenteditable='true' and @role='textbox']")[-1]


def wait_draft_saved(driver, timeout=12):
    """Gmail enregistre le brouillon quelques secondes après la frappe : on attend « Brouillon enregistré »
    avant de fermer la réponse, sinon Echap peut le faire disparaître."""
    xp = ("//*[contains(normalize-space(text()), 'Brouillon enregistré') or "
          "contains(normalize-space(text()), 'Draft saved') or contains(normalize-space(text()), 'Enregistré')]")
    end = time.time() + timeout
    while time.time() < end:
        if visible(driver, xp):
            return True
        time.sleep(0.5)
    return False


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
    win.wait("visible", timeout=45)  # l'Explorateur peut être lent quand la machine est chargée
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
    focus_browser()
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
