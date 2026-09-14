# 🚀 Getting Started Tutorial - Step by Step

Panduan praktis untuk setup Smart AI IoT dari nol sampai sistem berjalan lengkap.

## 📋 Prerequisites Checklist

Sebelum mulai, pastikan Anda punya:

- [ ] **Laptop/PC** dengan Windows/Mac/Linux
- [ ] **Python 3.11+** terinstall ([Download](https://www.python.org/downloads/))
- [ ] **Arduino IDE** terinstall ([Download](https://www.arduino.cc/en/software))
- [ ] **ESP32 Development Board** + kabel USB
- [ ] **Relay Module 5V** (1-channel atau lebih)
- [ ] **Kabel jumper** female-female (minimal 3 buah)
- [ ] **Google Gemini API Key** ([Dapatkan gratis](https://aistudio.google.com/app/apikey))
- [ ] **HiveMQ Cloud Account** gratis ([Sign up](https://www.hivemq.com/mqtt-cloud-broker/))

**Estimasi Waktu**: 30-45 menit untuk setup lengkap

---

## Part 1: Setup MQTT Broker (HiveMQ Cloud)

### 1.1 Buat Akun HiveMQ Cloud

1. Buka https://www.hivemq.com/mqtt-cloud-broker/
2. Klik **"Try Free"** atau **"Sign Up"**
3. Lengkapi form registrasi dan verifikasi email

### 1.2 Buat Cluster MQTT Baru

1. Login ke HiveMQ Console
2. Klik **"Create Cluster"**
3. Pilih **Free Plan** (100 connections, cukup untuk testing)
4. **Cluster Name**: `smart-iot-cluster` (atau nama bebas)
5. **Region**: Pilih yang terdekat (e.g., EU Central)
6. Klik **"Create"**
7. Tunggu 2-3 menit hingga cluster status = **Running**

### 1.3 Catat Credentials

Setelah cluster ready, catat informasi berikut:

```
MQTT Broker URL: <your-cluster-id>.s1.eu.hivemq.cloud
Port: 8883 (TLS)
Username: (buat di tab "Access Management")
Password: (buat di tab "Access Management")
```

**Buat Username/Password**:
1. Tab **"Access Management"** → **"Add Credentials"**
2. Username: `SMART_AI_IoT`
3. Password: `<buat password strong>` (misal: `SmartHome2026!`)
4. Permissions: Pilih **"All"** atau custom:
   - Subscribe: `#` (all topics)
   - Publish: `#` (all topics)
5. Klik **"Add"**

**✅ Checkpoint**: Anda sekarang punya MQTT broker dengan credentials

---

## Part 2: Setup Backend (Python FastAPI)

### 2.1 Clone atau Extract Project

```bash
cd "D:\IoT ESP\smarthome-AIoT"
# Atau extract ZIP jika download dari repository
```

### 2.2 Install Python Dependencies

```bash
cd backend

# Buat virtual environment (recommended)
python -m venv venv

# Aktifkan virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Troubleshooting**:
- Jika `pip install` gagal, update pip: `python -m pip install --upgrade pip`
- Jika error SSL, gunakan: `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt`

### 2.3 Configure Environment Variables

```bash
# Copy template .env
cp ../.env.example .env

# Edit file .env
notepad .env   # Windows
nano .env      # Mac/Linux
```

**Isi dengan credentials Anda**:

```env
# Application
APP_NAME="SMART AI IoT Backend"
APP_VERSION="3.0.0"
APP_ENV="development"
DEBUG=true

# Server
HOST="0.0.0.0"
PORT=8000

# Database (gunakan default SQLite)
DATABASE_URL="sqlite+aiosqlite:///./smart_aiot.db"

# MQTT (ganti dengan credentials HiveMQ Anda)
MQTT_BROKER="<your-cluster-id>.s1.eu.hivemq.cloud"
MQTT_PORT=8883
MQTT_USERNAME="SMART_AI_IoT"
MQTT_PASSWORD="SmartHome2026!"
MQTT_KEEPALIVE=60

# Google Gemini AI (ganti dengan API key Anda)
GEMINI_API_KEY="AIza...your-actual-key"
GEMINI_MODEL="gemini-2.0-flash-exp"

# Security (generate random string)
SECRET_KEY="your-secret-key-change-this-to-random-string"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS
BACKEND_CORS_ORIGINS="http://localhost:3000,http://localhost:8000"

# Logging
LOG_LEVEL="INFO"
LOG_FILE="logs/app.log"
```

**Generate SECRET_KEY** (random string):
```bash
# Windows PowerShell:
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})

# Mac/Linux:
openssl rand -hex 32
```

### 2.4 Initialize Database

```bash
# Buat folder logs
mkdir logs

# Run database migrations
alembic upgrade head
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Running upgrade -> abc123, initial schema
INFO  [alembic.runtime.migration] Running upgrade abc123 -> def456, add timers
```

### 2.5 Start Backend Server

```bash
python main.py
```

**Expected Output**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     app_startup | app_name=SMART AI IoT Backend
INFO:     MQTT connected to broker
INFO:     Gemini AI service initialized
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**✅ Checkpoint**: Backend berjalan di http://localhost:8000

### 2.6 Verify Backend

Buka browser:

1. **API Docs**: http://localhost:8000/docs (Swagger UI interaktif)
2. **Health Check**: http://localhost:8000/health

Expected response health check:
```json
{
  "status": "ok",
  "version": "3.0.0",
  "environment": "development",
  "timestamp": "2026-09-14T13:40:54.370Z",
  "services": {
    "mqtt": "connected",
    "gemini": "ready",
    "websocket": "0 connections",
    "database": "configured"
  }
}
```

**✅ Checkpoint**: Backend healthy dan terhubung ke MQTT broker

---

## Part 3: Setup Hardware (ESP32)

### 3.1 Install Arduino Libraries

1. Buka **Arduino IDE**
2. **Tools** → **Manage Libraries** (atau Ctrl+Shift+I)
3. Install libraries berikut:

| Library | Author | Version |
|---------|--------|---------|
| **PubSubClient** | Nick O'Leary | 2.8+ |
| **ArduinoJson** | Benoit Blanchon | 6.21+ |

**Cara install**:
- Ketik nama library di search box
- Klik **Install** pada hasil yang sesuai
- Tunggu hingga status = **INSTALLED**

### 3.2 Configure ESP32 Board

1. **File** → **Preferences**
2. **Additional Board Manager URLs**, tambahkan:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Klik **OK**
4. **Tools** → **Board** → **Boards Manager**
5. Search: `esp32`
6. Install: **ESP32 by Espressif Systems** (versi 2.0.0+)

### 3.3 Wiring ESP32 + Relay

**Diagram**:
```
ESP32          Relay Module
-----          ------------
GPIO 4  ───→   IN
GND     ───→   GND
VIN(5V) ───→   VCC
```

**Langkah-langkah**:
1. **Matikan power** ESP32 (cabut USB)
2. Ambil 3 kabel jumper female-female
3. Hubungkan:
   - Jumper 1: ESP32 pin **GPIO 4** → Relay pin **IN**
   - Jumper 2: ESP32 pin **GND** → Relay pin **GND**
   - Jumper 3: ESP32 pin **VIN** → Relay pin **VCC**
4. Cek koneksi tidak ada yang loose (goyang)

**⚠️ Safety**: Jangan hubungkan relay ke listrik AC dulu. Testing dulu dengan LED atau voltmeter.

### 3.4 Create Arduino Sketch

1. **File** → **New** (buat sketch baru)
2. **File** → **Save As**: `smart_home_device.ino`
3. Buat file `config.h` di folder yang sama

**config.h** (copy dari `Hardware/config.py` template):

```cpp
#ifndef CONFIG_H
#define CONFIG_H

// WiFi Configuration
const char* WIFI_SSID = "NamaWiFiRumahAnda";
const char* WIFI_PASSWORD = "PasswordWiFiAnda";

// MQTT Configuration (sama dengan backend/.env)
const char* MQTT_BROKER = "<your-cluster-id>.s1.eu.hivemq.cloud";
const int MQTT_PORT = 8883;
const char* MQTT_USERNAME = "SMART_AI_IoT";
const char* MQTT_PASSWORD = "SmartHome2026!";

// Device Configuration (HARUS UNIK!)
const char* HOME_ID = "mikohome";
const char* DEVICE_ID = "light_lamp_test_001";
const char* MQTT_CLIENT_ID = "esp32_test_001";

// Pin Configuration
const int RELAY_PIN = 4;

#endif
```

**smart_home_device.ino** (main code):

```cpp
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "config.h"

WiFiClientSecure espClient;
PubSubClient mqttClient(espClient);

String commandTopic;
String statusTopic;

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);
  
  setupWiFi();
  setupMQTT();
  
  commandTopic = String(HOME_ID) + "/" + String(DEVICE_ID) + "/set";
  statusTopic = String(HOME_ID) + "/" + String(DEVICE_ID) + "/status";
}

void loop() {
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();
}

void setupWiFi() {
  Serial.print("[WiFi] Connecting to ");
  Serial.println(WIFI_SSID);
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\n[WiFi] ✓ Connected!");
  Serial.print("[WiFi] IP: ");
  Serial.println(WiFi.localIP());
}

void setupMQTT() {
  espClient.setInsecure(); // Skip cert verification (OK untuk testing)
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
}

void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Connecting to broker...");
    
    if (mqttClient.connect(MQTT_CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD)) {
      Serial.println(" ✓ Connected!");
      mqttClient.subscribe(commandTopic.c_str());
      Serial.print("[MQTT] ✓ Subscribed to: ");
      Serial.println(commandTopic);
      
      publishStatus("unknown");
    } else {
      Serial.print(" ✗ Failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" Retry in 5s...");
      delay(5000);
    }
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("[MQTT] Received on ");
  Serial.print(topic);
  Serial.print(": ");
  
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);
  
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, message);
  
  if (error) {
    Serial.println("[ERROR] JSON parse failed");
    return;
  }
  
  const char* state = doc["state"];
  
  if (strcmp(state, "on") == 0) {
    digitalWrite(RELAY_PIN, HIGH);
    Serial.println("[Device] → State: ON");
    publishStatus("on");
  } else if (strcmp(state, "off") == 0) {
    digitalWrite(RELAY_PIN, LOW);
    Serial.println("[Device] → State: OFF");
    publishStatus("off");
  }
}

void publishStatus(String state) {
  StaticJsonDocument<128> doc;
  doc["state"] = state;
  doc["timestamp"] = millis() / 1000;
  
  char buffer[128];
  serializeJson(doc, buffer);
  
  mqttClient.publish(statusTopic.c_str(), buffer);
  Serial.print("[MQTT] Published status: ");
  Serial.println(buffer);
}
```

### 3.5 Upload ke ESP32

1. Colokkan ESP32 ke laptop via USB
2. **Tools** → **Board** → pilih **ESP32 Dev Module**
3. **Tools** → **Port** → pilih port COM yang muncul (e.g., COM3)
4. **Upload Speed** → `115200`
5. Klik tombol **Upload** (→)
6. Tunggu hingga "Done uploading"

### 3.6 Monitor Serial Output

1. **Tools** → **Serial Monitor** (atau Ctrl+Shift+M)
2. Set baud rate: **115200**
3. Observe output:

```
[WiFi] Connecting to NamaWiFiRumahAnda
........
[WiFi] ✓ Connected!
[WiFi] IP: 192.168.1.100
[MQTT] Connecting to broker... ✓ Connected!
[MQTT] ✓ Subscribed to: mikohome/light_lamp_test_001/set
[MQTT] Published status: {"state":"unknown","timestamp":0}
[Device] Ready. Waiting for commands...
```

**✅ Checkpoint**: ESP32 terhubung ke WiFi dan MQTT broker

---

## Part 4: Register Device di Backend

### 4.1 Via Swagger UI (Recommended untuk Pemula)

1. Buka http://localhost:8000/docs
2. Scroll ke **POST /api/v1/homes/{home_id}/devices**
3. Klik **"Try it out"**
4. Isi parameters:
   - `home_id`: `mikohome`
5. Isi Request body:
   ```json
   {
     "device_id": "light_lamp_test_001",
     "device_type": "relay",
     "room": "test_room"
   }
   ```
6. Klik **"Execute"**

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "device_id": "light_lamp_test_001",
    "home_id": "mikohome",
    "device_type": "relay",
    "room": "test_room",
    "state": "unknown"
  },
  "error": null
}
```

### 4.2 Via cURL (Alternative)

```bash
curl -X POST "http://localhost:8000/api/v1/homes/mikohome/devices" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "light_lamp_test_001",
    "device_type": "relay",
    "room": "test_room"
  }'
```

**✅ Checkpoint**: Device registered di database backend

---

## Part 5: Testing End-to-End

### 5.1 Test Manual Toggle (via API)

**Via Swagger UI**:
1. http://localhost:8000/docs
2. **POST /api/v1/homes/{home_id}/devices/{device_id}/toggle**
3. Klik **"Try it out"**
4. Isi:
   - `home_id`: `mikohome`
   - `device_id`: `light_lamp_test_001`
   - Request body: `{"state": "on"}`
5. Klik **"Execute"**

**Via cURL**:
```bash
curl -X POST "http://localhost:8000/api/v1/homes/mikohome/devices/light_lamp_test_001/toggle" \
  -H "Content-Type: application/json" \
  -d '{"state": "on"}'
```

**Expected**:
- Backend log: `MQTT published to mikohome/light_lamp_test_001/set`
- ESP32 Serial Monitor:
  ```
  [MQTT] Received on mikohome/light_lamp_test_001/set: {"state":"on",...}
  [Device] → State: ON
  [MQTT] Published status: {"state":"on",...}
  ```
- **Relay**: Akan terdengar "click" dan LED relay menyala
- Backend log: `Received status update from light_lamp_test_001: on`

**✅ Test berhasil** jika relay bekerja dan backend terima status update!

### 5.2 Test OFF Command

```bash
curl -X POST "http://localhost:8000/api/v1/homes/mikohome/devices/light_lamp_test_001/toggle" \
  -H "Content-Type: application/json" \
  -d '{"state": "off"}'
```

Expected: Relay click OFF, LED relay mati

### 5.3 Test AI Chat (dengan Konfirmasi)

**Via Swagger UI**:
1. **POST /api/v1/homes/{home_id}/chat**
2. `home_id`: `mikohome`
3. Request body:
   ```json
   {
     "message": "nyalakan lampu test"
   }
   ```
4. **Execute**

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "type": "confirmation_required",
    "action_id": "act_a1b2c3",
    "intent_summary": "Menyalakan light_lamp_test_001 di mikohome",
    "proposed_action": {
      "tool": "set_device_state",
      "device_id": "light_lamp_test_001",
      "state": "on"
    },
    "expires_in": 60
  }
}
```

**Confirm Action**:
1. **POST /api/v1/homes/{home_id}/chat/confirm**
2. Request body:
   ```json
   {
     "action_id": "act_a1b2c3",
     "confirm": true
   }
   ```
3. **Execute**

Expected: Relay ON, sama seperti manual toggle

### 5.4 Test Conversational Chat

Request body:
```json
{
  "message": "halo, apa kabar?"
}
```

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "type": "chat",
    "message": "Halo! Saya baik, terima kasih. Ada yang bisa saya bantu untuk kontrol smart home Anda?"
  }
}
```

**✅ Checkpoint**: Sistem berjalan end-to-end dari frontend → backend → MQTT → ESP32!

---

## Part 6: Open Frontend UI (Optional)

1. Buka http://localhost:8000/ui
2. Atau buka file `frontend/index.html` di browser

Expected: Dashboard dengan device card dan chat interface

---

## 🎉 Congratulations!

Anda berhasil setup Smart AI IoT lengkap! Sekarang Anda bisa:

- ✅ Kontrol device via REST API
- ✅ Kontrol device via AI chat natural language
- ✅ Real-time status update via MQTT
- ✅ Konfirmasi eksplisit untuk AI commands

## 🚀 Next Steps

1. **Tambah device kedua** - copy sketch dengan `DEVICE_ID` berbeda
2. **Setup frontend** - customisasi UI sesuai kebutuhan
3. **Tambah fitur timer** - schedule on/off otomatis
4. **Deploy ke production** - gunakan PostgreSQL + Redis
5. **Integrate AC/TV** - tambah IR transmitter untuk control AC

## 📚 Troubleshooting

Jika ada masalah, lihat [TROUBLESHOOTING.md](TROUBLESHOOTING.md) untuk solusi lengkap.

---

**Last Updated**: 2026-09-14
