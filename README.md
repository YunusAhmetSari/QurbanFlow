# 🕌 QurbanFlow – Automatische Kurban-Video-Produktion

Ein Telegram-Bot der automatisch Kurban-Videos zusammenschneidet, basierend auf einem festen Schema.

## ✨ Features

- 🤖 **Telegram-Bot** — Dein Vater schickt Medien direkt an den Bot
- 🔍 **KI-Texterkennung** — Spendername wird automatisch vom Flyer erkannt (GPT-4o Vision)
- 📁 **Intelligente Ordnerstruktur** — Automatischer Zähler pro Spender (z.B. Max_Mustermann_1, Max_Mustermann_2)
- 🎬 **Automatischer Videoschnitt** — Clips werden nach festem Schema zusammengebaut
- 🔊 **Audio-Normalisierung** — Einheitliche Lautstärke über das gesamte Video
- 📤 **Direkter Versand** — Fertiges Video wird automatisch zurück an Telegram gesendet

## 📐 Video-Schema

| # | Inhalt | Audio |
|---|--------|-------|
| 1 | Flyer (Vollbild) | 🎵 Song A |
| 2 | Afrika-Clip (fest) | 🎵 Song A |
| 3 | Opfertier + Flyer | 🎵 Song A |
| 4 | Gebet & Schlachtung | 🔊 Original |
| 5 | Verteilung & Gebete | 🔊 Original |
| 6 | Dankeschön-Clip (fest) | 🎵 Song B |

## 🚀 Schnellstart

### 1. Voraussetzungen

- Python 3.11+
- FFmpeg installiert und im PATH
- Telegram Bot Token (von [@BotFather](https://t.me/BotFather))
- OpenAI API Key

### 2. Installation

```bash
# Repository klonen / in das Projektverzeichnis wechseln
cd QurbanFlow

# Virtual Environment erstellen
python -m venv venv
venv\Scripts\activate  # Windows

# Abhängigkeiten installieren
pip install -r requirements.txt
```

### 3. Konfiguration

```bash
# .env-Datei erstellen
copy .env.example .env

# .env bearbeiten und Tokens eintragen
notepad .env
```

### 4. Assets bereitstellen

Lege die festen Medien in den `assets/`-Ordner:

```
assets/
├── africa_clip.mp4    # Kurzes Afrika-Video (lächelnde Kinder)
├── thanks_clip.mp4    # Kurzes Dankeschön-Video
├── song_a.mp3         # Hintergrundmusik für Clips 1-3
└── song_b.mp3         # Hintergrundmusik für Clip 6
```

### 5. Bot starten

```bash
python -m bot.telegram_bot
```

### 6. Nutzen

Dem Bot in Telegram schreiben:
1. `/start` senden
2. Flyer-Bild schicken
3. Spendername bestätigen
4. Opfertier-Bild schicken
5. Schlachtungsvideo schicken
6. Verteilungsvideo schicken
7. ✅ Fertiges Video wird automatisch zurückgesendet!

## ⚙️ Konfiguration

Alle Einstellungen in `.env`:

| Variable | Standard | Beschreibung |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | Telegram Bot Token |
| `OPENAI_API_KEY` | — | OpenAI API Key |
| `ALLOWED_USER_IDS` | — | Kommagetrennte Telegram User-IDs |
| `FLYER_STILL_DURATION` | 5 | Sekunden für Flyer-Standbild |
| `ANIMAL_STILL_DURATION` | 5 | Sekunden für Opfertier-Standbild |
| `MAX_SLAUGHTER_DURATION` | 45 | Max. Sekunden Schlachtungsvideo |
| `VIDEO_WIDTH` | 1920 | Ausgabe-Breite (px) |
| `VIDEO_HEIGHT` | 1080 | Ausgabe-Höhe (px) |
| `VIDEO_FPS` | 30 | Frames pro Sekunde |

## 🧪 Tests

```bash
python -m pytest tests/ -v
```

## 📁 Projektstruktur

```
QurbanFlow/
├── bot/                    # Telegram-Bot
│   ├── telegram_bot.py     # Bot-Einstiegspunkt
│   └── handlers.py         # Konversations-Handler
├── core/                   # Kernlogik
│   ├── donor_manager.py    # Spenderverwaltung
│   ├── ocr.py              # Flyer-Texterkennung
│   ├── video_assembler.py  # Video-Assembly
│   └── audio_processor.py  # Audio-Verarbeitung
├── assets/                 # Feste Medien
├── donors/                 # Eingehende Spender-Medien
├── output/                 # Gerenderte Videos
└── tests/                  # Unit-Tests
```
