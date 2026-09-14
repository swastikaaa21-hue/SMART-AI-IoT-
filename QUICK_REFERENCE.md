# 📋 Quick Reference - Smart AI IoT

Cheat sheet untuk operasional sehari-hari Smart AI IoT platform.

## 🚀 Quick Start Commands

### Start Backend
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python main.py
# atau
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Start All Services (Windows)
```bash
run_all.bat
```

### Stop Services
```bash
# Ctrl+C di terminal
# atau Windows:
taskkill /F /IM python.exe
```

---

## 🌐 Important URLs

| Service | URL | Description |
|---------|-----|-------------|
| **Backend API Docs** | http://localhost:8000/docs | Swagger UI interaktif |
| **Backend UI** | http://localhost:8000/ui | Dashboard web |
| **Health Check** | http://localhost:8000/health | Status semua services |
| **ReDoc** | http://localhost:8000/redoc | Alternative API docs |

---

## 📡 MQTT Quick Reference

### Topic Patterns
```
Command:  /{home_id}/{device_id}/set      (Backend → Device)
Status:   /{home_id}/{device_id}/status   (Device → Backend)
```

### Example Topics
```
mikohome/light_lamp_outdoor_f9gv/set       # Command to device
mikohome/light_lamp_outdoor_f9gv/status    # Status from device
```

### Payload Format
```json
{"state": "on", "timestamp": 1726318027}
{"state": "off", "timestamp": 1726318090}
```

---

## 🔌 REST API Quick Reference

Base URL: `http://localhost:8000/api/v1`

### Device Control

**List All Devices**
```bash
GET /homes/{home_id}/devices

# Example
curl http://localhost:8000/api/v1/homes/mikohome/devices
```

**Toggle Device**
```bash
POST /homes/{home_id}/devices/{device_id}/toggle
Body: {"state": "on"}

# Example
curl -X POST http://localhost:8000/api/v1/homes/mikohome/devices/light_lamp_outdoor_f9gv/toggle \
  -H "Content-Type: application/json" \
  -d '{"state": "on"}'
```

**Set Timer**
```bash
POST /homes/{home_id}/devices/{device_id}/timer
Body: {
  "action": "off",
  "datetime": "2026-09-14T22:00:00"
}
```

### AI Chat

**Send Chat Message**
```bash
POST /homes/{home_id}/chat
Body: {"message": "matikan lampu outdoor"}

# Returns type: "chat" or "confirmation_required"
```

**Confirm AI Action**
```bash
POST /homes/{home_id}/chat/confirm
Body: {
  "action_id": "act_9f2a1b",
  "confirm": true
}
```

### Device Management

**Register New Device**
```bash
POST /homes/{home_id}/devices
Body: {
  "device_id": "light_lamp_test_001",
  "device_type": "relay",
  "room": "test_room"
}
```

**Delete Device**
```bash
DELETE /homes/{home_id}/devices/{device_id}
```

---

## 🔧 ESP32 Quick Setup

### 1. Edit config.h
```cpp
const char* WIFI_SSID = "YourWiFiName";
const char* WIFI_PASSWORD = "YourPassword";
const char* MQTT_BROKER = "xxx.s1.eu.hivemq.cloud";
const char* MQTT_USERNAME = "SMART_AI_IoT";
const char* MQTT_PASSWORD = "YourMQTTPassword";
const char* HOME_ID = "mikohome";
const char* DEVICE_ID = "light_lamp_test_001";  // MUST BE UNIQUE
```

### 2. Upload Sketch
- Board: **ESP32 Dev Module**
- Port: Select COM port
- Upload Speed: **115200**
- Click **Upload**

### 3. Monitor Serial (115200 baud)
```
[WiFi] ✓ Connected! IP: 192.168.1.100
[MQTT] ✓ Connected to broker
[MQTT] ✓ Subscribed to: mikohome/light_lamp_test_001/set
```

---

## 🐛 Common Issues & Quick Fixes

### Backend won't start
```bash
# Missing dependencies
pip install -r requirements.txt

# Database not initialized
alembic upgrade head

# Port already in use
# Windows: taskkill /F /PID <pid>
# Linux: kill -9 $(lsof -t -i:8000)
```

### ESP32 won't connect to WiFi
```cpp
// Check 2.4GHz WiFi (ESP32 doesn't support 5GHz)
// Check SSID/password (case-sensitive)
// Move closer to router
```

### ESP32 won't connect to MQTT
```cpp
// Check credentials in config.h
// Test with MQTTX client first
// Verify port 8883 (TLS)
// Check rc error code in Serial Monitor:
//   rc=-2: Network timeout
//   rc=-4: Authentication failed
```

### Device not appearing in dashboard
```bash
# 1. Check device registered
curl http://localhost:8000/api/v1/homes/mikohome/devices

# 2. If not registered, register it
curl -X POST http://localhost:8000/api/v1/homes/mikohome/devices \
  -H "Content-Type: application/json" \
  -d '{"device_id":"light_lamp_test_001","device_type":"relay","room":"test"}'

# 3. Check ESP32 published status
# Monitor Serial: should see "Published status: ..."
```

---

## 📊 Status Codes Reference

### MQTT Error Codes (ESP32)
```
rc = -4  : MQTT_CONNECTION_TIMEOUT
rc = -3  : MQTT_CONNECTION_LOST
rc = -2  : MQTT_CONNECT_FAILED
rc = -1  : MQTT_DISCONNECTED
rc = 0   : MQTT_CONNECTED
rc = 1   : MQTT_CONNECT_BAD_PROTOCOL
rc = 2   : MQTT_CONNECT_BAD_CLIENT_ID
rc = 3   : MQTT_CONNECT_UNAVAILABLE
rc = 4   : MQTT_CONNECT_BAD_CREDENTIALS
rc = 5   : MQTT_CONNECT_UNAUTHORIZED
```

