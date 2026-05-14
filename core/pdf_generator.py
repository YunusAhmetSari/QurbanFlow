"""
QurbanFlow – Kurban-Listen PDF-Generator

Erstellt PDF-Zertifikate mit bis zu 7 Spendernamen auf der Kurban-Vorlage.
Jeder Eintrag enthält: Laufende Nummer, Name (UPPERCASE), Kurban-Typ im Badge.

Features:
- Nummerierung von 1 bis 7 pro PDF
- Statistik-Tracking pro Kurban-Typ
- Historien-Log aller generierten PDFs
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

from PIL import Image, ImageDraw, ImageFont

from config import (
    KURBAN_VORLAGE,
    KURBAN_HISTORY_FILE,
    KURBAN_STATS_FILE,
    KURBAN_TYPES,
    FONTS_DIR,
    PDFS_DIR,
)

logger = logging.getLogger(__name__)

# ── Schrift-Setup ────────────────────────────────────────────────────────────

FONT_BOLD_PATH = FONTS_DIR / "Montserrat-Bold.ttf"

# Fallback-Schriftpfade für Windows
_SYSTEM_FONT_PATHS = [
    Path("C:/Windows/Fonts/arialbd.ttf"),     # Arial Bold
    Path("C:/Windows/Fonts/calibrib.ttf"),     # Calibri Bold
    Path("C:/Windows/Fonts/verdanab.ttf"),     # Verdana Bold
]


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Lädt Montserrat Bold oder Fallback-Schrift."""
    if FONT_BOLD_PATH.exists():
        return ImageFont.truetype(str(FONT_BOLD_PATH), size)

    for fallback in _SYSTEM_FONT_PATHS:
        if fallback.exists():
            logger.warning(f"Montserrat-Bold nicht gefunden, verwende {fallback.name}")
            return ImageFont.truetype(str(fallback), size)

    logger.warning("Keine passende Schriftart gefunden, verwende Standard")
    return ImageFont.load_default()


# ── Statistik-Tracking ───────────────────────────────────────────────────────


