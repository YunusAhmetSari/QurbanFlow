"""
QurbanFlow – Audio-Verarbeitung

Funktionen für:
- Lautstärke-Normalisierung
- Song-Overlay über Video-Clips
- Audio Fade-In/Fade-Out
"""

import logging
from pathlib import Path
from typing import Optional

from pydub import AudioSegment

from config import TARGET_DBFS, AUDIO_FADE_DURATION

logger = logging.getLogger(__name__)


def normalize_audio_file(input_path: Path, output_path: Optional[Path] = None) -> Path:
    """
    Normalisiert die Lautstärke einer Audiodatei.

    Args:
        input_path: Pfad zur Eingabe-Audiodatei
        output_path: Pfad für die Ausgabe (optional, überschreibt Eingabe wenn None)

    Returns:
        Pfad zur normalisierten Audiodatei
    """
    if output_path is None:
        output_path = input_path

    audio = AudioSegment.from_file(str(input_path))

    # Normalisierung auf Ziel-dBFS
    change_in_dbfs = TARGET_DBFS - audio.dBFS
    normalized = audio.apply_gain(change_in_dbfs)

    # Exportformat anhand der Dateiendung
    export_format = output_path.suffix.lstrip(".").lower()
    if export_format == "mp3":
        normalized.export(str(output_path), format="mp3")
    else:
        normalized.export(str(output_path), format="wav")

    logger.info(
        f"Audio normalisiert: {input_path.name} "
        f"({audio.dBFS:.1f} dBFS → {TARGET_DBFS:.1f} dBFS)"
    )
    return output_path


def extract_audio_from_video(video_path: Path, output_path: Path) -> Path:
    """
    Extrahiert die Audiospur aus einem Video als WAV-Datei.

    Args:
        video_path: Pfad zum Video
        output_path: Pfad für die Audio-Ausgabe (.wav)

    Returns:
        Pfad zur extrahierten Audiodatei
    """
    audio = AudioSegment.from_file(str(video_path))
    audio.export(str(output_path), format="wav")
    logger.info(f"Audio extrahiert: {video_path.name} → {output_path.name}")
    return output_path


def get_audio_duration_ms(audio_path: Path) -> int:
    """Gibt die Dauer einer Audiodatei in Millisekunden zurück."""
    audio = AudioSegment.from_file(str(audio_path))
    return len(audio)


def apply_fade(
    audio: AudioSegment,
    fade_in_ms: Optional[int] = None,
    fade_out_ms: Optional[int] = None,
) -> AudioSegment:
    """
    Wendet Fade-In und/oder Fade-Out auf ein AudioSegment an.

    Args:
        audio: AudioSegment zum Bearbeiten
        fade_in_ms: Fade-In Dauer in ms (None = Standard aus Config)
        fade_out_ms: Fade-Out Dauer in ms (None = Standard aus Config)

    Returns:
        AudioSegment mit Fade-Effekten
    """
    default_fade = int(AUDIO_FADE_DURATION * 1000)

    if fade_in_ms is None:
        fade_in_ms = default_fade
    if fade_out_ms is None:
        fade_out_ms = default_fade

    if fade_in_ms > 0:
        audio = audio.fade_in(fade_in_ms)
    if fade_out_ms > 0:
        audio = audio.fade_out(fade_out_ms)

    return audio


def create_silent_audio(duration_ms: int, sample_rate: int = 44100) -> AudioSegment:
    """Erstellt ein stilles AudioSegment mit gegebener Dauer."""
    return AudioSegment.silent(duration=duration_ms, frame_rate=sample_rate)
