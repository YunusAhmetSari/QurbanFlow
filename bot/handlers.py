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

from config import ALLOWED_USER_IDS, DONORS_DIR

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
    donor_path, output_path, normalized_name, counter = create_donor_folder(donor_name)
    context.user_data["donor_name"] = donor_name
    context.user_data["normalized_name"] = normalized_name
    context.user_data["counter"] = counter
    context.user_data["donor_path"] = str(donor_path)
    context.user_data["output_path"] = str(output_path)

    # Flyer in den Spender-Ordner verschieben
    flyer_src = Path(context.user_data["media_files"]["flyer"])
    flyer_dst = donor_path / "flyer.jpg"
    flyer_src.rename(flyer_dst)
    context.user_data["media_files"]["flyer"] = str(flyer_dst)

    await update.message.reply_text(
        f"✅ *Spender:* `{donor_name}`\n"
        f"📁 *Ordner:* `{normalized_name}_{counter}`\n\n"
        f"📸 *Schritt 2:* Sende jetzt das Bild vom *Opfertier mit Flyer*.",
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
    has_distribution = context.user_data["media_files"].get("distribution") is not None
    
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
        f"📸 Opfertier: ✅\n"
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
        output_dir = Path(context.user_data["output_path"])
        normalized_name = context.user_data["normalized_name"]
        counter = context.user_data["counter"]

        output_file = output_dir / f"{normalized_name}_{counter}.mp4"

        # Video-Assembly starten
        result_path = assemble_video(
            flyer_image=Path(media["flyer"]),
            animal_image=Path(media["animal"]),
            slaughter_video=Path(media["slaughter"]),
            distribution_video=Path(media["distribution"]) if media.get("distribution") else None,
            output_path=output_file,
        )

        # Fertiges Video an User senden
        file_size = result_path.stat().st_size
        file_size_mb = file_size / 1024 / 1024
        logger.info(f"Video erstellt: {result_path} ({file_size_mb:.1f} MB)")

        # Telegram Bot-API hat ein hartes Limit von 50 MB für alle Uploads.
        # Falls das Video zu groß ist, wird es mit niedrigerer Bitrate neu kodiert.
        TELEGRAM_LIMIT = 49 * 1024 * 1024  # 49 MB (etwas Puffer)
        send_path = result_path

        if file_size > TELEGRAM_LIMIT:
            logger.info(f"Video zu groß ({file_size_mb:.1f} MB), wird komprimiert...")
            await update.message.reply_text(
                f"⚠️ Video ist {file_size_mb:.1f} MB groß (Telegram-Limit: 50 MB).\n"
                "🔄 *Wird komprimiert...*",
                parse_mode="Markdown",
            )

            compressed_path = result_path.parent / f"{result_path.stem}_compressed.mp4"
            try:
                import subprocess
                # Zielbitrate berechnen: (49 MB * 8 bit) / Dauer - Audio-Bitrate
                from core.video_assembler import get_video_duration
                duration = get_video_duration(result_path)
                # Zielgröße 48 MB, abzüglich ~128kbps Audio
                target_video_bitrate = int((48 * 8 * 1024) / duration - 128)  # in kbps
                target_video_bitrate = max(target_video_bitrate, 500)  # Mindestens 500 kbps

                logger.info(f"Komprimiere mit {target_video_bitrate}k Bitrate (Dauer: {duration:.1f}s)")

                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(result_path),
                    "-c:v", "libx264",
                    "-b:v", f"{target_video_bitrate}k",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-preset", "fast",
                    str(compressed_path),
                ]
                subprocess.run(cmd, check=True, capture_output=True)

                compressed_size = compressed_path.stat().st_size
                compressed_size_mb = compressed_size / 1024 / 1024
                logger.info(f"Komprimiert: {compressed_size_mb:.1f} MB")

                if compressed_size <= TELEGRAM_LIMIT:
                    send_path = compressed_path
                else:
                    logger.warning(f"Komprimiertes Video immer noch zu groß: {compressed_size_mb:.1f} MB")
                    await update.message.reply_text(
                        f"⚠️ Video konnte nicht unter 50 MB komprimiert werden ({compressed_size_mb:.1f} MB).\n"
                        f"📁 Das Video wurde lokal gespeichert unter:\n`{result_path}`",
                        parse_mode="Markdown",
                    )
                    return ConversationHandler.END

            except FileNotFoundError:
                logger.error("FFmpeg nicht gefunden – Komprimierung nicht möglich")
                await update.message.reply_text(
                    f"⚠️ Video ist zu groß ({file_size_mb:.1f} MB) und FFmpeg ist nicht installiert.\n"
                    f"📁 Das Video wurde lokal gespeichert unter:\n`{result_path}`",
                    parse_mode="Markdown",
                )
                return ConversationHandler.END
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg Komprimierung fehlgeschlagen: {e}")
                await update.message.reply_text(
                    f"⚠️ Video-Komprimierung fehlgeschlagen.\n"
                    f"📁 Das Video wurde lokal gespeichert unter:\n`{result_path}`",
                    parse_mode="Markdown",
                )
                return ConversationHandler.END

        # Video senden – mit korrektem File-Handle-Management
        send_size = send_path.stat().st_size
        caption = (
            f"✅ *Kurban-Video fertig!*\n"
            f"👤 Spender: `{context.user_data['donor_name']}`\n"
            f"📁 `{normalized_name}_{counter}`"
        )

        try:
            with open(str(send_path), "rb") as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=caption,
                    parse_mode="Markdown",
                    read_timeout=300,
                    write_timeout=300,
                    connect_timeout=60,
                )
            logger.info(f"Video erfolgreich an Telegram gesendet ({send_size / 1024 / 1024:.1f} MB)")
        except Exception as send_err:
            logger.warning(f"reply_video fehlgeschlagen: {send_err}, versuche als Dokument...")
            # Fallback: als Dokument senden
            try:
                with open(str(send_path), "rb") as video_file:
                    await update.message.reply_document(
                        document=video_file,
                        caption=caption + "\n\n⚠️ Als Dokument gesendet (Video-Vorschau nicht möglich).",
                        parse_mode="Markdown",
                        read_timeout=300,
                        write_timeout=300,
                        connect_timeout=60,
                    )
                logger.info(f"Video als Dokument gesendet ({send_size / 1024 / 1024:.1f} MB)")
            except Exception as doc_err:
                logger.error(f"Auch Dokument-Versand fehlgeschlagen: {doc_err}", exc_info=True)
                await update.message.reply_text(
                    f"❌ *Video konnte nicht gesendet werden.*\n\n"
                    f"Fehler: `{str(doc_err)}`\n\n"
                    f"📁 Das Video wurde lokal gespeichert unter:\n`{result_path}`",
                    parse_mode="Markdown",
                )

        # Komprimierte Temp-Datei aufräumen
        if send_path != result_path and send_path.exists():
            try:
                send_path.unlink()
            except Exception:
                pass

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
        "3️⃣ Opfertier-Bild senden\n"
        "4️⃣ Schlachtungsvideo senden\n"
        "5️⃣ Verteilungsvideo senden\n"
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
