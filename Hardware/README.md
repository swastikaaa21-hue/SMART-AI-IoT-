# 🔌 ESP32 Smart Home Devices - Hardware Setup Guide

Panduan setup lengkap untuk ESP32 IoT devices yang terhubung ke Smart AI IoT platform.

## 📦 Hardware Requirements

| Komponen | Spesifikasi | Keterangan |
|----------|-------------|------------|
| ESP32 Dev Board | ESP32-WROOM-32 | Microcontroller utama dengan WiFi |
| Relay Module | 5V 1-Channel | Untuk kontrol perangkat listrik AC |
| Kabel Jumper | Female-Female | Koneksi ESP32 ke Relay |
| Power Supply | 5V 2A | Power untuk ESP32 + Relay |
| Micro USB Cable | - | Upload code & power ESP32 |

## 🔧 Pin Configuration

| Pin ESP32 | Koneksi Ke | Fungsi |
|-----------|------------|--------|
| GPIO 4 | Relay IN | Kontrol relay (signal) |
| GND | Relay GND | Ground |
| VIN (5V) | Relay VCC | Power relay module |

## 📐 Wiring Diagram

```
┌─────────────┐           ┌──────────────┐
│   ESP32     │           │  Relay 5V    │
│             │           │              │
│   GPIO 4  ──┼──────────→│  IN          │
│   GND     ──┼──────────→│  GND         │
│   VIN(5V) ──┼──────────→│  VCC         │
│             │           │              │
│             │           │  COM  ─┐     │
│             │           │  NO   ─┤     │
│             │           │  NC    │     │
└─────────────┘           └────────┼─────┘
                                   │
                                   └─→ Lampu/Device AC
```

**Catatan Keamanan**:
- ⚠️ Relay mengontrol listrik AC 220V - hati-hati saat wiring
- ⚠️ Matikan power AC sebelum wiring
- ⚠️ Gunakan kabel yang sesuai untuk beban AC

## 📚 Library Dependencies

Install via Arduino IDE Library Manager:

1. **WiFi** (built-in ESP32) - Koneksi WiFi
2. **WiFiClientSecure** (built-in ESP32) - TLS/SSL untuk MQTT
3. **PubSubClient** by Nick O'Leary `v2.8+` - MQTT client
4. **ArduinoJson** by Benoit Blanchon `v6.21+` - JSON parsing

**Cara Install**:
```
Arduino IDE → Tools → Manage Libraries → Search library name → Install
```

## ⚙️ Setup Instructions (Step by Step)

### Step 1: Copy Configuration Template

```bash
cd Hardware
cp config.py config.h
```

### Step 2: Edit Credentials di `config.h`

**WiFi Settings**:
```cpp
const char* WIFI_SSID = "NamaWiFiAnda";       // Ganti dengan WiFi rumah
const char* WIFI_PASSWORD = "PasswordWiFi";    // Ganti dengan password WiFi
```

**MQTT Settings** (harus sama dengan backend/.env):
```cpp
const char* MQTT_BROKER = "xxxxx.s1.eu.hivemq.cloud";  // MQTT broker address
const int MQTT_PORT = 8883;                             // TLS port (wajib)
const char* MQTT_USERNAME = "SMART_AI_IoT";             // MQTT username
const char* MQTT_PASSWORD = "YourMQTTPassword";         // MQTT password
```

**Device Identity** (setiap device HARUS unik):
```cpp
const char* HOME_ID = "mikohome";                       // ID rumah Anda
const char* DEVICE_ID = "light_lamp_outdoor_f9gv";      // ID device (unik!)
const char* MQTT_CLIENT_ID = "esp32_light_outdoor_f9gv"; // Client ID (unik!)
```

**Naming Convention**:
- HOME_ID: nama rumah (e.g., `mikohome`, `arinhome`)
- DEVICE_ID: `{type}_{location}_{random}` (e.g., `light_lamp_outdoor_f9gv`)
- MQTT_CLIENT_ID: `esp32_{location}_{random}` (e.g., `esp32_light_outdoor_f9gv`)

### Step 3: Configure Pin (Optional)

Jika menggunakan GPIO pin lain:
```cpp
const int RELAY_PIN = 4;  // Default GPIO 4, ubah jika perlu
```

### Step 4: Create Arduino Sketch

Rename `main.py` ke `main.ino` atau copy code ke Arduino IDE sketch baru.

### Step 5: Upload ke ESP32

