"""
QurbanFlow – Telegram Bot

Einstiegspunkt für den Telegram-Bot.
Startet den Bot und registriert alle Handler.

Nutzung:
    python -m bot.telegram_bot
"""

import logging
import sys
from pathlib import Path

# Projektverzeichnis zum Python-Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telegram.ext import Application, CommandHandler

from config import TELEGRAM_BOT_TOKEN
from bot.handlers import get_conversation_handler, help_command

# ── Logging einrichten ──────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# Telegram-eigene Logs reduzieren
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main():
    """Bot starten."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN ist nicht gesetzt!\n"
            "Bitte erstelle eine .env-Datei (siehe .env.example)."
        )
        sys.exit(1)

    logger.info("🕌 QurbanFlow Bot wird gestartet...")

    # Application erstellen
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(300)
        .write_timeout(300)
        .connect_timeout(300)
        .pool_timeout(300)
        .build()
    )

    # Handler registrieren
    application.add_handler(get_conversation_handler())
    application.add_handler(CommandHandler("help", help_command))

    # Bot starten (Polling-Modus)
    logger.info("Bot läuft! Drücke Strg+C zum Beenden.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
