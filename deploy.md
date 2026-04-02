# 🚀 QurbanFlow – Cloud-Deployment (Hetzner)

Schritt-für-Schritt Anleitung: QurbanFlow auf einem Hetzner Cloud Server deployen,
mit dem lokalen Telegram Bot API Server für Dateien bis **2 GB**.

---

## 1. Voraussetzungen

Du brauchst:

- **Telegram Bot Token** von [@BotFather](https://t.me/BotFather)
- **Telegram API Credentials** von [my.telegram.org](https://my.telegram.org):
  1. Einloggen mit deiner Telefonnummer
  2. „API Development Tools" auswählen
  3. `API ID` und `API Hash` notieren
- **Hetzner Cloud Account** ([cloud.hetzner.com](https://cloud.hetzner.com))

---

## 2. Hetzner Server erstellen

1. Im [Hetzner Cloud Console](https://console.hetzner.cloud):
   - **Neues Projekt** erstellen (z.B. „QurbanFlow")
   - **Server hinzufügen**:
     - Location: **Falkenstein** (günstigster EU-Standort)
     - Image: **Ubuntu 24.04**
     - Typ: **CX23** (2 vCPU, 4 GB RAM, 40 GB SSD, 20 TB Traffic)
     - SSH-Key hinzufügen (empfohlen) oder Passwort setzen

2. Server-IP notieren (z.B. `65.21.xxx.xxx`)

---

## 3. Server einrichten

Per SSH verbinden:

```bash
ssh root@DEINE_SERVER_IP
```

### Docker installieren

```bash
# Docker installieren (offizielles Skript)
curl -fsSL https://get.docker.com | sh

# Docker Compose Plugin ist automatisch dabei
docker compose version
```

### Projekt auf den Server kopieren

Auf deinem **lokalen Rechner** (nicht auf dem Server):

```bash
# Git-Repository klonen (oder per SCP kopieren)
scp -r . root@DEINE_SERVER_IP:/opt/qurbanflow
```

Oder auf dem **Server** direkt:

```bash
# Falls du ein Git-Repository hast:
cd /opt
git clone https://github.com/DEIN_USER/QurbanFlow.git qurbanflow
```

---

## 4. Konfiguration

Auf dem Server:

```bash
cd /opt/qurbanflow

# .env erstellen
cp .env.example .env
nano .env
```

Folgende Werte **ausfüllen**:

```env
# Dein Bot Token (von @BotFather)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...

# Erlaubte User-IDs (kommagetrennt)
ALLOWED_USER_IDS=123456789

# Optional: User-ID für Video-Benachrichtigungen
NOTIFY_USER_ID=123456789

# Von my.telegram.org (für den lokalen API-Server)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef
```

---

## 5. Bot starten

```bash
cd /opt/qurbanflow

# Erstmalig bauen und starten
docker compose up -d --build

# Logs prüfen
docker compose logs -f
```

Du solltest sehen:
```
telegram-bot-api  | [info] Telegram Bot API started
qurbanflow        | 🕌 QurbanFlow Bot wird gestartet...
qurbanflow        | 🔗 Lokaler API-Server: http://telegram-bot-api:8081/bot
qurbanflow        | 📂 Lokaler Modus aktiv
qurbanflow        | Bot läuft!
```

### Bot testen

Sende `/start` an deinen Bot in Telegram und teste den ganzen Flow!

---

## 6. Nützliche Befehle

```bash
# Status prüfen
docker compose ps

# Logs ansehen
docker compose logs -f qurbanflow

# Bot neustarten
docker compose restart qurbanflow

# Alles stoppen
docker compose down

# Neu bauen nach Code-Änderungen
docker compose up -d --build

# Spender-Ordner auf dem Server ansehen
ls -la /opt/qurbanflow/Spender/
```

---

## 7. Updates deployen

```bash
cd /opt/qurbanflow

# Neuen Code holen
git pull

# Neu bauen und starten
docker compose up -d --build
```

---

## 8. Troubleshooting

### Bot startet nicht
```bash
# Logs des API-Servers prüfen
docker compose logs telegram-bot-api

# Häufigster Fehler: TELEGRAM_API_ID oder TELEGRAM_API_HASH fehlt/falsch
```

### Video-Upload funktioniert nicht
```bash
# Prüfen ob der lokale API-Server läuft
docker compose ps

# Shared Volume prüfen
docker compose exec qurbanflow ls -la /var/lib/telegram-bot-api/
```

### Speicherplatz prüfen
```bash
df -h
# Der CX22 hat 40 GB – sollte für viele Videos reichen
# Alte Spender-Ordner können bei Bedarf gelöscht werden
```
