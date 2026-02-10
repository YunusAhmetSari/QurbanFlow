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
ASSETS_DIR = BASE_DIR / "Vorlagen"
DONORS_DIR = BASE_DIR / "Spender"
OUTPUT_DIR = BASE_DIR / "Spender"

# Verzeichnisse erstellen, falls nicht vorhanden
DONORS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

# ── Feste Assets ────────────────────────────────────────────────────────────
AFRICA_CLIP = ASSETS_DIR / "africa_clip.mp4"
THANKS_CLIP = ASSETS_DIR / "thanks_clip.mp4"
SONG_A = ASSETS_DIR / "song_a.mp3"
SONG_B = ASSETS_DIR / "song_b.mp3"

# ── Telegram ────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_IDS = [
    int(uid.strip())
    for uid in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if uid.strip().isdigit()
]

# ── OpenAI ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ── Video-Einstellungen ────────────────────────────────────────────────────
FLYER_STILL_DURATION = int(os.getenv("FLYER_STILL_DURATION", "5"))       # Sekunden
ANIMAL_STILL_DURATION = int(os.getenv("ANIMAL_STILL_DURATION", "5"))     # Sekunden
MAX_SLAUGHTER_DURATION = int(os.getenv("MAX_SLAUGHTER_DURATION", "45"))  # Sekunden
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1920"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "1080"))
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "30"))

# ── Audio-Einstellungen ────────────────────────────────────────────────────
AUDIO_FADE_DURATION = 1.0   # Sekunden für Ein-/Ausblendung
TARGET_DBFS = -20.0          # Ziel-Lautstärke für Normalisierung
