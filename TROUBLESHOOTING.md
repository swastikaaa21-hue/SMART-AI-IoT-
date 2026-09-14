# 🔧 Troubleshooting Guide

Solusi untuk masalah umum yang sering terjadi saat setup dan operasional Smart AI IoT.

## 📑 Table of Contents

- [Backend Issues](#backend-issues)
- [ESP32 Hardware Issues](#esp32-hardware-issues)
- [MQTT Connection Issues](#mqtt-connection-issues)
- [AI / Gemini Issues](#ai--gemini-issues)
- [Database Issues](#database-issues)
- [Network & Firewall](#network--firewall)

---

## Backend Issues

### Issue: `ModuleNotFoundError` saat jalankan backend

**Gejala**:
```
ModuleNotFoundError: No module named 'fastapi'
```

**Penyebab**: Dependencies belum terinstall atau virtual environment tidak aktif

**Solusi**:
```bash
cd backend

# Aktifkan virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep fastapi
```

---

### Issue: Backend crash dengan `MQTT connection failed`

**Gejala**:
```
ERROR: MQTT connection failed, rc=-2
Application startup failed
```

**Penyebab**: 
- Credentials MQTT salah di `.env`
- HiveMQ cluster tidak aktif
- Firewall block port 8883

**Solusi**:

**1. Cek credentials di `.env`**:
```bash
cat .env | grep MQTT
```

Expected:
```
MQTT_BROKER=<your-cluster-id>.s1.eu.hivemq.cloud
MQTT_PORT=8883
MQTT_USERNAME=SMART_AI_IoT
MQTT_PASSWORD=<your-password>
```

**2. Test MQTT connection manual**:
```bash
# Install mosquitto client
# Windows: Download dari https://mosquitto.org/download/
# Mac: brew install mosquitto
# Linux: apt install mosquitto-clients

# Test connection
mosquitto_pub -h <your-broker>.s1.eu.hivemq.cloud -p 8883 \
  -u SMART_AI_IoT -P <password> \
  -t test/topic -m "hello" \
  --cafile /path/to/ca.crt
```

Jika gagal → problem di broker atau credentials

**3. Cek HiveMQ cluster status**:
- Login ke HiveMQ Console
- Dashboard → Cluster harus status **Running** (hijau)
- Jika **Stopped** → klik **Start**

**4. Cek firewall**:
```bash
# Test port 8883 accessible
telnet <your-broker>.s1.eu.hivemq.cloud 8883
# atau
curl -v telnet://<your-broker>.s1.eu.hivemq.cloud:8883
```

Jika timeout → firewall block port 8883

---

### Issue: `Gemini API error: PERMISSION_DENIED`

**Gejala**:
```
ERROR: Gemini API call failed
google.api_core.exceptions.PermissionDenied: 403 API key not valid
```

**Penyebab**: 
- API key salah
- API key belum enable Gemini API
- Quota exceeded

**Solusi**:

**1. Verify API key**:
```bash
cat backend/.env | grep GEMINI_API_KEY
```

**2. Test API key manual**:
```bash
curl -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"hello"}]}]}' \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=YOUR_API_KEY"
```

**3. Enable Gemini API**:
- Buka https://aistudio.google.com/
- Login dengan akun yang sama
- Settings → API Keys → pastikan status **Active**

**4. Cek quota**:
- Google AI Studio → Usage
- Free tier: 60 requests/minute
- Jika exceed → tunggu 1 menit atau upgrade

---

### Issue: `Database locked` error (SQLite)

**Gejala**:
```
sqlite3.OperationalError: database is locked
```

**Penyebab**: 
- Multiple backend instances akses SQLite bersamaan
- File `.db` corrupt
- Antivirus lock file

**Solusi**:

**1. Stop semua backend instances**:
```bash
# Windows:
taskkill /F /IM python.exe
# Mac/Linux:
pkill -f "python main.py"
```

**2. Delete lock file**:
```bash
cd backend
rm smart_aiot.db-journal  # Jika ada
```

**3. Verify database**:
```bash
sqlite3 smart_aiot.db "PRAGMA integrity_check;"
```

**4. Jika corrupt, recreate**:
```bash
# Backup old DB
mv smart_aiot.db smart_aiot.db.backup

# Recreate schema
alembic upgrade head
```

**5. Production fix**: Gunakan PostgreSQL, bukan SQLite
```env
# .env
DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/smart_iot_db"
```

---

## ESP32 Hardware Issues

### Issue: WiFi tidak connect

**Gejala**:
```
[WiFi] Connecting to YourSSID
...................
(stuck forever)
```

**Penyebab**:
- SSID/password salah
- WiFi 5GHz (ESP32 hanya support 2.4GHz)
- Jarak terlalu jauh dari router
- WiFi hidden SSID

**Solusi**:

**1. Verify credentials di `config.h`**:
```cpp
const char* WIFI_SSID = "NamaWiFiAnda";  // CASE SENSITIVE!
const char* WIFI_PASSWORD = "PasswordWiFi";
```

**2. Cek WiFi frequency**:
- Buka router settings
- Pastikan 2.4GHz band enabled
- ESP32 **tidak support** 5GHz

**3. Test jarak WiFi**:
- Dekatkan ESP32 ke router (< 3 meter)
- Jika connect → masalah jarak/sinyal lemah
- Solusi: gunakan WiFi extender atau external antenna

**4. Debug WiFi scan**:
Tambahkan code di `setup()`:
```cpp
void setup() {
  Serial.begin(115200);
  
  // Scan available networks
  int n = WiFi.scanNetworks();
  Serial.println("WiFi networks found:");
  for (int i = 0; i < n; i++) {
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.print(WiFi.SSID(i));
    Serial.print(" (");
    Serial.print(WiFi.RSSI(i));
    Serial.println(" dBm)");
  }
  
  // Then connect...
}
```

Jika SSID Anda tidak muncul → problem di router/ESP32 hardware

**5. Hidden SSID**:
```cpp
// Jika WiFi hidden, gunakan:
WiFi.begin(WIFI_SSID, WIFI_PASSWORD, 0, NULL, true);
```

---

### Issue: MQTT tidak connect dari ESP32

**Gejala**:
```
[MQTT] Connecting to broker... ✗ Failed, rc=-2
[MQTT] Retry in 5s...
```

**Error codes**:
- `-2`: Network timeout → cek internet connection
- `-4`: Authentication failed → cek username/password
- `-5`: Not authorized → cek permissions di broker

**Solusi per error code**:

**rc=-2 (Network timeout)**:
```cpp
// Cek internet connection
void setup() {
  setupWiFi();
  
  // Test ping Google DNS
  IPAddress testIP(8, 8, 8, 8);
  if (Ping.ping(testIP)) {
    Serial.println("Internet OK");
  } else {
    Serial.println("No internet connection!");
  }
}
```

**rc=-4 (Auth failed)**:
```cpp
// Verify credentials
Serial.print("MQTT_BROKER: "); Serial.println(MQTT_BROKER);
Serial.print("MQTT_USERNAME: "); Serial.println(MQTT_USERNAME);
Serial.print("MQTT_PASSWORD: "); Serial.println(MQTT_PASSWORD);

// Pastikan tidak ada trailing spaces atau special chars
```

**rc=-5 (Not authorized)**:
- Login HiveMQ Console
- Access Management → Permissions
- Pastikan user bisa **Subscribe** dan **Publish** ke `#` (all topics)

**rc=-1 (Connection refused)**:
```cpp
// Cek TLS/SSL setup
espClient.setInsecure();  // Skip cert verification (testing only)

// Jika masih gagal, coba non-TLS port 1883 (testing only)
const int MQTT_PORT = 1883;  // TEMPORARY - switch back to 8883 after test
```

---

### Issue: Relay tidak bekerja

**Gejala**:
- Serial Monitor: "State: ON"
- Tapi relay tidak click, LED tidak menyala

**Penyebab**:
- Wiring loose
- Relay module butuh logic inverted
- Insufficient power
- Relay rusak

**Solusi**:

**1. Test manual GPIO**:
```cpp
void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  
  // Test loop
  for (int i = 0; i < 10; i++) {
    Serial.println("ON");
    digitalWrite(RELAY_PIN, HIGH);
    delay(1000);
    
    Serial.println("OFF");
    digitalWrite(RELAY_PIN, LOW);
    delay(1000);
  }
}
```

Jika tetap tidak bekerja → lanjut step berikutnya

**2. Cek wiring dengan multimeter**:
```
ESP32 GPIO 4 → Measure voltage:
- HIGH state: ~3.3V
- LOW state: ~0V
```

Jika voltage OK tapi relay tidak respond → masalah di relay module

**3. Test inverted logic** (some relay active LOW):
```cpp
// Swap HIGH/LOW
if (state == "on") {
  digitalWrite(RELAY_PIN, LOW);   // Inverted
} else {
  digitalWrite(RELAY_PIN, HIGH);  // Inverted
}
```

**4. Cek power supply**:
- Relay module butuh **5V external power** untuk coil
- ESP32 VIN hanya supply jika USB plug 5V
- Solusi: gunakan power supply 5V 2A eksternal

**5. Replace relay module**:
- Test dengan relay lain
- Atau test dengan LED sederhana:
  ```cpp
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);  // LED should light up
  ```

---

## MQTT Connection Issues

### Issue: Device status tidak update di backend

**Gejala**:
- ESP32 publish status (terlihat di Serial Monitor)
- Backend tidak terima update (database state tetap "unknown")

**Penyebab**:
- Backend tidak subscribe topic yang benar
- Topic name typo
- Payload format salah

**Solusi**:

**1. Verify topic names match**:

ESP32 (`config.h`):
```cpp
const char* HOME_ID = "mikohome";
const char* DEVICE_ID = "light_lamp_test_001";
```

Backend register device:
```json
{
  "home_id": "mikohome",
  "device_id": "light_lamp_test_001"
}
```

Harus **EXACT MATCH** (case-sensitive)

**2. Monitor MQTT traffic**:

Install MQTTX (MQTT client GUI): https://mqttx.app/

Connect ke broker dan subscribe:
```
Topic: mikohome/+/status
```

Trigger ESP32 publish → Anda harus lihat message muncul di MQTTX

Jika tidak muncul → ESP32 tidak publish
Jika muncul tapi backend tidak terima → backend subscribe issue

**3. Check backend subscription**:

Backend log saat startup harus ada:
```
INFO: MQTT subscribed to: mikohome/+/status
```

Jika tidak ada → backend tidak subscribe

**4. Verify payload format**:

ESP32 harus publish JSON valid:
```json
{"state":"on","timestamp":12345}
```

**Tidak boleh**:
```json
{state:on}           // Missing quotes
{"state": on}        // Missing quotes on value
```

Test JSON di ESP32:
```cpp
void publishStatus(String state) {
  StaticJsonDocument<128> doc;
  doc["state"] = state;
  doc["timestamp"] = millis() / 1000;
  
  char buffer[128];
  size_t len = serializeJson(doc, buffer);
  
  // Debug: print JSON before publish
  Serial.print("JSON payload: ");
  Serial.println(buffer);
  
  mqttClient.publish(statusTopic.c_str(), buffer);
}
```

---

## AI / Gemini Issues

### Issue: AI tidak klasifikasi intent dengan benar

**Gejala**:
- User: "matikan lampu" → Response: `type: chat` (harusnya `confirmation_required`)
- User: "apa kabar" → Response: `type: confirmation_required` (harusnya `chat`)

**Penyebab**:
- LLM prompt tidak jelas
- Model hallucination
- Function calling tools tidak didefinisikan dengan benar

**Solusi**:

**1. Review system prompt** di `backend/app/services/gemini_service.py`:

```python
SYSTEM_PROMPT = """
Kamu adalah asisten smart home. PENTING:

1. Jika user memberi PERINTAH eksplisit untuk kontrol device (kata kunci: nyalakan, matikan, hidupkan, padamkan, set timer),
   WAJIB panggil tool yang sesuai. JANGAN jawab teks biasa.

2. Jika user hanya bertanya, ngobrol, curhat, minta info (BUKAN perintah kontrol),
   JANGAN panggil tool. Jawab natural sebagai teks.

3. Kalau ragu → anggap OBROLAN (lebih aman).

Contoh PERINTAH (call tool):
- "matikan lampu outdoor"
- "nyalakan kipas"
- "set timer mati jam 10"

Contoh OBROLAN (no tool):
- "kenapa lampu sering mati?"
- "apa kabar?"
- "gimana cara hemat listrik?"
"""
```

**2. Test dengan berbagai variasi**:

```bash
# Via Swagger UI atau curl
curl -X POST "http://localhost:8000/api/v1/homes/mikohome/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "TEST_MESSAGE_HERE"}'
```

Test cases:
| Message | Expected `type` | Reason |
|---------|-----------------|--------|
| "matikan lampu" | `confirmation_required` | Explicit command |
| "nyalakan kipas ruang tamu" | `confirmation_required` | Explicit command |
| "kenapa lampu mati?" | `chat` | Question, not command |
| "apa kabar?" | `chat` | Conversation |
| "tolong matikan lampu outdoor" | `confirmation_required` | Polite command |

**3. Jika tetap salah → upgrade model**:

```env
# .env - try different model
GEMINI_MODEL="gemini-1.5-pro"  # More accurate than flash
```

**4. Fallback: Manual keyword detection** (last resort):

```python
# Jika LLM tidak reliable, tambahkan keyword matching
COMMAND_KEYWORDS = ["nyalakan", "matikan", "hidupkan", "padamkan", "set timer"]

def classify_intent(message: str) -> str:
    message_lower = message.lower()
    
    # Manual detection
    for keyword in COMMAND_KEYWORDS:
        if keyword in message_lower:
            # Then use LLM for parameter extraction
            return "command"
    
    return "chat"
```

---

## Database Issues

### Issue: Alembic migration failed

**Gejala**:
```
alembic.util.exc.CommandError: Target database is not up to date.
```

**Solusi**:

```bash
# Check current revision
alembic current

# Check pending migrations
alembic heads

# Force to latest
alembic upgrade head

# Jika error "can't locate revision"
alembic stamp head  # Force stamp sebagai current
```

---

### Issue: Duplicate device registration

**Gejala**:
```
IntegrityError: UNIQUE constraint failed: devices.home_id, devices.device_id
```

**Solusi**:

```bash
# Check existing devices
curl "http://localhost:8000/api/v1/homes/mikohome/devices"

# Delete duplicate
curl -X DELETE "http://localhost:8000/api/v1/homes/mikohome/devices/light_lamp_test_001"

# Re-register
curl -X POST "http://localhost:8000/api/v1/homes/mikohome/devices" -d '...'
```

---

## Network & Firewall

### Issue: Frontend tidak bisa akses backend

**Gejala**:
```
Failed to fetch: ERR_CONNECTION_REFUSED
```

**Solusi**:

**1. Cek backend running**:
```bash
curl http://localhost:8000/health
```

**2. Cek firewall allow port 8000**:
```bash
# Windows: Allow in Windows Defender Firewall
netsh advfirewall firewall add rule name="Backend API" dir=in action=allow protocol=TCP localport=8000

# Mac:
# System Preferences → Security & Privacy → Firewall → Firewall Options
# Add Python to allowed apps
```

**3. Access dari network lain** (e.g., mobile):
```bash
# Backend running di PC: 192.168.1.100
# Di mobile browser: http://192.168.1.100:8000/ui
```

Jika tidak bisa akses → firewall block atau CORS issue

**4. Fix CORS** di backend:
```python
# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all (development only)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📞 Getting More Help

Jika masalah tidak terpecahkan:

1. **Check logs**:
   ```bash
   # Backend logs
   cat backend/logs/app.log
   
   # ESP32 serial output
   # Save dari Serial Monitor
   ```

2. **Minimal reproducible example**:
   - Exact command/action yang trigger error
   - Error message lengkap
   - Environment info (OS, Python version, ESP32 board)

3. **GitHub Issues**:
   - Open issue di repository project
   - Attach logs dan screenshots

4. **Community**:
   - FastAPI Discord
   - ESP32 Forum
   - MQTT Community

---

**Last Updated**: 2026-09-14
