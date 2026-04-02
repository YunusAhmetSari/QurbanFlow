"""
QurbanFlow – Telegram Bot Handlers

Konversations-basierter Flow:
1. /start → Willkommen, warte auf Flyer
2. Flyer empfangen → OCR → Name bestätigen
3. Opfertier-Bild empfangen
4. Schlachtungsvideo empfangen
5. Verteilungsvideo empfangen
6. Bestätigung → Pipeline starten → Video zurücksenden
"""

import logging



from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)


from core.donor_manager import create_donor_folder
from core.video_assembler import assemble_video

from config import ALLOWED_USER_IDS, DONORS_DIR, NOTIFY_USER_ID

logger = logging.getLogger(__name__)

# ── Konversations-States ────────────────────────────────────────────────────
AWAITING_FLYER = 0
CONFIRM_NAME = 1
AWAITING_ANIMAL_PHOTO = 2
AWAITING_SLAUGHTER_VIDEO = 3
AWAITING_DISTRIBUTION_VIDEO = 4
CONFIRM_ASSEMBLY = 5


def _is_authorized(user_id: int) -> bool:
    """Prüft ob der User berechtigt ist."""
    if not ALLOWED_USER_IDS:
        return True  # Kein Filter konfiguriert → alle erlaubt
    return user_id in ALLOWED_USER_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler für /start – Beginnt den Workflow."""
    user = update.effective_user

    if not _is_authorized(user.id):
        await update.message.reply_text("⛔ Du bist nicht berechtigt, diesen Bot zu nutzen.")
        return ConversationHandler.END

    await update.message.reply_text(
        f"🕌 *Bismillah!* Willkommen, {user.first_name}!\n\n"
        "Ich helfe dir, ein Kurban-Video zu erstellen.\n\n"
        "📸 *Schritt 1:* Sende mir bitte den *Flyer* (Vollbild) als Foto.\n"
        "Daraus lese ich den Namen des Spenders.",
        parse_mode="Markdown",
    )

    # Temp-Daten für diese Session initialisieren
    context.user_data.clear()
    context.user_data["media_files"] = {}

    return AWAITING_FLYER


async def receive_flyer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Flyer-Bild empfangen → Manuelle Namenseingabe."""
    photo = update.message.photo[-1] if update.message.photo else None
    document = update.message.document if not photo else None

    if not photo and not document:
        await update.message.reply_text("❌ Bitte sende ein *Foto* des Flyers.", parse_mode="Markdown")
        return AWAITING_FLYER

    # Foto herunterladen
    if photo:
        file = await photo.get_file()
    else:
        file = await document.get_file()

    # Temporärer Speicherort
    temp_dir = DONORS_DIR / "_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    flyer_path = temp_dir / f"flyer_{update.effective_user.id}.jpg"

    await file.download_to_drive(str(flyer_path))
    context.user_data["media_files"]["flyer"] = str(flyer_path)

    # OCR überspringen -> Direkt nach Namen fragen
    await update.message.reply_text(
        "✅ Flyer erhalten!\n\n"
        "✏️ Bitte gib jetzt den *Spendernamen* ein:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data["manual_name_input"] = True
    return CONFIRM_NAME


async def confirm_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Name bestätigen oder korrigieren."""
    text = update.message.text.strip()

    if text == "✅ Ja, korrekt":
        donor_name = context.user_data["donor_name_suggestion"]
    elif text == "❌ Nein, Name korrigieren":
        await update.message.reply_text(
            "✏️ Bitte gib den *korrekten Spendernamen* ein:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data["manual_name_input"] = True
        return CONFIRM_NAME
    elif context.user_data.get("manual_name_input"):
        donor_name = text
        context.user_data.pop("manual_name_input", None)
    else:
        await update.message.reply_text("Bitte wähle eine Option oder gib den Namen ein.")
        return CONFIRM_NAME

    # Ordner anlegen
    donor_path, normalized_name, counter = create_donor_folder(donor_name)
    context.user_data["donor_name"] = donor_name
    context.user_data["normalized_name"] = normalized_name
    context.user_data["counter"] = counter
    context.user_data["donor_path"] = str(donor_path)

    # Flyer in den Spender-Ordner verschieben
    flyer_src = Path(context.user_data["media_files"]["flyer"])
    flyer_dst = donor_path / "flyer.jpg"
    flyer_src.rename(flyer_dst)
    context.user_data["media_files"]["flyer"] = str(flyer_dst)

    await update.message.reply_text(
        f"✅ *Spender:* `{donor_name}`\n"
        f"📁 *Ordner:* `{normalized_name}_{counter}`\n\n"
        f"📸 *Schritt 2:* Sende jetzt das Bild vom *Opfertier mit Flyer*.\n"
        f"_Oder sende /skip um diesen Schritt zu überspringen._",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return AWAITING_ANIMAL_PHOTO


async def receive_animal_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Opfertier-Bild empfangen."""
    photo = update.message.photo[-1] if update.message.photo else None
    document = update.message.document if not photo else None

    if not photo and not document:
        await update.message.reply_text("❌ Bitte sende ein *Foto* des Opfertiers.", parse_mode="Markdown")
        return AWAITING_ANIMAL_PHOTO

    if photo:
        file = await photo.get_file()
    else:
        file = await document.get_file()

    donor_path = Path(context.user_data["donor_path"])
    animal_path = donor_path / "animal.jpg"
    await file.download_to_drive(str(animal_path))
    context.user_data["media_files"]["animal"] = str(animal_path)

    await update.message.reply_text(
        "✅ Opfertier-Bild erhalten!\n\n"
        "🎥 *Schritt 3:* Sende das *Schlachtungsvideo* (Gebet & Schlachtung).",
        parse_mode="Markdown",
    )
    return AWAITING_SLAUGHTER_VIDEO


async def skip_animal_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Opfertier-Bild überspringen."""
    context.user_data["media_files"]["animal"] = None

    await update.message.reply_text(
        "⏩ Opfertier-Bild übersprungen.\n\n"
        "🎥 *Schritt 3:* Sende das *Schlachtungsvideo* (Gebet & Schlachtung).",
        parse_mode="Markdown",
    )
    return AWAITING_SLAUGHTER_VIDEO


async def receive_slaughter_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Schlachtungsvideo empfangen."""
    video = update.message.video
    document = update.message.document if not video else None

    if not video and not document:
        await update.message.reply_text("❌ Bitte sende ein *Video*.", parse_mode="Markdown")
        return AWAITING_SLAUGHTER_VIDEO

    if video:
        file = await video.get_file()
        ext = ".mp4"
    else:
        file = await document.get_file()
        ext = Path(document.file_name).suffix if document.file_name else ".mp4"

    donor_path = Path(context.user_data["donor_path"])
    slaughter_path = donor_path / f"slaughter{ext}"
    await file.download_to_drive(str(slaughter_path))
    context.user_data["media_files"]["slaughter"] = str(slaughter_path)

    await update.message.reply_text(
        "✅ Schlachtungsvideo erhalten!\n\n"
        "🎥 *Schritt 4:* Sende das *Verteilungsvideo* (Fleisch & Gebete).\n"
        "_Oder sende /skip um diesen Schritt zu überspringen._",
        parse_mode="Markdown",
    )
    return AWAITING_DISTRIBUTION_VIDEO


async def receive_distribution_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Verteilungsvideo empfangen."""
    video = update.message.video
    document = update.message.document if not video else None

    if not video and not document:
        await update.message.reply_text("❌ Bitte sende ein *Video*.", parse_mode="Markdown")
        return AWAITING_DISTRIBUTION_VIDEO

    if video:
        file = await video.get_file()
        ext = ".mp4"
    else:
        file = await document.get_file()
        ext = Path(document.file_name).suffix if document.file_name else ".mp4"

    donor_path = Path(context.user_data["donor_path"])
    distribution_path = donor_path / f"distribution{ext}"
    await file.download_to_drive(str(distribution_path))
    context.user_data["media_files"]["distribution"] = str(distribution_path)

    # Zusammenfassung zeigen
    return await _show_summary(update, context)


async def skip_distribution_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Verteilungsvideo überspringen."""
    context.user_data["media_files"]["distribution"] = None
    
    await update.message.reply_text(
        "⏩ Verteilungsvideo übersprungen.",
        parse_mode="Markdown"
    )
    return await _show_summary(update, context)


async def _show_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Zeigt die Zusammenfassung und fragt nach Bestätigung."""
    donor_name = context.user_data["donor_name"]
    has_animal = context.user_data["media_files"].get("animal") is not None
    has_distribution = context.user_data["media_files"].get("distribution") is not None
    
    animal_status = "✅" if has_animal else "❌ (übersprungen)"
    dist_status = "✅" if has_distribution else "❌ (übersprungen)"

    keyboard = ReplyKeyboardMarkup(
        [["🎬 Video erstellen!"], ["❌ Abbrechen"]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )

    await update.message.reply_text(
        f"✅ Alle Medien erhalten!\n\n"
        f"📋 *Zusammenfassung:*\n"
        f"👤 Spender: `{donor_name}`\n"
        f"📸 Flyer: ✅\n"
        f"📸 Opfertier: {animal_status}\n"
        f"🎥 Schlachtung: ✅\n"
        f"🎥 Verteilung: {dist_status}\n\n"
        f"Soll ich das Video jetzt erstellen?",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    return CONFIRM_ASSEMBLY


async def confirm_assembly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Assembly bestätigen und Pipeline starten."""
    text = update.message.text.strip()

    if text == "❌ Abbrechen":
        await update.message.reply_text(
            "❌ Abgebrochen. Sende /start um von vorne zu beginnen.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    if text != "🎬 Video erstellen!":
        await update.message.reply_text("Bitte wähle eine Option.")
        return CONFIRM_ASSEMBLY

    await update.message.reply_text(
        "⏳ *Video wird erstellt...*\n\n"
        "Das kann einige Minuten dauern. Ich melde mich, wenn es fertig ist! 🎬",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )

    try:
        media = context.user_data["media_files"]
        output_dir = Path(context.user_data["donor_path"])
        normalized_name = context.user_data["normalized_name"]
        counter = context.user_data["counter"]

        output_file = output_dir / f"{normalized_name}_{counter}.mp4"

        # Video-Assembly starten
        result_path = assemble_video(
            flyer_image=Path(media["flyer"]),
            animal_image=Path(media["animal"]) if media.get("animal") else None,
            slaughter_video=Path(media["slaughter"]),
            distribution_video=Path(media["distribution"]) if media.get("distribution") else None,
            output_path=output_file,
        )

        # Benachrichtigung: Video erstellt
        file_size = result_path.stat().st_size
        file_size_mb = file_size / 1024 / 1024
        logger.info(f"Video erstellt: {result_path} ({file_size_mb:.1f} MB)")

        # Video an den Anfragenden senden
        await update.message.reply_text(
            f"✅ *Kurban-Video wurde erfolgreich erstellt!*\n\n"
            f"👤 Spender: `{context.user_data['donor_name']}`\n"
            f"📦 Größe: {file_size_mb:.1f} MB\n\n"
            f"⏳ Video wird gesendet...",
            parse_mode="Markdown",
        )

        # Video als natives Video senden (ermöglicht Player am Handy)
        try:
            with open(str(result_path), "rb") as video_file:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=video_file,
                    filename=result_path.name,
                    caption=f"🎬 Kurban-Video: {context.user_data['donor_name']}",
                    supports_streaming=True,
                )
            logger.info(f"Video an User {update.effective_user.id} gesendet")
        except Exception as send_err:
            logger.error(f"Video-Versand an User fehlgeschlagen: {send_err}")
            # Fallback: Als Dokument versuchen
            try:
                with open(str(result_path), "rb") as video_file:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=video_file,
                        filename=result_path.name,
                        caption=f"🎬 Kurban-Video: {context.user_data['donor_name']} (Fallback Dokument)",
                    )
            except Exception:
                await update.message.reply_text(
                    f"⚠️ Video konnte nicht gesendet werden: `{send_err}`\n"
                    f"Das Video liegt aber unter: `{result_path}`",
                    parse_mode="Markdown",
                )

        # Video auch an den Weiterleitenden (NOTIFY_USER_ID) senden
        if NOTIFY_USER_ID:
            try:
                await context.bot.send_message(
                    chat_id=NOTIFY_USER_ID,
                    text=(
                        f"🔔 *Neues Kurban-Video fertig!*\n\n"
                        f"👤 Spender: `{context.user_data['donor_name']}`\n"
                        f"📁 Ordner: `{normalized_name}_{counter}`\n"
                        f"📦 Größe: {file_size_mb:.1f} MB"
                    ),
                    parse_mode="Markdown",
                )
                # Video auch an NOTIFY_USER senden
                with open(str(result_path), "rb") as video_file:
                    await context.bot.send_video(
                        chat_id=NOTIFY_USER_ID,
                        video=video_file,
                        filename=result_path.name,
                        caption=f"🎬 Kurban-Video: {context.user_data['donor_name']}",
                        supports_streaming=True,
                    )
                logger.info(f"Video an NOTIFY_USER {NOTIFY_USER_ID} gesendet")
            except Exception as notify_err:
                logger.error(f"Benachrichtigung/Versand an NOTIFY_USER fehlgeschlagen: {notify_err}")

    except Exception as e:
        logger.error(f"Video-Assembly fehlgeschlagen: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ *Fehler bei der Video-Erstellung:*\n\n`{str(e)}`\n\n"
            "Bitte versuche es erneut mit /start.",
            parse_mode="Markdown",
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler für /cancel – Bricht den Workflow ab."""
    await update.message.reply_text(
        "❌ Abgebrochen. Sende /start um von vorne zu beginnen.",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler für /help."""
    await update.message.reply_text(
        "🕌 *QurbanFlow – Hilfe*\n\n"
        "*Befehle:*\n"
        "/start – Neues Kurban-Video erstellen\n"
        "/cancel – Aktuellen Vorgang abbrechen\n"
        "/help – Diese Hilfe anzeigen\n\n"
        "*Ablauf:*\n"
        "1️⃣ Flyer-Bild senden\n"
        "2️⃣ Spendername bestätigen\n"
        "3️⃣ Opfertier-Bild senden (oder /skip)\n"
        "4️⃣ Schlachtungsvideo senden\n"
        "5️⃣ Verteilungsvideo senden (oder /skip)\n"
        "6️⃣ Video wird automatisch erstellt! 🎬",
        parse_mode="Markdown",
    )


def get_conversation_handler() -> ConversationHandler:
    """Erstellt und gibt den Konversations-Handler zurück."""
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AWAITING_FLYER: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, receive_flyer),
            ],
            CONFIRM_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_name),
            ],
            AWAITING_ANIMAL_PHOTO: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, receive_animal_photo),
                CommandHandler("skip", skip_animal_photo),
            ],
            AWAITING_SLAUGHTER_VIDEO: [
                MessageHandler(
                    filters.VIDEO | filters.Document.ALL,
                    receive_slaughter_video,
                ),
            ],
            AWAITING_DISTRIBUTION_VIDEO: [
                MessageHandler(
                    filters.VIDEO | filters.Document.ALL,
                    receive_distribution_video,
                ),
                CommandHandler("skip", skip_distribution_video),
            ],
            CONFIRM_ASSEMBLY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_assembly),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
