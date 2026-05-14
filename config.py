"""
QurbanFlow – Zentrale Konfiguration

Alle Pfade, Limits und Einstellungen an einem Ort.
Werte können über .env-Datei überschrieben werden.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Basispfade ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "Vorlagen"  # War vorher "assets"
DONORS_DIR = BASE_DIR / "Spender"   # War vorher "donors"
PDFS_DIR   = BASE_DIR / "PDFs"      # Ausgabeordner für PDF-Listen
FONTS_DIR  = ASSETS_DIR / "fonts"   # Schriftarten

# Verzeichnisse erstellen, falls nicht vorhanden
DONORS_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)
PDFS_DIR.mkdir(exist_ok=True)
FONTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Feste Assets ────────────────────────────────────────────────────────────
# Dateinamen basierend auf `ls Vorlagen` angepasst
AFRICA_CLIP = ASSETS_DIR / "Afrika.mp4"
THANKS_CLIP = ASSETS_DIR / "Dankeschön.mp4"
SONG_A = ASSETS_DIR / "SamiYusuf.mp4" # Das ist eigentlich ein Video, wird als Audio genutzt
SONG_B = ASSETS_DIR / "Dankeschön.mp4" # Fallback: Nutze Audio vom Thanks-Clip, falls kein song_b.mp3 da ist

# ── Kurban-PDF-Einstellungen ────────────────────────────────────────────────
KURBAN_VORLAGE = ASSETS_DIR / "Kurban_Vorlage.jpeg"
KURBAN_COUNTER_FILE = PDFS_DIR / "kurban_counter.json"
KURBAN_HISTORY_FILE = PDFS_DIR / "kurban_history.json"
KURBAN_STATS_FILE = PDFS_DIR / "kurban_stats.json"
KURBAN_TYPES = ["VACİP", "ADAK", "ŞÜKÜR", "AKİKA", "NAFİLE"]

# ── Telegram ────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_USER_IDS = [
    int(uid.strip())
    for uid in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if uid.strip().isdigit()
]

# User-ID, die benachrichtigt wird, wenn ein Video fertig ist (z.B. für manuelles Weiterleiten)
_notify_id = os.getenv("NOTIFY_USER_ID", "").strip()
NOTIFY_USER_ID = int(_notify_id) if _notify_id.isdigit() else None

# ── Lokaler Telegram Bot API Server (für Dateien bis 2 GB) ─────────────────
# Wenn gesetzt, verbindet sich der Bot mit dem lokalen API-Server statt api.telegram.org
TELEGRAM_API_BASE_URL = os.getenv("TELEGRAM_API_BASE_URL", "").strip() or None
TELEGRAM_API_BASE_FILE_URL = os.getenv("TELEGRAM_API_BASE_FILE_URL", "").strip() or None
TELEGRAM_LOCAL_MODE = os.getenv("TELEGRAM_LOCAL_MODE", "").strip().lower() in ("true", "1", "yes")
# ── Video-Einstellungen ────────────────────────────────────────────────────
FLYER_STILL_DURATION = int(os.getenv("FLYER_STILL_DURATION", "5"))       # Sekunden
ANIMAL_STILL_DURATION = int(os.getenv("ANIMAL_STILL_DURATION", "5"))     # Sekunden
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1280"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "720"))
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "24"))

# ── Audio-Einstellungen ────────────────────────────────────────────────────
TARGET_DBFS = float(os.getenv("TARGET_DBFS", "-20.0"))          # Ziel-Lautstärke in dBFS
AUDIO_FADE_DURATION = float(os.getenv("AUDIO_FADE_DURATION", "1.0"))  # Fade-Dauer in Sekunden
