# 🕌 QurbanFlow – Automatische Kurban-Video-Produktion

Ein Telegram-Bot der automatisch Kurban-Videos zusammenschneidet, basierend auf einem festen Schema.

## ✨ Features

- 🤖 **Telegram-Bot** — Dein Vater schickt Medien direkt an den Bot
- 📁 **Intelligente Ordnerstruktur** — Automatischer Zähler pro Spender (z.B. Max Mustermann 1, Max Mustermann 2)
- 🎬 **Automatischer Videoschnitt** — Clips werden nach festem Schema zusammengebaut
- 📤 **Direkter Versand** — Fertiges Video wird automatisch zurück an Telegram gesendet

## 📐 Video-Schema

| # | Inhalt | Audio |
|---|--------|-------|
| 1 | Flyer (Vollbild) | 🎵 Song A |
| 2 | Afrika-Clip (fest) | 🎵 Song A |
| 3 | Opfertier + Flyer (optional) | 🎵 Song A |
| 4 | Gebet & Schlachtung | 🔊 Original |
| 5 | Verteilung & Gebete (optional) | 🔊 Original |
| 6 | Dankeschön-Clip (fest) | 🎵 Song B |

## 🚀 Schnellstart

### 1. Voraussetzungen

- Python 3.11+
- FFmpeg installiert und im PATH
- Telegram Bot Token (von [@BotFather](https://t.me/BotFather))

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

Die Assets liegen bereits im `Vorlagen/`-Ordner:

```
Vorlagen/
├── Afrika.mp4         # Kurzes Afrika-Video
├── Dankeschön.mp4     # Kurzes Dankeschön-Video
└── SamiYusuf.mp4      # Hintergrundmusik (Video als Audio genutzt)
```

Eingehende Medien und fertige Videos werden in `Spender/` gespeichert.

### 5. Bot starten (lokal)

```bash
python -m bot.telegram_bot
```

### 5b. Bot starten (Cloud/Docker – empfohlen)

Für Dateien bis **2 GB** und ohne laufenden PC:

```bash
# .env konfigurieren (TELEGRAM_API_ID + TELEGRAM_API_HASH von my.telegram.org)
cp .env.example .env
notepad .env

# Mit Docker starten
docker compose up -d --build
```

👉 Siehe [deploy.md](deploy.md) für die vollständige Deployment-Anleitung auf Hetzner Cloud.

### 6. Nutzen

Dem Bot in Telegram schreiben:
1. `/start` senden
2. Flyer-Bild schicken
3. Spendername eingeben
4. Opfertier-Bild schicken (oder `/skip`)
5. Schlachtungsvideo schicken
6. Verteilungsvideo schicken (oder `/skip`)
7. ✅ Fertiges Video wird automatisch zurückgesendet!

## ⚙️ Konfiguration

Alle Einstellungen in `.env`:

| Variable | Standard | Beschreibung |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | Telegram Bot Token |
| `ALLOWED_USER_IDS` | — | Kommagetrennte Telegram User-IDs |
| `NOTIFY_USER_ID` | — | Telegram User-ID für Benachrichtigungen |
| `FLYER_STILL_DURATION` | 5 | Sekunden für Flyer-Standbild |
| `ANIMAL_STILL_DURATION` | 5 | Sekunden für Opfertier-Standbild |
| `VIDEO_WIDTH` | 1280 | Ausgabe-Breite (px) |
| `VIDEO_HEIGHT` | 720 | Ausgabe-Höhe (px) |
| `VIDEO_FPS` | 24 | Frames pro Sekunde |

## 📁 Projektstruktur

```
QurbanFlow/
├── bot/                    # Telegram-Bot
│   ├── telegram_bot.py     # Bot-Einstiegspunkt
│   └── handlers.py         # Konversations-Handler
├── core/                   # Kernlogik
│   ├── donor_manager.py    # Spenderverwaltung
│   └── video_assembler.py  # Video-Assembly
├── Vorlagen/               # Feste Medien (Afrika, Danke, Song)
└── Spender/                # Eingehende Medien + fertige Videos
```