1. Buka Arduino IDE
2. **Tools → Board** → pilih `ESP32 Dev Module`
3. **Tools → Port** → pilih port USB ESP32
4. **Tools → Upload Speed** → `115200`
5. Klik tombol **Upload** (→)

### Step 6: Monitor Serial Output

1. **Tools → Serial Monitor**
2. Set baud rate: `115200`
3. Tunggu hingga muncul:
   ```
   ✓ WiFi connected
   ✓ MQTT connected
   ✓ Subscribed to: mikohome/light_lamp_outdoor_f9gv/set
   ```

## 📡 MQTT Communication Pattern

### 🔽 SUBSCRIBE (Terima Perintah dari Backend)

ESP32 **subscribe** ke topic:
```
/{home_id}/{device_id}/set
```

**Contoh**:
```
mikohome/light_lamp_outdoor_f9gv/set
```

**Payload yang diterima** (JSON):
```json
{
  "state": "on",
  "timestamp": 1735900000
}
```

**Action ESP32**:
- Parse JSON
- Extract `state` field
- Jika `"on"` → `digitalWrite(RELAY_PIN, HIGH)` → relay close → lampu nyala
- Jika `"off"` → `digitalWrite(RELAY_PIN, LOW)` → relay open → lampu mati
- Publish status update ke topic `status` (lihat di bawah)

### 🔼 PUBLISH (Kirim Status ke Backend)

ESP32 **publish** ke topic:
```
/{home_id}/{device_id}/status
```

**Contoh**:
```
mikohome/light_lamp_outdoor_f9gv/status
```

**Payload yang dikirim** (JSON):
```json
{
  "state": "off",
  "timestamp": 1735900123
}
```

**Kapan publish**:
1. Setelah terima command dari `/set` → publish status baru
2. Setelah boot/reconnect → publish status awal
3. Setiap 30 detik → heartbeat (optional)

### 📊 Flow Diagram

```
Backend                    MQTT Broker                    ESP32 Device
   │                            │                              │
   │ 1. Publish                 │                              │
   │  {state:"on"}              │                              │
   ├───────────────────────────→│                              │
   │  Topic: mikohome/lamp/set  │                              │
   │                            │  2. Forward                  │
   │                            ├─────────────────────────────→│
   │                            │                              │ 3. Execute
   │                            │                              │    digitalWrite(4, HIGH)
   │                            │                              │    Relay CLOSE → Lampu ON
   │                            │                              │
   │                            │  4. Publish status           │
   │                            │←─────────────────────────────┤
   │                            │  {state:"on"}                │
   │  5. Receive status         │  Topic: mikohome/lamp/status │
   │←───────────────────────────┤                              │
   │                            │                              │
   │  6. Update DB & notify UI  │                              │
   │                            │                              │
```

## 🧪 Testing

### Test 1: Serial Monitor Check

Setelah upload, buka Serial Monitor dan pastikan:
```
[WiFi] Connecting to NamaWiFiAnda...
[WiFi] ✓ Connected! IP: 192.168.1.100

[MQTT] Connecting to broker...
[MQTT] ✓ Connected to HiveMQ Cloud
[MQTT] ✓ Subscribed to: mikohome/light_lamp_outdoor_f9gv/set

[Device] Ready. Waiting for commands...
```

### Test 2: Manual MQTT Publish

Gunakan MQTT client (MQTTX, mosquitto_pub, atau backend test script):
```bash
# Publish command untuk nyalakan lampu
mosquitto_pub -h "xxxxx.s1.eu.hivemq.cloud" -p 8883 \
  -u "SMART_AI_IoT" -P "password" --cafile ca.crt \
  -t "mikohome/light_lamp_outdoor_f9gv/set" \
  -m '{"state":"on","timestamp":1735900000}'
```

**Expected**: 
- Relay click → lampu nyala
- Serial Monitor: `[MQTT] Received: {"state":"on",...}`
- Backend receive status update via `status` topic

### Test 3: Backend Integration

```bash
# Via backend API
curl -X POST "http://localhost:8000/api/v1/homes/mikohome/devices/light_lamp_outdoor_f9gv/toggle" \
  -H "Content-Type: application/json" \
  -d '{"state":"off"}'
```

## 🐛 Troubleshooting

### WiFi Tidak Connect

**Gejala**: Serial monitor stuck di "Connecting to WiFi..."

**Solusi**:
- ✓ Cek SSID dan password di `config.h`
- ✓ Pastikan WiFi 2.4GHz (ESP32 tidak support 5GHz)
- ✓ Cek jarak ESP32 dari router
- ✓ Restart ESP32 (tekan tombol RESET)

