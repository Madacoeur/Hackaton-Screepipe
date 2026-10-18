"""Petit client pour l'API locale de screenpipe (lecture seule)."""
import json
import os
import subprocess
import tempfile
import urllib.parse
import urllib.request

BASE = os.getenv("SCREENPIPE_LOCAL_API_URL", "http://localhost:3030")
BUN = os.path.expandvars(r"%LOCALAPPDATA%\screenpipe\bun.exe")
_token = None


def token():
    """Token d'API : variable d'environnement, sinon demandé à la CLI screenpipe (jamais stocké sur disque)."""
    global _token
    if _token is None:
        _token = os.getenv("SCREENPIPE_LOCAL_API_KEY") or subprocess.run(
            [BUN, "x", "screenpipe@latest", "auth", "token"],
            capture_output=True, text=True, cwd=tempfile.mkdtemp(), timeout=120,
        ).stdout.strip().splitlines()[-1]
    return _token


def get(path, **params):
    url = f"{BASE}{path}?{urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token()}",
        "X-Screenpipe-Client": "api",
        "X-Screenpipe-Agent": "claude",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def search_all(start, end, max_rows=200, **filters):
    """/search paginé (limit max 20 par page), trié chronologiquement."""
    rows, offset = [], 0
    while len(rows) < max_rows:
        page = get("/search", start_time=start.isoformat(), end_time=end.isoformat(),
                   limit=20, offset=offset, **filters)["data"]
        if not page:
            break
        rows += page
        offset += len(page)
    return sorted(rows, key=lambda r: r["content"]["timestamp"])
