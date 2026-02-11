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
OUTPUT_DIR = BASE_DIR / "Output"    # Neu, um Originaldaten nicht zu vermischen

# Verzeichnisse erstellen, falls nicht vorhanden
DONORS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

# ── Feste Assets ────────────────────────────────────────────────────────────
# Dateinamen basierend auf `ls Vorlagen` angepasst
AFRICA_CLIP = ASSETS_DIR / "Afrika.mp4"
THANKS_CLIP = ASSETS_DIR / "Dankeschön.mp4"
SONG_A = ASSETS_DIR / "SamiYusuf.mp4" # Das ist eigentlich ein Video, wird als Audio genutzt
SONG_B = ASSETS_DIR / "Dankeschön.mp4" # Fallback: Nutze Audio vom Thanks-Clip, falls kein song_b.mp3 da ist

# ── Telegram ────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_USER_IDS = [
    int(uid.strip())
    for uid in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if uid.strip().isdigit()
]

# ── OpenAI ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# ── Video-Einstellungen ────────────────────────────────────────────────────
FLYER_STILL_DURATION = int(os.getenv("FLYER_STILL_DURATION", "5"))       # Sekunden
ANIMAL_STILL_DURATION = int(os.getenv("ANIMAL_STILL_DURATION", "5"))     # Sekunden
MAX_SLAUGHTER_DURATION = int(os.getenv("MAX_SLAUGHTER_DURATION", "90"))  # Sekunden
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1280"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "720"))
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "24"))

# ── Audio-Einstellungen ────────────────────────────────────────────────────
AUDIO_FADE_DURATION = 1.0   # Sekunden für Ein-/Ausblendung
TARGET_DBFS = -20.0          # Ziel-Lautstärke für Normalisierung