def update_statistics(entries: List[Tuple[str, str]]) -> dict:
    """
    Aktualisiert die Statistik pro Kurban-Typ.

    Args:
        entries: Liste von (name, kurban_type) Tupeln

    Returns:
        Aktualisierte Statistik als Dict
    """
    stats = {}
    if KURBAN_STATS_FILE.exists():
        try:
            stats = json.loads(KURBAN_STATS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            stats = {}

    # Grundstruktur sicher stellen
    if "total_pdfs" not in stats:
        stats["total_pdfs"] = 0
    if "total_entries" not in stats:
        stats["total_entries"] = 0
    if "per_type" not in stats:
        stats["per_type"] = {}

    stats["total_pdfs"] += 1
    stats["total_entries"] += len(entries)
    stats["last_generated"] = datetime.now().isoformat()

    for _, kurban_type in entries:
        stats["per_type"][kurban_type] = stats["per_type"].get(kurban_type, 0) + 1

    KURBAN_STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    KURBAN_STATS_FILE.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Statistik aktualisiert: {stats['total_pdfs']} PDFs, {stats['total_entries']} Einträge")
    return stats


def get_statistics() -> dict:
    """Liest die aktuelle Statistik."""
    if not KURBAN_STATS_FILE.exists():
        return {"total_pdfs": 0, "total_entries": 0, "per_type": {}}
    try:
        return json.loads(KURBAN_STATS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"total_pdfs": 0, "total_entries": 0, "per_type": {}}


# ── Historien-Log ────────────────────────────────────────────────────────────

def log_history(
    entries: List[Tuple[str, str]],
    pdf_filename: str,
) -> None:
    """
    Protokolliert eine PDF-Generierung im Historien-Log.

    Args:
        entries: Liste von (name, kurban_type) Tupeln
        pdf_filename: Name der PDF-Datei
    """
    history = []
    start_number = 1
    if KURBAN_HISTORY_FILE.exists():
        try:
            history = json.loads(KURBAN_HISTORY_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            history = []

    record = {
        "timestamp": datetime.now().isoformat(),
        "pdf_file": pdf_filename,
        "start_number": start_number,
        "end_number": start_number + len(entries) - 1,
        "entries": [
            {"number": start_number + i, "name": name, "type": kurban_type}
            for i, (name, kurban_type) in enumerate(entries)
        ],
    }
    history.append(record)

    KURBAN_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    KURBAN_HISTORY_FILE.write_text(
        json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(f"Historien-Eintrag gespeichert: {pdf_filename}")


# ── PDF-Generierung ─────────────────────────────────────────────────────────

def _draw_badge(
    draw: ImageDraw.Draw,
    text: str,
    center_x: int,
    center_y: int,
    font: ImageFont.FreeTypeFont,
    fixed_w: int = 0,
    fixed_h: int = 0,
) -> None:
    """
    Zeichnet einen dekorativen Badge (Rahmen mit geschweiften Klammern)
    um den Kurban-Typ-Text.

    Wenn fixed_w/fixed_h angegeben, werden alle Badges gleich groß.
    """
    bbox = font.getbbox(text)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Badge-Abmessungen (fest oder dynamisch)
    badge_w = fixed_w if fixed_w else text_w + 56
    badge_h = fixed_h if fixed_h else text_h + 24

    x1 = center_x - badge_w // 2
    y1 = center_y - badge_h // 2
    x2 = center_x + badge_w // 2
    y2 = center_y + badge_h // 2

    # Abgerundeter Rahmen
    draw.rounded_rectangle(
        [x1, y1, x2, y2],
        radius=8,
        outline=(30, 30, 30),
        width=3,
    )

    # Dekorative Spitzen (geschweifte Klammern links/rechts)
    arrow_size = 10
    draw.polygon(
        [(x1 - arrow_size, center_y), (x1, center_y - arrow_size), (x1, center_y + arrow_size)],
        fill=(30, 30, 30),
    )
    draw.polygon(
        [(x2 + arrow_size, center_y), (x2, center_y - arrow_size), (x2, center_y + arrow_size)],
        fill=(30, 30, 30),
    )

    # Text zentriert im Badge
    text_x = center_x - text_w // 2
    text_y = center_y - text_h // 2 - bbox[1]
    draw.text((text_x, text_y), text, fill=(30, 30, 30), font=font)


def _draw_separator(
    draw: ImageDraw.Draw,
    y: int,
    left_x: int,
    right_x: int,
    center_x: int,
) -> None:
    """Zeichnet eine Trennlinie mit Diamant-Symbol in der Mitte."""
    line_color = (180, 170, 140)  # Goldlich/Beige wie im Beispiel
    diamond_size = 6

    # Linie links
    draw.line([(left_x, y), (center_x - 20, y)], fill=line_color, width=1)
    # Linie rechts
    draw.line([(center_x + 20, y), (right_x, y)], fill=line_color, width=1)

    # Diamant in der Mitte
    draw.polygon(
        [
            (center_x, y - diamond_size),
            (center_x + diamond_size, y),
            (center_x, y + diamond_size),
            (center_x - diamond_size, y),
        ],
        fill=line_color,
        outline=(160, 150, 120),
    )


def _draw_name_entry(
    draw: ImageDraw.Draw,
    name: str,
    name_x: int,
    center_y: int,
    font: ImageFont.FreeTypeFont,
    font_size: int,
) -> None:
    """
    Zeichnet einen Namen in ein oder zwei Zeilen.

    Erste Zeile: Vorname(n), Zweite Zeile: Nachname.
    Der letzte Namensteil ist immer der Nachname.
    Schriftgröße ist für alle Einträge gleich (vorab berechnet).
    """
    text_color = (30, 30, 30)
    name_upper = name.upper()
    parts = name_upper.split()

    if len(parts) <= 1:
        # Einzelner Name → eine Zeile
        draw.text(
            (name_x, center_y - font_size // 2),
            name_upper,
            fill=text_color,
            font=font,
        )
    else:
        # Mehrteiliger Name → Zeile 1: Vorname(n), Zeile 2: Nachname
        first_names = " ".join(parts[:-1])
        last_name = parts[-1]

        line_gap = 4
        total_text_h = font_size * 2 + line_gap
        top_y = center_y - total_text_h // 2

        draw.text((name_x, top_y), first_names, fill=text_color, font=font)
        draw.text((name_x, top_y + font_size + line_gap), last_name, fill=text_color, font=font)


def generate_kurban_pdf(
    entries: List[Tuple[str, str]],
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generiert ein Kurban-Listen-PDF basierend auf der Vorlage.

    Args:
        entries: Liste von (name, kurban_type) Tupeln (max 7)
        output_path: Pfad für die PDF-Datei (optional, wird automatisch generiert)

    Returns:
        Pfad zur generierten PDF-Datei

    Raises:
        FileNotFoundError: Wenn die Vorlage fehlt
        ValueError: Wenn mehr als 7 Einträge oder ungültiger Typ
    """
    # Validierung
    if not KURBAN_VORLAGE.exists():
        raise FileNotFoundError(f"Kurban-Vorlage nicht gefunden: {KURBAN_VORLAGE}")

    if len(entries) > 7:
        raise ValueError("Maximal 7 Einträge pro PDF erlaubt.")

    if len(entries) == 0:
        raise ValueError("Mindestens ein Eintrag erforderlich.")

    for name, kurban_type in entries:
        if kurban_type not in KURBAN_TYPES:
            raise ValueError(
                f"Ungültiger Kurban-Typ: '{kurban_type}'. "
                f"Erlaubt: {', '.join(KURBAN_TYPES)}"
            )

    start_number = 1
    logger.info(f"PDF-Generierung gestartet: {len(entries)} Einträge")

    # ── Bild laden ───────────────────────────────────────────────────────
    img = Image.open(str(KURBAN_VORLAGE)).convert("RGB")
    draw = ImageDraw.Draw(img)

    img_w, img_h = img.size
    logger.info(f"Vorlage geladen: {img_w}x{img_h}")

    # ── Basis-Schriftgrößen (relativ zur Bildgröße) ─────────────────────
    number_font_size = int(img_h * 0.04)
    base_name_font_size = int(img_h * 0.038)
    badge_font_size = int(img_h * 0.028)

    # ── Layout-Berechnung ────────────────────────────────────────────────
    header_end_y = int(img_h * 0.32)
    footer_start_y = int(img_h * 0.96)
    available_h = footer_start_y - header_end_y
    row_height = available_h // 7

    # Feste Lücken
    gap_num_name = int(img_w * 0.03)   # Lücke zwischen Nummer und Name
    gap_name_badge = int(img_w * 0.03) # Lücke zwischen Name und Badge

    # Horizontale Positionen (aligned mit Vorlage)
    # Nummer: links aligned mit "T" von TÜRKİYE (≈ 3%)
    number_x = int(img_w * 0.06)
    # Rechte Kante: aligned mit letztem "A" von TANZANYA (≈ 97%)
    badge_right_edge = int(img_w * 0.95)
    # Trennlinien-Bereich
    margin_left = number_x
    margin_right = badge_right_edge

    text_color = (30, 30, 30)

    # ── Einheitliche Badge-Größe berechnen (basierend auf breitstem Typ)
    badge_font = _get_font(badge_font_size)
    badge_pad_x = 28
    badge_pad_y = 12
    max_type_w = 0
    max_type_h = 0
    for typ in KURBAN_TYPES:
        bbox = badge_font.getbbox(typ)
        max_type_w = max(max_type_w, bbox[2] - bbox[0])
        max_type_h = max(max_type_h, bbox[3] - bbox[1])
    badge_w = max_type_w + badge_pad_x * 2
    badge_h = max_type_h + badge_pad_y * 2
    arrow_size = 10

    # Badge-Zentrum: rechte Kante (Box + Pfeil) = badge_right_edge
    badge_center_x = badge_right_edge - arrow_size - badge_w // 2

    # ── Nummern-Breite berechnen ─────────────────────────────────────────
    number_font = _get_font(number_font_size)
    max_num_text = f"{start_number + len(entries) - 1}."
    num_bbox = number_font.getbbox(max_num_text)
    max_num_w = num_bbox[2] - num_bbox[0]

    # Name beginnt nach Nummer + Lücke
    name_x = number_x + max_num_w + gap_num_name

    # Verfügbare Breite für Namen = bis Badge-Linke-Kante - Pfeil - Lücke
    badge_left_edge = badge_center_x - badge_w // 2 - arrow_size
    max_name_width = badge_left_edge - name_x - gap_name_badge

    # ── Einheitliche Namensgröße berechnen (passt für längsten Namen) ───
    name_font_size = base_name_font_size
    name_font = _get_font(name_font_size)
    while name_font_size > 14:
        fits = True
        for name, _ in entries:
            parts = name.upper().split()
            if len(parts) <= 1:
                line = name.upper()
            else:
                first_line = " ".join(parts[:-1])
                last_line = parts[-1]
                line = first_line if len(first_line) >= len(last_line) else last_line
            bbox = name_font.getbbox(line)
            if (bbox[2] - bbox[0]) > max_name_width:
                fits = False
                break
        if fits:
            break
        name_font_size -= 2
        name_font = _get_font(name_font_size)

    logger.info(f"Layout: Namensgröße={name_font_size}, Badge={badge_w}x{badge_h}")

    # ── Einträge zeichnen ────────────────────────────────────────────────
    for i in range(7):
        row_y = header_end_y + i * row_height
        text_center_y = row_y + row_height // 2

        if i < len(entries):
            name, kurban_type = entries[i]
            current_number = start_number + i

            # Nummer zeichnen
            num_text = f"{current_number}."
            draw.text(
                (number_x, text_center_y - number_font_size // 2),
                num_text,
                fill=text_color,
                font=number_font,
            )

            # Name zeichnen (einheitliche Schriftgröße, ggf. zweizeilig)
            _draw_name_entry(
                draw, name, name_x, text_center_y,
                name_font, name_font_size,
            )

            # Badge mit Kurban-Typ (einheitliche Größe)
            _draw_badge(
                draw, kurban_type, badge_center_x, text_center_y,
                badge_font, fixed_w=badge_w, fixed_h=badge_h,
            )

        # Trennlinie (nur zwischen Einträgen, nicht nach dem letzten)
        if i < 6:
            separator_y = row_y + row_height
            _draw_separator(
                draw, separator_y,
                margin_left, margin_right,
                img_w // 2,
            )

    # ── PDF speichern ────────────────────────────────────────────────────
    if output_path is None:
        PDFS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = PDFS_DIR / f"Kurban_Liste_{timestamp}.pdf"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Pillow kann direkt als PDF speichern
    img.save(str(output_path), "PDF", resolution=150.0)
    logger.info(f"PDF gespeichert: {output_path}")

    # ── Statistik und History aktualisieren ──────────────────────
    update_statistics(entries)
    log_history(entries, output_path.name)

    return output_path


def get_stats_text() -> str:
    """Formatiert die Statistik als lesbaren Text für den Bot."""
    stats = get_statistics()

    if stats["total_pdfs"] == 0:
        return "📊 Noch keine PDFs erstellt."

    lines = [
        "📊 *Kurban-Listen Statistik:*\n",
        f"📄 PDFs erstellt: {stats['total_pdfs']}",
        f"👥 Einträge gesamt: {stats['total_entries']}",
    ]

    if stats.get("per_type"):
        lines.append("\n📋 *Pro Kurban-Typ:*")
        for typ, count in sorted(stats["per_type"].items()):
            lines.append(f"  • {typ}: {count}")

    if stats.get("last_generated"):
        try:
            dt = datetime.fromisoformat(stats["last_generated"])
            lines.append(f"\n🕐 Zuletzt: {dt.strftime('%d.%m.%Y %H:%M')}")
        except ValueError:
            pass

    return "\n".join(lines)
