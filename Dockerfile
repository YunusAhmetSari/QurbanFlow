# ── QurbanFlow – Docker Image ────────────────────────────────────────────────
# Python 3.11 + FFmpeg für Video-Assembly
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# FFmpeg installieren (benötigt für moviepy/Video-Rendering)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Arbeitsverzeichnis
WORKDIR /app

# Dependencies zuerst (Docker-Caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Projektdateien kopieren
COPY config.py .
COPY bot/ bot/
COPY core/ core/
COPY Vorlagen/ Vorlagen/

# Spender-Verzeichnis erstellen (wird als Volume gemountet)
RUN mkdir -p /app/Spender

# Virtual Environment in PATH aufnehmen
ENV PATH="/app/.venv/bin:$PATH"

# Bot starten
CMD ["python", "-m", "bot.telegram_bot"]
