"""
QurbanFlow – Video-Assembly-Pipeline

Baut das fertige Kurban-Video nach festem Schema zusammen:

Videospur: 
   1. Flyer (Bild → Still-Video)     | Audio: Song A (Start)
   2. Afrika-Clip (fest)              | Audio: Song A (Mitte)
   3. [Optional] Opfertier+Flyer (Bild → Still)  | Audio: Song A (Ende)
   4. Schlachtungsvideo               | Audio: Original
   5. [Optional] Verteilungsvideo     | Audio: Original
   6. Danke-Clip (fest)               | Audio: Song B

Alle Clips werden auf eine einheitliche Zielauflösung normalisiert
(Scale + Pad), damit keine schwarzen Ränder entstehen.
Song A wird auf 10s (ohne Opfertier) oder 15s (mit Opfertier) gekürzt.
Clip 3 (Opfertier) und Clip 5 (Verteilung) sind optional.
"""

import logging
from pathlib import Path
from typing import Optional


from moviepy.editor import (
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    concatenate_videoclips,
)

from config import (
    AFRICA_CLIP,
    THANKS_CLIP,
    SONG_A,
    SONG_B,
    FLYER_STILL_DURATION,
    ANIMAL_STILL_DURATION,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_FPS,
)

logger = logging.getLogger(__name__)

# Zielauflösung für alle Clips
TARGET_W = VIDEO_WIDTH
TARGET_H = VIDEO_HEIGHT


def _validate_assets():
    """Prüft ob alle festen Assets vorhanden sind."""
    missing = []
    for asset in [AFRICA_CLIP, THANKS_CLIP, SONG_A, SONG_B]:
        if not asset.exists():
            missing.append(str(asset))

    if missing:
        raise FileNotFoundError(
            "Fehlende Assets:\n" + "\n".join(f"  - {m}" for m in missing)
        )


def _normalize_clip(clip, target_w=TARGET_W, target_h=TARGET_H):
    """Normalisiert einen Clip auf die Zielauflösung (Scale + Pad).
    
    1. Skaliert den Clip so, dass er in die Zielauflösung passt 
       (Aspect Ratio bleibt erhalten).
    2. Zentriert den skalierten Clip auf einem schwarzen Hintergrund
       der Zielauflösung.
    """
    clip_w, clip_h = clip.size

    # Skalierungsfaktor berechnen (fit within target, keep aspect ratio)
    scale = min(target_w / clip_w, target_h / clip_h)
    new_w = int(clip_w * scale)
    new_h = int(clip_h * scale)

    # Skalieren
    scaled = clip.resize(newsize=(new_w, new_h))

    # Auf schwarzem Hintergrund zentrieren (Padding)
    bg = ColorClip(size=(target_w, target_h), color=(0, 0, 0))
    bg = bg.set_duration(clip.duration).set_fps(VIDEO_FPS)

    x_offset = (target_w - new_w) // 2
    y_offset = (target_h - new_h) // 2

    result = CompositeVideoClip(
        [bg, scaled.set_position((x_offset, y_offset))],
        size=(target_w, target_h),
    )
    # Audio übertragen falls vorhanden
    if clip.audio is not None:
        result = result.set_audio(clip.audio)

    return result


def _make_still_clip(image_path: Path, duration: float) -> ImageClip:
    """Erstellt einen normalisierten Still-Video-Clip aus einem Bild."""
    clip = (
        ImageClip(str(image_path))
        .set_duration(duration)
        .set_fps(VIDEO_FPS)
    )
    return _normalize_clip(clip)


def _preprocess_video(input_path: Path) -> Path:
    """
    Konvertiert Smartphone-Videos (z.B. iPhone 10-bit HEVC) über das System-FFmpeg
    in ein standardisiertes Format (H.264, yuv420p). Behebt MoviePy Lese-Fehler.
    """
    import subprocess
    
    if not input_path.exists() or input_path.stat().st_size == 0:
        raise ValueError(f"Videodatei {input_path.name} ist leer oder fehlt.")
        
    output_path = input_path.with_stem(input_path.stem + "_fixed")
    
    logger.info(f"Führe Pre-Processing für {input_path.name} durch (Stabilität/H264)...")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(input_path),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-preset", "ultrafast",
            "-crf", "23",
            str(output_path)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg Pre-Processing fehlgeschlagen für {input_path}: {e}")
        # Wenn es fehlschlägt, versuchen wir es mit dem Original weiter
        return input_path

