"""
QurbanFlow – Telegram Bot Handlers

Konversations-basierter Flow mit Auswahlmenü:

A) Video-Flow:
   1. /start → Auswahl: Video oder PDF
   2. Flyer empfangen → OCR → Name bestätigen
   3. Opfertier-Bild empfangen
   4. Schlachtungsvideo empfangen
   5. Verteilungsvideo empfangen
   6. Bestätigung → Pipeline starten → Video zurücksenden

B) PDF-Listen-Flow:
   1. /start → Auswahl: Video oder PDF
   2. Name eingeben (max. 7×)
   3. Kurban-Typ wählen
   4. Weitere Namen? Ja / Nein
   5. Zusammenfassung + ggf. Korrektur
   6. PDF generieren & senden
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
from core.pdf_generator import (
    generate_kurban_pdf,
    get_stats_text,
)

from config import ALLOWED_USER_IDS, DONORS_DIR, NOTIFY_USER_ID, KURBAN_TYPES

logger = logging.getLogger(__name__)

# ── Konversations-States ────────────────────────────────────────────────────
# Gemeinsam
CHOOSE_AUTOMATION = 0

# Video-Flow
AWAITING_FLYER = 1
CONFIRM_NAME = 2
AWAITING_ANIMAL_PHOTO = 3
AWAITING_SLAUGHTER_VIDEO = 4
AWAITING_DISTRIBUTION_VIDEO = 5
CONFIRM_ASSEMBLY = 6

# PDF-Flow
PDF_ENTER_NAME = 11
PDF_CHOOSE_TYPE = 12
PDF_MORE_NAMES = 13
PDF_CONFIRM = 14
PDF_EDIT_CHOICE = 15
PDF_EDIT_NAME = 16
PDF_EDIT_TYPE = 17


def _is_authorized(user_id: int) -> bool:
    """Prüft ob der User berechtigt ist."""
    if not ALLOWED_USER_IDS:
        return True  # Kein Filter konfiguriert → alle erlaubt
    return user_id in ALLOWED_USER_IDS


# ══════════════════════════════════════════════════════════════════════════════
#  GEMEINSAME HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler für /start – Zeigt Auswahlmenü."""
    user = update.effective_user

    if not _is_authorized(user.id):
        await update.message.reply_text("⛔ Du bist nicht berechtigt, diesen Bot zu nutzen.")
        return ConversationHandler.END

    keyboard = ReplyKeyboardMarkup(
        [["🎬 Kurban-Video erstellen"], ["📄 Kurban-Liste (PDF)"], ["📊 Statistik"]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )

    await update.message.reply_text(
        f"🕌 *Bismillah!* Willkommen, {user.first_name}!\n\n"
        "Was möchtest du tun?",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

    # Temp-Daten für diese Session initialisieren
    context.user_data.clear()

    return CHOOSE_AUTOMATION


async def choose_automation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Auswahl zwischen Video und PDF."""
    text = update.message.text.strip()

    if text == "🎬 Kurban-Video erstellen":
        # Video-Flow starten
        context.user_data["media_files"] = {}
        await update.message.reply_text(
            "📸 *Schritt 1:* Sende mir bitte den *Flyer* (Vollbild) als Foto.\n"
            "Daraus lese ich den Namen des Spenders.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return AWAITING_FLYER

    elif text == "📄 Kurban-Liste (PDF)":
        # PDF-Flow starten
        context.user_data["pdf_entries"] = []

        await update.message.reply_text(
            "📄 *Kurban-Liste erstellen*\n\n"
            "✏️ Gib jetzt den *1. Namen* ein:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return PDF_ENTER_NAME

    elif text == "📊 Statistik":
        stats_text = get_stats_text()
        keyboard = ReplyKeyboardMarkup(
            [["🎬 Kurban-Video erstellen"], ["📄 Kurban-Liste (PDF)"], ["📊 Statistik"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        )
        await update.message.reply_text(
            stats_text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        return CHOOSE_AUTOMATION

    else:
        await update.message.reply_text("Bitte wähle eine der Optionen.")
        return CHOOSE_AUTOMATION


# ══════════════════════════════════════════════════════════════════════════════
#  VIDEO-FLOW HANDLER (bestehend)
# ══════════════════════════════════════════════════════════════════════════════

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
    return await _show_video_summary(update, context)


async def skip_distribution_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Verteilungsvideo überspringen."""
    context.user_data["media_files"]["distribution"] = None

    await update.message.reply_text(
        "⏩ Verteilungsvideo übersprungen.",
        parse_mode="Markdown"
    )
    return await _show_video_summary(update, context)


async def _show_video_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
        result_path, thumb_path, duration, width, height = assemble_video(
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

        # Video an den Anfragenden senden (ermöglicht Player am Handy)
        try:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=str(result_path),
                thumbnail=str(thumb_path),
                filename=result_path.name,
                caption=f"🎬 Kurban-Video: {context.user_data['donor_name']}",
                supports_streaming=True,
                duration=int(duration),
                width=width,
                height=height,
            )
            logger.info(f"Video an User {update.effective_user.id} gesendet")

            # Finaler Hinweis für das nächste Video
            await update.message.reply_text(
                "✨ Fertig! Sende /start um ein neues Video zu erstellen.",
                parse_mode="Markdown",
            )
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
                await context.bot.send_video(
                    chat_id=NOTIFY_USER_ID,
                    video=str(result_path),
                    thumbnail=str(thumb_path),
                    filename=result_path.name,
                    caption=f"🎬 Kurban-Video: {context.user_data['donor_name']}",
                    supports_streaming=True,
                    duration=int(duration),
                    width=width,
                    height=height,
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


# ══════════════════════════════════════════════════════════════════════════════
#  PDF-FLOW HANDLER
# ══════════════════════════════════════════════════════════════════════════════



async def pdf_enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Namen für PDF-Eintrag eingeben."""
    name = update.message.text.strip()

    if not name:
        await update.message.reply_text("❌ Der Name darf nicht leer sein. Bitte erneut eingeben:")
        return PDF_ENTER_NAME

    context.user_data["pdf_current_name"] = name
    entry_num = len(context.user_data["pdf_entries"]) + 1

    # Kurban-Typ Auswahl
    keyboard = ReplyKeyboardMarkup(
        [[t] for t in KURBAN_TYPES],
        one_time_keyboard=True,
        resize_keyboard=True,
    )

    await update.message.reply_text(
        f"👤 Name: *{name}*\n\n"
        f"Wähle den *Kurban-Typ* für Eintrag {entry_num}:",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    return PDF_CHOOSE_TYPE


async def pdf_choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Kurban-Typ auswählen."""
    kurban_type = update.message.text.strip()

    if kurban_type not in KURBAN_TYPES:
        keyboard = ReplyKeyboardMarkup(
            [[t] for t in KURBAN_TYPES],
            one_time_keyboard=True,
            resize_keyboard=True,
        )
        await update.message.reply_text(
            "❌ Ungültiger Typ. Bitte wähle eine der Optionen:",
            reply_markup=keyboard,
        )
        return PDF_CHOOSE_TYPE

    name = context.user_data["pdf_current_name"]
    context.user_data["pdf_entries"].append((name, kurban_type))
    context.user_data.pop("pdf_current_name", None)

    entry_count = len(context.user_data["pdf_entries"])

    await update.message.reply_text(
        f"✅ Eintrag {entry_count} gespeichert:\n"
        f"  {entry_count}. *{name.upper()}* — {kurban_type}",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )

    if entry_count >= 7:
        # Max erreicht → direkt zur Zusammenfassung
        await update.message.reply_text(
            "📋 Maximum von 7 Einträgen erreicht!",
        )
        return await _show_pdf_summary(update, context)

    # Weitere Namen?
    keyboard = ReplyKeyboardMarkup(
        [["➕ Weiteren Namen hinzufügen"], ["✅ Fertig – PDF erstellen"]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )

    await update.message.reply_text(
        f"Möchtest du einen weiteren Namen hinzufügen? ({entry_count}/7)",
        reply_markup=keyboard,
    )
    return PDF_MORE_NAMES


async def pdf_more_names(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Weitere Namen oder fertig."""
    text = update.message.text.strip()

    if text == "➕ Weiteren Namen hinzufügen":
        entry_count = len(context.user_data["pdf_entries"])
        await update.message.reply_text(
            f"✏️ Gib den *{entry_count + 1}. Namen* ein:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return PDF_ENTER_NAME

    elif text == "✅ Fertig – PDF erstellen":
        return await _show_pdf_summary(update, context)

    else:
        await update.message.reply_text("Bitte wähle eine der Optionen.")
        return PDF_MORE_NAMES


async def _show_pdf_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Zeigt die PDF-Zusammenfassung mit Korrekturmöglichkeit."""
    entries = context.user_data["pdf_entries"]

    lines = ["📋 *Zusammenfassung der Kurban-Liste:*\n"]
    for i, (name, kurban_type) in enumerate(entries):
        num = i + 1
        lines.append(f"  {num}. *{name.upper()}* — {kurban_type}")

    lines.append(f"\n📄 Datei: `Kurban_Liste.pdf`")

    buttons = [
        ["✅ PDF erstellen"],
        ["✏️ Eintrag bearbeiten"],
        ["🗑️ Eintrag löschen"],
    ]
    if len(entries) < 7:
        buttons.append(["➕ Eintrag hinzufügen"])
    buttons.append(["❌ Abbrechen"])

    keyboard = ReplyKeyboardMarkup(
        buttons,
        one_time_keyboard=True,
        resize_keyboard=True,
    )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    return PDF_CONFIRM


async def pdf_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: PDF-Zusammenfassung bestätigen, bearbeiten oder löschen."""
    text = update.message.text.strip()

    if text == "❌ Abbrechen":
        await update.message.reply_text(
            "❌ Abgebrochen. Sende /start um von vorne zu beginnen.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    elif text == "✅ PDF erstellen":
        return await _generate_and_send_pdf(update, context)

    elif text == "✏️ Eintrag bearbeiten":
        entries = context.user_data["pdf_entries"]

        buttons = []
        for i, (name, kurban_type) in enumerate(entries):
            num = i + 1
            buttons.append([f"{num}. {name.upper()} – {kurban_type}"])

        buttons.append(["↩️ Zurück"])

        keyboard = ReplyKeyboardMarkup(
            buttons,
            one_time_keyboard=True,
            resize_keyboard=True,
        )
        await update.message.reply_text(
            "✏️ Welchen Eintrag möchtest du bearbeiten?",
            reply_markup=keyboard,
        )
        return PDF_EDIT_CHOICE

    elif text == "🗑️ Eintrag löschen":
        entries = context.user_data["pdf_entries"]

        if len(entries) <= 1:
            await update.message.reply_text(
                "❌ Du musst mindestens einen Eintrag behalten.\n"
                "Sende /cancel um komplett abzubrechen."
            )
            return await _show_pdf_summary(update, context)

        buttons = []
        for i, (name, kurban_type) in enumerate(entries):
            num = i + 1
            buttons.append([f"🗑️ {num}. {name.upper()} – {kurban_type}"])

        buttons.append(["↩️ Zurück"])

        keyboard = ReplyKeyboardMarkup(
            buttons,
            one_time_keyboard=True,
            resize_keyboard=True,
        )
        await update.message.reply_text(
            "🗑️ Welchen Eintrag möchtest du löschen?",
            reply_markup=keyboard,
        )
        return PDF_EDIT_CHOICE

    elif text == "➕ Eintrag hinzufügen":
        entries = context.user_data["pdf_entries"]
        if len(entries) >= 7:
            await update.message.reply_text("❌ Maximum von 7 Einträgen bereits erreicht.")
            return await _show_pdf_summary(update, context)
        await update.message.reply_text(
            f"✏️ Gib den *{len(entries) + 1}. Namen* ein:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return PDF_ENTER_NAME

    else:
        await update.message.reply_text("Bitte wähle eine der Optionen.")
        return PDF_CONFIRM


async def pdf_edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Eintrag zum Bearbeiten/Löschen auswählen."""
    text = update.message.text.strip()

    if text == "↩️ Zurück":
        return await _show_pdf_summary(update, context)

    entries = context.user_data["pdf_entries"]


    # Löschen?
    if text.startswith("🗑️ "):
        # Index aus der Nummer extrahieren
        for i, (name, kurban_type) in enumerate(entries):
            num = i + 1
            expected = f"🗑️ {num}. {name.upper()} – {kurban_type}"
            if text == expected:
                removed = entries.pop(i)
                await update.message.reply_text(
                    f"🗑️ Eintrag gelöscht: {removed[0].upper()} – {removed[1]}",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return await _show_pdf_summary(update, context)

    # Bearbeiten
    for i, (name, kurban_type) in enumerate(entries):
        num = i + 1
        expected = f"{num}. {name.upper()} – {kurban_type}"
        if text == expected:
            context.user_data["pdf_edit_index"] = i
            await update.message.reply_text(
                f"✏️ Eintrag {num}: *{name.upper()}* – {kurban_type}\n\n"
                f"Gib den *neuen Namen* ein\n"
                f"_(oder sende /keep um den Namen beizubehalten):_",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove(),
            )
            return PDF_EDIT_NAME

    await update.message.reply_text("❌ Eintrag nicht gefunden. Bitte wähle erneut.")
    return await _show_pdf_summary(update, context)


async def pdf_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Bearbeiteten Namen eingeben."""
    text = update.message.text.strip()
    idx = context.user_data["pdf_edit_index"]
    entries = context.user_data["pdf_entries"]

    if text == "/keep":
        # Name beibehalten, nur Typ ändern
        context.user_data["pdf_edit_new_name"] = entries[idx][0]
    else:
        context.user_data["pdf_edit_new_name"] = text

    keyboard = ReplyKeyboardMarkup(
        [[t] for t in KURBAN_TYPES],
        one_time_keyboard=True,
        resize_keyboard=True,
    )

    await update.message.reply_text(
        f"Wähle den *neuen Kurban-Typ*\n"
        f"_(aktuell: {entries[idx][1]}):_",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    return PDF_EDIT_TYPE


async def pdf_edit_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler: Bearbeiteten Kurban-Typ auswählen."""
    kurban_type = update.message.text.strip()

    if kurban_type not in KURBAN_TYPES:
        keyboard = ReplyKeyboardMarkup(
            [[t] for t in KURBAN_TYPES],
            one_time_keyboard=True,
            resize_keyboard=True,
        )
        await update.message.reply_text(
            "❌ Ungültiger Typ. Bitte wähle eine der Optionen:",
            reply_markup=keyboard,
        )
        return PDF_EDIT_TYPE

    idx = context.user_data["pdf_edit_index"]
    new_name = context.user_data["pdf_edit_new_name"]
    entries = context.user_data["pdf_entries"]

    old_name, old_type = entries[idx]
    entries[idx] = (new_name, kurban_type)

    await update.message.reply_text(
        f"✅ Eintrag aktualisiert:\n"
        f"  Alt: {old_name.upper()} – {old_type}\n"
        f"  Neu: *{new_name.upper()}* – {kurban_type}",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )

    # Aufräumen
    context.user_data.pop("pdf_edit_index", None)
    context.user_data.pop("pdf_edit_new_name", None)

    return await _show_pdf_summary(update, context)


async def _generate_and_send_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generiert das PDF und sendet es an den User."""
    entries = context.user_data["pdf_entries"]


    await update.message.reply_text(
        "⏳ *PDF wird erstellt...*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )

    try:
        pdf_path = generate_kurban_pdf(
            entries=entries,
        )

        file_size = pdf_path.stat().st_size
        file_size_kb = file_size / 1024
        start_num = 1
        end_num = start_num + len(entries) - 1

        # PDF an User senden
        with open(str(pdf_path), "rb") as pdf_file:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=pdf_file,
                filename=pdf_path.name,
                caption=(
                    f"📄 Kurban-Liste erstellt!\n"
                    f"🔢 Nummern: {start_num}–{end_num}\n"
                    f"👥 Einträge: {len(entries)}\n"
                    f"📦 Größe: {file_size_kb:.0f} KB"
                ),
            )

        logger.info(f"PDF an User {update.effective_user.id} gesendet: {pdf_path.name}")

        # PDF auch an NOTIFY_USER senden
        if NOTIFY_USER_ID:
            try:
                with open(str(pdf_path), "rb") as pdf_file:
                    await context.bot.send_document(
                        chat_id=NOTIFY_USER_ID,
                        document=pdf_file,
                        filename=pdf_path.name,
                        caption=(
                            f"🔔 Neue Kurban-Liste erstellt!\n"
                            f"🔢 Nummern: {start_num}–{end_num}\n"
                            f"👥 Einträge: {len(entries)}"
                        ),
                    )
            except Exception as e:
                logger.error(f"PDF-Benachrichtigung an NOTIFY_USER fehlgeschlagen: {e}")

        await update.message.reply_text(
            "✨ Fertig! Sende /start um eine neue Automatisierung zu starten.",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"PDF-Generierung fehlgeschlagen: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ *Fehler bei der PDF-Erstellung:*\n\n`{str(e)}`\n\n"
            "Bitte versuche es erneut mit /start.",
            parse_mode="Markdown",
        )

    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  ALLGEMEINE HANDLER
# ══════════════════════════════════════════════════════════════════════════════

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
        "/start – Neues Kurban-Video oder PDF erstellen\n"
        "/cancel – Aktuellen Vorgang abbrechen\n"
        "/help – Diese Hilfe anzeigen\n\n"
        "*🎬 Video-Flow:*\n"
        "1️⃣ Flyer-Bild senden\n"
        "2️⃣ Spendername bestätigen\n"
        "3️⃣ Opfertier-Bild senden (oder /skip)\n"
        "4️⃣ Schlachtungsvideo senden\n"
        "5️⃣ Verteilungsvideo senden (oder /skip)\n"
        "6️⃣ Video wird automatisch erstellt! 🎬\n\n"
        "*📄 PDF-Listen-Flow:*\n"
        "1️⃣ Namen eingeben (max. 7)\n"
        "2️⃣ Kurban-Typ wählen\n"
        "3️⃣ Zusammenfassung prüfen/korrigieren\n"
        "4️⃣ PDF wird automatisch erstellt! 📄",
        parse_mode="Markdown",
    )


def get_conversation_handler() -> ConversationHandler:
    """Erstellt und gibt den Konversations-Handler zurück."""
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            # Gemeinsam: Auswahl
            CHOOSE_AUTOMATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_automation),
            ],

            # Video-Flow
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

            # PDF-Flow
            PDF_ENTER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pdf_enter_name),
            ],
            PDF_CHOOSE_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pdf_choose_type),
            ],
            PDF_MORE_NAMES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pdf_more_names),
            ],
            PDF_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pdf_confirm),
            ],
            PDF_EDIT_CHOICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pdf_edit_choice),
            ],
            PDF_EDIT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pdf_edit_name),
                CommandHandler("keep", pdf_edit_name),
            ],
            PDF_EDIT_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pdf_edit_type),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
