import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# Expéditeur "client" des demandes
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_NAME = os.getenv("SENDER_NAME", "Karim - Studio Nova")
REPLY_TO = os.getenv("REPLY_TO", "")

# Serveur SMTP : Brevo par défaut (smtp-relay.brevo.com), ou Gmail avec mot de passe d'application
SMTP_HOST = os.getenv("SMTP_HOST", "smtp-relay.brevo.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_LOGIN = os.getenv("SMTP_LOGIN", SENDER_EMAIL)
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").replace(" ", "")

# Compte démo (celui qui est connecté dans le navigateur et qui répond)
DEMO_EMAIL = os.getenv("DEMO_EMAIL", "")
SIGNATURE = os.getenv("SIGNATURE", "Table En")

BROWSER_PATH = os.getenv("BROWSER_PATH", r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe")
DEBUG_PORT = int(os.getenv("DEBUG_PORT", "9222"))
PROFILE_DIR = ROOT / "browser_profile"

FILES_DIR = Path(os.path.expandvars(os.getenv("FILES_DIR", r"%USERPROFILE%\Documents\Freelance-Demo")))

LOG_FILE = ROOT / "scenarios_log.jsonl"