### MQTT Tidak Connect

**Gejala**: "MQTT connection failed, rc=-2" atau "rc=-4"

**Solusi**:
- ✓ Cek MQTT_BROKER, USERNAME, PASSWORD di `config.h`
- ✓ Pastikan pakai port 8883 (TLS), bukan 1883
- ✓ Cek internet connection (ping google.com)
- ✓ Cek HiveMQ Cloud dashboard (broker aktif?)

**Error Codes**:
- `-2`: Connect timeout → cek network/broker
- `-4`: Authentication failed → cek username/password
- `-5`: Not authorized → cek permissions di broker

### Relay Tidak Bekerja

**Gejala**: Lampu tidak nyala/mati walau command terkirim

**Solusi**:
- ✓ Cek wiring GPIO 4 → Relay IN
- ✓ Cek power relay (butuh 5V dari VIN)
- ✓ Test manual: tambah di `setup()`:
  ```cpp
  digitalWrite(RELAY_PIN, HIGH); delay(2000);
  digitalWrite(RELAY_PIN, LOW);  delay(2000);
  ```
- ✓ Pastikan relay module bukan inverted logic (some relay active LOW)
- ✓ Ukur voltage di GPIO 4 (should be ~3.3V when HIGH)

### Device Tidak Muncul di Dashboard

**Gejala**: Frontend tidak tampilkan device

**Solusi**:
1. Cek device sudah registered di backend:
   ```bash
   curl "http://localhost:8000/api/v1/homes/mikohome/devices"
   ```
2. Jika belum, register manual:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/homes/mikohome/devices" \
     -H "Content-Type: application/json" \
     -d '{"device_id":"light_lamp_outdoor_f9gv","device_type":"relay","room":"outdoor"}'
   ```
3. Cek ESP32 sudah publish status ke topic `status`

## 📱 Multiple Devices

### Menambah Device Kedua (dan seterusnya)

1. **Copy sketch ke folder baru** atau buat sketch baru
2. **Edit `config.h`** dengan identitas UNIK:
   ```cpp
   const char* DEVICE_ID = "light_lamp_indoor_2";        // BEDA dari device 1
   const char* MQTT_CLIENT_ID = "esp32_light_indoor_2";  // BEDA dari device 1
   ```
3. **Upload ke ESP32 kedua**
4. **Register di backend** dengan `device_id` yang sama

**PENTING**: Setiap device HARUS punya `DEVICE_ID` dan `MQTT_CLIENT_ID` yang unik!

### Device ID Naming Convention

| Device Type | Format | Contoh |
|-------------|--------|--------|
| Lampu | `light_{location}_{random}` | `light_lamp_outdoor_f9gv` |
| Kipas | `fan_{location}_{random}` | `fan_living_room_a3kx` |
| AC | `ac_{location}_{random}` | `ac_bedroom_master_7j2p` |
| Smart Plug | `plug_{location}_{random}` | `plug_kitchen_fridge_9m4s` |

**Generate random suffix**: https://randomkeygen.com/ (ambil 4 karakter)

## 🚀 Next Steps

1. ✅ Upload code ke ESP32
2. ✅ Verify di Serial Monitor (WiFi + MQTT connected)
3. ✅ Register device di backend via API
4. ✅ Test toggle dari dashboard UI
5. ✅ Test AI chat: "nyalakan lampu outdoor"

Kembali ke [Root README](../README.md) untuk dokumentasi lengkap.

---

**Last Updated**: 2026-09-14

## Testing
1. Buka Serial Monitor (115200 baud)
2. Tunggu hingga WiFi dan MQTT connected
3. Coba kontrol dari Frontend atau test via MQTT client
4. Monitor output relay di pin 4

## Troubleshooting

### WiFi tidak connect
- Pastikan SSID dan password benar
- Cek jarak sinyal WiFi
- Restart ESP32

### MQTT tidak connect
- Pastikan credentials MQTT benar
- Cek koneksi internet
- Pastikan HiveMQ Cloud broker aktif

### Relay tidak bekerja
- Cek wiring pin GPIO 4
- Cek power supply relay (butuh 5V)
- Test manual: `digitalWrite(4, HIGH);`

## Multiple Devices
Untuk menambah device baru:
1. Copy file `.ino`
2. Ubah `DEVICE_ID` dan `MQTT_CLIENT_ID` (harus unique!)
3. Ubah `RELAY_PIN` sesuai kebutuhan
4. Upload ke ESP32 baru
