# 🏠 Smart AI IoT - Sistem Smart Home dengan AI Assistant

Platform smart home terintegrasi dengan AI (Google Gemini) yang memungkinkan kontrol perangkat IoT menggunakan perintah natural language dan konfirmasi eksekusi yang aman.

## 📁 Struktur Project

```
smarthome-AIoT/
├── backend/              # Python FastAPI Backend
│   ├── app/             
│   │   ├── api/         # REST API endpoints
│   │   ├── core/        # Config, database, logging
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   └── services/    # MQTT, Gemini AI, WebSocket
│   ├── alembic/         # Database migrations
│   ├── main.py          # Entry point
│   └── requirements.txt # Python dependencies
│
├── Hardware/            # ESP32 IoT Devices
│   ├── config.py        # Template konfigurasi (copy ke config.h)
│   ├── main.py          # Arduino sketch (rename ke .ino)
│   └── README.md        # Setup guide hardware
│
├── frontend/            # Frontend UI (HTML)
│   └── index.html       # Dashboard UI
│
└── smart-ai-iot-job-spec-v3.md  # Dokumentasi API Contract (LOCKED)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- ESP32 development board + relay module
- Arduino IDE atau PlatformIO
- HiveMQ Cloud account (atau MQTT broker lain dengan TLS)
- Google Gemini API key

### 1. Setup Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Copy template environment
cp .env.example .env

# Edit .env dan isi:
# - GEMINI_API_KEY
# - MQTT_BROKER, MQTT_USERNAME, MQTT_PASSWORD
# - DATABASE_URL (default: sqlite:///smart_aiot.db)

# Run database migrations
alembic upgrade head

# Start backend server
python main.py
# atau
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Backend akan berjalan di `http://localhost:8000`
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 2. Setup Hardware (ESP32)

```bash
cd Hardware

# 1. Copy template config
cp config.py config.h

# 2. Edit config.h, isi:
#    - WIFI_SSID dan WIFI_PASSWORD
#    - MQTT credentials (sama dengan backend)
#    - HOME_ID dan DEVICE_ID yang unik

# 3. Install Arduino libraries:
#    - WiFi (built-in)
#    - WiFiClientSecure (built-in)
#    - PubSubClient by Nick O'Leary
#    - ArduinoJson by Benoit Blanchon

# 4. Rename main.py ke main.ino (atau buat sketch baru)

# 5. Upload ke ESP32 via Arduino IDE
```

Detail lengkap: [Hardware/README.md](Hardware/README.md)

### 3. Register Device di Backend

```bash
# Via API (gunakan Swagger UI di /docs atau curl)
curl -X POST "http://localhost:8000/api/v1/homes/mikohome/devices" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "light_lamp_outdoor_f9gv",
    "device_type": "relay",
    "room": "outdoor"
  }'
```

### 4. Test System

1. Buka Serial Monitor ESP32 (115200 baud) → pastikan WiFi dan MQTT connected
2. Buka Frontend UI: `http://localhost:8000/ui`
3. Test manual toggle dari dashboard
4. Test chat AI: "matikan lampu outdoor"
5. Klik tombol **Lanjutkan** untuk konfirmasi eksekusi

## 📡 MQTT Topic Convention (PATEN v3)

### Format Topic
```
/{home_id}/{device_id}/set       → Backend ke Device (command)
/{home_id}/{device_id}/status    → Device ke Backend (status update)
```

### Contoh
```
mikohome/light_lamp_outdoor_f9gv/set
mikohome/light_lamp_outdoor_f9gv/status
```

### Payload JSON Standar

**Command** (Backend → Device):
```json
{
  "state": "on",
  "timestamp": 1735900000
}
```

**Status** (Device → Backend):
```json
{
  "state": "off",
  "timestamp": 1735900123
}
```

### Supported States
- `"on"` - Nyalakan device
- `"off"` - Matikan device

## 🤖 AI Chat Flow dengan Konfirmasi

### 1. User mengirim perintah via chat
```
POST /api/v1/homes/mikohome/chat
Body: { "message": "matikan lampu outdoor" }
```

### 2A. Perintah eksekusi → Butuh konfirmasi
Response:
```json
{
  "success": true,
  "data": {
    "type": "confirmation_required",
    "action_id": "act_9f2a1b",
    "intent_summary": "Mematikan light_lamp_outdoor_f9gv di mikohome",
    "proposed_action": {
      "tool": "set_device_state",
      "home_id": "mikohome",
      "device_id": "light_lamp_outdoor_f9gv",
      "state": "off"
    },
    "expires_in": 60
  }
}
```

Frontend menampilkan bubble dengan 2 tombol: **Lanjutkan** / **Batalkan**

### 2B. Obrolan biasa → Langsung tampil
```json
{
  "success": true,
  "data": {
    "type": "chat",
    "message": "Lampu outdoor sedang menyala sejak 2 jam yang lalu. Mau saya matikan?"
  }
}
```

Frontend menampilkan sebagai teks biasa, tanpa tombol konfirmasi.

### 3. User konfirmasi
```
POST /api/v1/homes/mikohome/chat/confirm
Body: { "action_id": "act_9f2a1b", "confirm": true }
```

Response:
```json
{
  "success": true,
  "data": {
    "executed": true,
    "result": "Lampu light_lamp_outdoor_f9gv di mikohome berhasil dimatikan"
  }
}
```

Backend publish MQTT command → ESP32 eksekusi relay → Lampu mati

## 🔌 REST API Endpoints