def assemble_video(
    flyer_image: Path,
    animal_image: Optional[Path],
    slaughter_video: Path,
    distribution_video: Optional[Path],
    output_path: Path,
) -> Path:
    """
    Baut das komplette Kurban-Video zusammen.

    Alle Clips werden auf VIDEO_WIDTH x VIDEO_HEIGHT normalisiert
    (Scale + Pad mit schwarzem Hintergrund).

    Args:
        flyer_image: Pfad zum Flyer-Bild
        animal_image: Pfad zum Opfertier+Flyer-Bild (Optional, None = skip)
        slaughter_video: Pfad zum Schlachtungsvideo
        distribution_video: Pfad zum Verteilungsvideo (Optional, None = skip)
        output_path: Pfad für das fertige Video

    Returns:
        Pfad zum gerenderten Video

    Raises:
        FileNotFoundError: Wenn Assets oder Medien fehlen
    """
    _validate_assets()

    # Eingabedateien prüfen
    for media in [flyer_image, slaughter_video]:
        if not media.exists():
            raise FileNotFoundError(f"Mediendatei nicht gefunden: {media}")

    if animal_image and not animal_image.exists():
        raise FileNotFoundError(f"Opfertier-Bild nicht gefunden: {animal_image}")

    if distribution_video and not distribution_video.exists():
        raise FileNotFoundError(f"Verteilungsvideo nicht gefunden: {distribution_video}")

    logger.info("=== Video-Assembly gestartet ===")
    logger.info(f"Zielauflösung: {TARGET_W}x{TARGET_H} @ {VIDEO_FPS}fps")

    clips_to_close = []

    try:
        # ── Clip 1: Flyer (Still-Bild) ─────────────────────────────────────
        logger.info(f"Clip 1: Flyer-Bild ({FLYER_STILL_DURATION}s)")
        clip1 = _make_still_clip(flyer_image, FLYER_STILL_DURATION)
        clips_to_close.append(clip1)

        # ── Clip 2: Afrika-Clip (fest) ──────────────────────────────────────
        logger.info("Clip 2: Afrika-Clip")
        clip2_raw = VideoFileClip(str(AFRICA_CLIP)).subclip(0, 5)
        clip2 = _normalize_clip(clip2_raw)
        clips_to_close.append(clip2_raw)
        clips_to_close.append(clip2)

        # ── Clip 3: Opfertier+Flyer (Still-Bild, Optional) ──────────────────
        if animal_image:
            logger.info(f"Clip 3: Opfertier-Bild ({ANIMAL_STILL_DURATION}s)")
            clip3 = _make_still_clip(animal_image, ANIMAL_STILL_DURATION)
            clips_to_close.append(clip3)
        else:
            logger.info("Clip 3: Übersprungen (Kein Opfertier-Bild)")
            clip3 = None

        # ── Clip 4: Schlachtungsvideo ────────────────────────────────────────
        logger.info("Clip 4: Schlachtungsvideo")
        slaughter_fixed = _preprocess_video(slaughter_video)
        clip4_raw = VideoFileClip(str(slaughter_fixed))
        clip4 = _normalize_clip(clip4_raw)
        clips_to_close.append(clip4_raw)
        clips_to_close.append(clip4)

        # ── Clip 5: Verteilungsvideo (Optional) ─────────────────────────────
        if distribution_video:
            logger.info("Clip 5: Verteilungsvideo")
            dist_fixed = _preprocess_video(distribution_video)
            clip5_raw = VideoFileClip(str(dist_fixed))
            clip5 = _normalize_clip(clip5_raw)
            clips_to_close.append(clip5_raw)
            clips_to_close.append(clip5)
        else:
            logger.info("Clip 5: Übersprungen (Kein Verteilungsvideo)")
            clip5 = None

        # ── Clip 6: Danke-Clip (fest) ───────────────────────────────────────
        logger.info("Clip 6: Danke-Clip")
        clip6_raw = VideoFileClip(str(THANKS_CLIP))
        clip6 = _normalize_clip(clip6_raw)
        clips_to_close.append(clip6_raw)
        clips_to_close.append(clip6)

        # ── Audio-Setup ─────────────────────────────────────────────────────

        # Song A: läuft über Clips 1-2 (ohne Opfertier) oder 1-3 (mit Opfertier)
        song_a_clips = [clip1, clip2]
        if clip3:
            song_a_clips.append(clip3)

        duration_song_a_clips = sum(c.duration for c in song_a_clips)
        logger.info(f"Song A Dauer: {duration_song_a_clips:.1f}s (Clips 1-{'3' if clip3 else '2'})")

        song_a = AudioFileClip(str(SONG_A))
        clips_to_close.append(song_a)

        # Song A begrenzen: 10s ohne Opfertier (5s Flyer + 5s Afrika),
        # 15s mit Opfertier (5s Flyer + 5s Afrika + 5s Tier)
        MAX_SONG_A_DURATION = 15.0 if clip3 else 10.0
        if song_a.duration > MAX_SONG_A_DURATION:
            song_a = song_a.subclip(0, MAX_SONG_A_DURATION)

        # Song A aufteilen (für jeden Clip)
        t1 = clip1.duration
        t2 = clip1.duration + clip2.duration

        song_a_part1 = song_a.subclip(0, t1)
        song_a_part2 = song_a.subclip(t1, min(t2, song_a.duration))

        # Clips mit Song A Audio versehen
        clip1 = clip1.set_audio(song_a_part1)
        clip2 = clip2.set_audio(song_a_part2)

        if clip3:
            song_a_part3 = song_a.subclip(t2, min(duration_song_a_clips, song_a.duration))
            clip3 = clip3.set_audio(song_a_part3)

        # Clip 4 & 5: Original-Audio behalten

        # Song B: läuft über Clip 6
        song_b = AudioFileClip(str(SONG_B))
        clips_to_close.append(song_b)

        if song_b.duration > clip6.duration:
            song_b = song_b.subclip(0, clip6.duration)

        clip6 = clip6.set_audio(song_b)

        # ── Zusammenfügen ───────────────────────────────────────────────────
        logger.info("Videos werden zusammengefügt...")
        
        final_clips = [clip1, clip2]
        if clip3:
            final_clips.append(clip3)
        final_clips.append(clip4)
        if clip5:
            final_clips.append(clip5)
        final_clips.append(clip6)

        final = concatenate_videoclips(
            final_clips,
            method="compose",
        )
        clips_to_close.append(final)

        total_duration = final.duration
        logger.info(f"Gesamtdauer: {total_duration:.1f}s")

        # ── Rendering ───────────────────────────────────────────────────────
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_file = str(output_path)

        # Thumbnail erstellen (Frame bei 1 Sekunde - meistens der Flyer)
        thumb_path = output_path.with_suffix(".jpg")
        logger.info(f"Thumbnail wird generiert: {thumb_path}")
        
        from PIL import Image
        import numpy as np
        
        frame = final.get_frame(1.0)
        # Falls der Frame tranparent ist (RGBA), Alpha-Kanal entfernen (RGB)
        if isinstance(frame, np.ndarray) and frame.ndim == 3 and frame.shape[2] == 4:
            frame = frame[:, :, :3]
            
        Image.fromarray(frame).save(str(thumb_path), format="JPEG")

        logger.info(f"Rendering nach: {output_file}")
        final.write_videofile(
            output_file,
            fps=VIDEO_FPS,
            codec="libx264",
            audio_codec="aac",
            bitrate="3000k",
            audio_bitrate="192k",
            preset="ultrafast",
            threads=2,
            ffmpeg_params=["-movflags", "+faststart"],
            logger=None,
        )

        logger.info(f"=== Video fertig: {output_file} ===")
        return output_path, thumb_path, total_duration, TARGET_W, TARGET_H

    finally:
        # Alle Clips sauber schließen
        for clip in clips_to_close:
            try:
                clip.close()
            except Exception:
                pass