### HTTP Status Codes (Backend API)
```
200 : OK
201 : Created
400 : Bad Request (invalid payload)
401 : Unauthorized (missing/invalid token)
404 : Not Found (device not exist)
422 : Validation Error (invalid schema)
500 : Internal Server Error
```

---

## 🔐 Environment Variables Checklist

### Required in backend/.env
```env
✅ GEMINI_API_KEY          # Get from ai.google.dev
✅ MQTT_BROKER             # HiveMQ cluster URL
✅ MQTT_USERNAME           # MQTT credentials
✅ MQTT_PASSWORD           # MQTT credentials
✅ SECRET_KEY              # Random string for JWT
```

### Optional (dengan defaults)
```env
DATABASE_URL              # Default: SQLite
REDIS_URL                 # Default: in-memory cache
DEBUG                     # Default: true
LOG_LEVEL                 # Default: INFO
```

---

## 📦 Dependencies Check

### Backend Python Packages
```bash
pip list | grep -E "fastapi|uvicorn|sqlalchemy|paho-mqtt|google-generativeai"
```

### ESP32 Arduino Libraries
```
✅ WiFi (built-in)
✅ WiFiClientSecure (built-in)
✅ PubSubClient by Nick O'Leary
✅ ArduinoJson by Benoit Blanchon
```

---

## 🧪 Testing Commands

### Test Backend Health
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","services":{"mqtt":"connected",...}}
```

### Test MQTT Connection
```bash
# Install MQTTX or mosquitto_pub
mosquitto_pub -h xxx.s1.eu.hivemq.cloud -p 8883 \
  -u SMART_AI_IoT -P password --cafile ca.crt \
  -t mikohome/test/set -m '{"state":"on","timestamp":1234567890}'
```

### Test Device Toggle
```bash
# Via API
curl -X POST http://localhost:8000/api/v1/homes/mikohome/devices/light_lamp_test_001/toggle \
  -H "Content-Type: application/json" \
  -d '{"state":"on"}'

# Expected: ESP32 relay click, Serial Monitor shows message received
```

### Test AI Chat
```bash
# Command that needs confirmation
curl -X POST http://localhost:8000/api/v1/homes/mikohome/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"nyalakan lampu test"}'

# Expected: {"type":"confirmation_required","action_id":"act_xxx",...}

# Conversational (no confirmation)
curl -X POST http://localhost:8000/api/v1/homes/mikohome/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"apa kabar?"}'

# Expected: {"type":"chat","message":"Saya baik..."}
```

---

## 🔗 Documentation Quick Links

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [README.md](README.md) | Project overview | First time |
| [GETTING_STARTED.md](GETTING_STARTED.md) | Step-by-step setup | Setup phase |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design | Understanding internals |
| [MQTT_TOPICS.md](MQTT_TOPICS.md) | MQTT reference | Working with topics |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Problem solving | When issues occur |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development guide | Adding features |
| [smart-ai-iot-job-spec-v3.md](smart-ai-iot-job-spec-v3.md) | API contract (LOCKED) | API integration |

---

## 💡 Tips & Tricks

### Speed Up Development

**1. Use Swagger UI** (http://localhost:8000/docs)
- Try API tanpa curl
- Auto-generate request examples
- See response schemas

**2. Monitor MQTT dengan MQTTX**
- Subscribe: `mikohome/#`
- See all traffic in real-time
- Debug payload issues

**3. Enable Debug Logging**
```env
# backend/.env
LOG_LEVEL="DEBUG"
```

### Production Deployment

**Quick checklist**:
```env
✅ DEBUG=false
✅ DATABASE_URL=postgresql://...
✅ REDIS_URL=redis://...
✅ SECRET_KEY=<strong-random-string>
✅ MQTT TLS cert validation enabled
```

### Multiple ESP32 Devices

**Device ID naming**:
```cpp
// Device 1
const char* DEVICE_ID = "light_lamp_outdoor_f9gv";
const char* MQTT_CLIENT_ID = "esp32_outdoor_f9gv";

// Device 2 (MUST BE DIFFERENT!)
const char* DEVICE_ID = "light_lamp_indoor_a3kx";
const char* MQTT_CLIENT_ID = "esp32_indoor_a3kx";
```

---

## 🆘 Emergency Fixes

### Backend Crash Loop
```bash
# 1. Check logs
cat backend/logs/app.log

# 2. Reset database
cd backend
rm smart_aiot.db
alembic upgrade head

# 3. Restart
python main.py
```

### ESP32 Boot Loop
```cpp
// Add watchdog timer
#include <esp_task_wdt.h>

void setup() {
  esp_task_wdt_init(30, true);  // 30s timeout
  esp_task_wdt_add(NULL);
  // ... rest of setup
}

void loop() {
  esp_task_wdt_reset();  // Reset watchdog
  // ... rest of loop
}
```

### MQTT Quota Exceeded (HiveMQ)
```bash
# Reduce publish rate
# ESP32: publish status setiap 30s (bukan setiap 1s)
# Backend: batch updates
```

---

## 📞 Get Help

- **Documentation**: Start with [GETTING_STARTED.md](GETTING_STARTED.md)
- **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **GitHub Issues**: For bug reports
- **Discussions**: For questions & ideas

---

**Last Updated**: 2026-09-14
**Version**: 3.0.0