Base URL: `http://localhost:8000/api/v1`

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| GET | `/homes/{home_id}/devices` | List semua device + status |
| POST | `/homes/{home_id}/devices/{device_id}/toggle` | Toggle manual (langsung eksekusi) |
| POST | `/homes/{home_id}/devices/{device_id}/timer` | Set timer (langsung eksekusi) |
| POST | `/homes/{home_id}/chat` | Kirim perintah AI (butuh konfirmasi) |
| POST | `/homes/{home_id}/chat/confirm` | Konfirmasi/batalkan eksekusi AI |
| POST | `/homes/{home_id}/devices` | Register device baru (admin) |

Response format standar:
```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

Detail lengkap: [smart-ai-iot-job-spec-v3.md](smart-ai-iot-job-spec-v3.md)

## 🔐 Security Best Practices

1. **Jangan commit file .env** - sudah ada di .gitignore
2. **Jangan commit config.h** - simpan credentials WiFi/MQTT secara lokal
3. **Gunakan TLS untuk MQTT** - port 8883, bukan 1883
4. **Gunakan strong password** untuk MQTT broker
5. **Rate limiting aktif** - backend sudah include SlowAPI
6. **Konfirmasi AI** - mencegah eksekusi tidak sengaja dari AI

## 🛠️ Development

### Backend Development
```bash
cd backend

# Install dev dependencies
pip install -r requirements.txt

# Run tests
pytest

# Database migration
alembic revision --autogenerate -m "Description"
alembic upgrade head

# Format code
black app/
isort app/

# Lint
ruff check app/
```

### Adding New Device Type

1. Edit `backend/app/models/device.py` - tambah device_type baru
2. Create migration: `alembic revision --autogenerate -m "Add new device type"`
3. Run migration: `alembic upgrade head`
4. Update Hardware sketch sesuai device type baru
5. Update AI tools di `backend/app/services/gemini_service.py`

### Scalability Considerations

- **Backend**: FastAPI async untuk high concurrency
- **Database**: SQLite untuk dev, migrate ke PostgreSQL untuk production
- **MQTT**: HiveMQ Cloud auto-scale, atau gunakan cluster MQTT sendiri
- **AI**: Gemini API quota management, fallback mechanism
- **WebSocket**: Gunakan Redis pub/sub untuk multi-instance deployment

## 📚 Dokumentasi Lengkap

### 🚀 Getting Started
- **[Getting Started Tutorial](GETTING_STARTED.md)** - Panduan step-by-step dari nol sampai running (30-45 menit)
- **[Hardware Setup Guide](Hardware/README.md)** - Setup ESP32 detail dengan wiring diagram

### 📖 Technical Documentation
- **[Architecture Overview](ARCHITECTURE.md)** - Arsitektur sistem, data flow, dan scalability
- **[MQTT Topics Reference](MQTT_TOPICS.md)** - Referensi lengkap format topic dan payload MQTT
- **[Job Spec v3 - API Contract](smart-ai-iot-job-spec-v3.md)** - **LOCKED**, kontrak resmi API (PATEN)

### 🛠️ Operations
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Solusi untuk masalah umum
- **[Backend API Docs](http://localhost:8000/docs)** - Swagger UI interaktif (saat backend running)

### 📂 Quick Links
- **[Quick Reference](QUICK_REFERENCE.md)** - Cheat sheet untuk daily operations
- **[Contributing Guide](CONTRIBUTING.md)** - Panduan untuk developers
- `.env.example` - Template environment variables (copy ke `.env`)
- `.gitignore` - Git ignore rules (sudah cover backend + hardware)
- `run_all.bat` - Script untuk start semua services (Windows)

## 🐛 Troubleshooting

### Backend tidak connect ke MQTT
```bash
# Check .env file
cat backend/.env | grep MQTT

# Test MQTT connection
python backend/test_mqtt.py
```

### ESP32 tidak connect ke WiFi
- Cek SSID dan password di config.h
- Cek jarak sinyal WiFi
- Monitor serial (115200 baud)

### AI tidak respond
- Cek GEMINI_API_KEY di .env
- Cek quota API di Google AI Studio
- Cek logs: `backend/logs/app.log`

### Device tidak muncul di dashboard
- Pastikan device sudah registered via POST `/devices`
- Cek MQTT connection ESP32
- Cek topic format: `{home_id}/{device_id}/status`

## 🤝 Contributing

Ingin menambah fitur atau fix bug? Lihat [CONTRIBUTING.md](CONTRIBUTING.md) untuk panduan development.

## 📝 Roadmap

- [ ] Support IR device (AC, TV remote)
- [ ] Mobile app (React Native)
- [ ] Voice control integration (Google Assistant, Alexa)
- [ ] Energy monitoring & analytics dashboard
- [ ] Scene/automation builder (visual workflow)
- [ ] Multi-user dengan role management (admin, user, guest)
- [ ] Integration dengan Google Home/Alexa
- [ ] OTA (Over-The-Air) firmware update untuk ESP32
- [ ] Notification system (push, email, Telegram)
- [ ] Historical data & charts

## 📄 License

Proprietary - Internal Use Only

## 👥 Contributors

Project ini dikembangkan untuk smart home automation dengan AI assistant.

Untuk kontribusi, lihat [CONTRIBUTING.md](CONTRIBUTING.md).

---

**Project Status**: ✅ Production Ready v3.0.0  
**Last Updated**: 2026-09-14  
**Maintainer**: Smart AI IoT Team
