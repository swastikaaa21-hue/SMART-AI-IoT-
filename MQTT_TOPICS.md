# 📋 MQTT Topics Reference - Quick Guide

Referensi lengkap format topic dan payload MQTT untuk Smart AI IoT platform.

## 🎯 Topic Pattern Overview

```
/{home_id}/{device_id}/{action}

Dimana:
- home_id   : ID rumah (e.g., mikohome, arinhome)
- device_id : ID device yang unik (e.g., light_lamp_outdoor_f9gv)
- action    : set | status
```

## 📤 Command Topics (Backend → Device)

### Topic Format
```
/{home_id}/{device_id}/set
```

### Siapa yang PUBLISH?
**Backend (FastAPI)** - saat:
- User klik toggle di dashboard
- User konfirmasi AI command
- Timer scheduled trigger

### Siapa yang SUBSCRIBE?
**ESP32 Device** - mendengarkan command untuk device tersebut

### Payload Schema

```json
{
  "state": "on",
  "timestamp": 1735900000
}
```

| Field | Type | Values | Required | Description |
|-------|------|--------|----------|-------------|
| `state` | string | `"on"` or `"off"` | ✅ Yes | Target state untuk device |
| `timestamp` | integer | Unix timestamp | ✅ Yes | Waktu command dikirim (seconds since epoch) |

### Examples

#### Example 1: Nyalakan lampu outdoor di mikohome

**Topic**:
```
mikohome/light_lamp_outdoor_f9gv/set
```

**Payload**:
```json
{
  "state": "on",
  "timestamp": 1726318027
}
```

**ESP32 Action**:
```cpp
digitalWrite(RELAY_PIN, HIGH);  // Relay close → Lampu nyala
publishStatus("on");            // Kirim konfirmasi ke backend
```

---

#### Example 2: Matikan kipas ruang tamu di arinhome

**Topic**:
```
arinhome/fan_living_room_a3kx/set
```

**Payload**:
```json
{
  "state": "off",
  "timestamp": 1726318090
}
```

**ESP32 Action**:
```cpp
digitalWrite(RELAY_PIN, LOW);   // Relay open → Kipas mati
publishStatus("off");           // Kirim konfirmasi ke backend
```

---

## 📥 Status Topics (Device → Backend)

### Topic Format
```
/{home_id}/{device_id}/status
```

### Siapa yang PUBLISH?
**ESP32 Device** - saat:
- Setelah eksekusi command (konfirmasi state berhasil diubah)
- Setelah boot/reconnect (report initial state)
- Heartbeat periodic (optional, tiap 30-60 detik)

### Siapa yang SUBSCRIBE?
**Backend (FastAPI)** - untuk update database dan broadcast ke frontend

### Payload Schema

```json
{
  "state": "off",
  "timestamp": 1735900123
}
```

| Field | Type | Values | Required | Description |
|-------|------|--------|----------|-------------|
| `state` | string | `"on"`, `"off"`, `"unknown"` | ✅ Yes | State aktual device saat ini |
| `timestamp` | integer | Unix timestamp | ✅ Yes | Waktu status dikirim (seconds since epoch) |

### Examples

#### Example 1: Device report status ON setelah eksekusi command

**Topic**:
```
mikohome/light_lamp_outdoor_f9gv/status
```

**Payload**:
```json
{
  "state": "on",
  "timestamp": 1726318028
}
```

**Backend Action**:
```python
# Update database
await db.update_device_status("light_lamp_outdoor_f9gv", "on")

# Broadcast via WebSocket ke frontend
await ws_manager.broadcast({
    "type": "device_status_update",
    "device_id": "light_lamp_outdoor_f9gv",
    "state": "on"
})
```

---

#### Example 2: Device report initial state setelah boot

**Topic**:
```
mikohome/light_lamp_outdoor_f9gv/status
```

**Payload**:
```json
{
  "state": "unknown",
  "timestamp": 1726318000
}
```

**Use Case**: ESP32 baru boot, belum tahu state relay terakhir

---

## 🔄 Complete Flow Examples

### Flow 1: User Toggle Manual dari Dashboard

```
┌──────────┐
│ Frontend │ User klik toggle button "ON"
└────┬─────┘
     │ POST /api/v1/homes/mikohome/devices/light_lamp_outdoor_f9gv/toggle
     │ Body: {"state": "on"}
     ▼
┌──────────┐
│ Backend  │ 
└────┬─────┘
     │ MQTT PUBLISH
     │ Topic: mikohome/light_lamp_outdoor_f9gv/set
     │ Payload: {"state":"on","timestamp":1726318027}
     ▼
┌──────────┐
│  MQTT    │ HiveMQ Cloud broker routes message
│  Broker  │
└────┬─────┘
     │ Forward to subscriber (ESP32)
     ▼
┌──────────┐
│  ESP32   │ SUBSCRIBE callback triggered
└────┬─────┘
     │ digitalWrite(RELAY_PIN, HIGH) → Lampu nyala
     │
     │ MQTT PUBLISH (konfirmasi)
     │ Topic: mikohome/light_lamp_outdoor_f9gv/status
     │ Payload: {"state":"on","timestamp":1726318028}
     ▼
┌──────────┐
│  MQTT    │ Broker routes status message
│  Broker  │
└────┬─────┘
     │ Forward to subscriber (Backend)
     ▼
┌──────────┐
│ Backend  │ SUBSCRIBE callback triggered
└────┬─────┘
     │ Update database: device.state = "on"
     │ WebSocket broadcast ke frontend
     ▼
┌──────────┐
│ Frontend │ WebSocket onMessage
└──────────┘ Update UI: device card icon → yellow (ON)
```

**Timeline**:
- T+0ms: User click
- T+50ms: Backend MQTT publish
- T+200ms: ESP32 receive, relay switch
- T+250ms: ESP32 MQTT publish status
- T+350ms: Backend receive status, update DB
- T+400ms: Frontend receive WebSocket update, UI refresh

**Total latency**: ~400ms end-to-end

---

### Flow 2: AI Command dengan Konfirmasi

```
┌──────────┐
│ Frontend │ User chat: "matikan lampu outdoor"
└────┬─────┘
     │ POST /api/v1/homes/mikohome/chat
     │ Body: {"message":"matikan lampu outdoor"}
     ▼
┌──────────┐
│ Backend  │ Gemini AI analyze → detect command intent
└────┬─────┘
     │ Return: {"type":"confirmation_required","action_id":"act_123",...}
     ▼
┌──────────┐
│ Frontend │ Render ConfirmationBubble dengan tombol [Lanjutkan] [Batalkan]
└────┬─────┘
     │ (User click "Lanjutkan")
     │ POST /api/v1/homes/mikohome/chat/confirm
     │ Body: {"action_id":"act_123","confirm":true}
     ▼
┌──────────┐
│ Backend  │ Retrieve action dari cache, execute
└────┬─────┘
     │ MQTT PUBLISH
     │ Topic: mikohome/light_lamp_outdoor_f9gv/set
     │ Payload: {"state":"off","timestamp":1726318100}
     ▼
     
(Lanjut sama seperti Flow 1: ESP32 execute → publish status → backend update DB → frontend update UI)
```

---

## 🔍 Topic Wildcard Patterns

### Backend Subscription Patterns

```python
# Subscribe semua device di mikohome
mqtt_client.subscribe("mikohome/+/status")

# Subscribe semua home
mqtt_client.subscribe("+/+/status")

# Subscribe specific device
mqtt_client.subscribe("mikohome/light_lamp_outdoor_f9gv/status")
```

### MQTTX Monitor Patterns

Untuk debugging, gunakan MQTTX dengan patterns:

```
# Monitor semua traffic di mikohome
mikohome/#

# Monitor semua command
+/+/set

# Monitor semua status
+/+/status

# Monitor everything
#
```

---

## 🛠️ Testing Topics dengan MQTTX

### 1. Install MQTTX
Download: https://mqttx.app/

### 2. Connect ke Broker

```
Name: Smart IoT Broker
Host: mqtt://<your-cluster-id>.s1.eu.hivemq.cloud
Port: 8883
Username: SMART_AI_IoT
Password: <your-password>
SSL/TLS: Enable
```

### 3. Subscribe untuk Monitor

Topic: `mikohome/#`

### 4. Publish Test Command

**Topic**: `mikohome/light_lamp_outdoor_f9gv/set`

**Payload**:
```json
{
  "state": "on",
  "timestamp": 1726318027
}
```

**Expected**: 
- ESP32 relay switch ON
- Status message muncul di MQTTX: `mikohome/light_lamp_outdoor_f9gv/status`

---

## 📊 Topic Naming Best Practices

### ✅ Good Device IDs

```
light_lamp_outdoor_f9gv        # Clear: type_location_suffix
fan_living_room_a3kx           # Clear
ac_bedroom_master_7j2p         # Clear
plug_kitchen_fridge_9m4s       # Clear
```

### ❌ Bad Device IDs

```
device1                        # Not descriptive
lamp                           # Not unique
outdoor-light                  # Use underscore, not dash
Light_Outdoor                  # Lowercase only
light lamp outdoor             # No spaces
```

### Device ID Format

```
{device_type}_{location}_{random_suffix}

device_type: light, fan, ac, plug, sensor
location: outdoor, living_room, bedroom, kitchen
random_suffix: 4 alphanumeric characters (untuk uniqueness)
```

**Generate random suffix**:
```bash
# Linux/Mac
echo $RANDOM | md5sum | head -c 4

# Windows PowerShell
-join ((48..57) + (97..122) | Get-Random -Count 4 | % {[char]$_})
```

---

## 🔐 Security Considerations

### Topic ACLs (HiveMQ Cloud)

**Backend credentials** (SMART_AI_IoT):
```
Publish: {home_id}/+/set      ✅ Allow
Subscribe: {home_id}/+/status  ✅ Allow
Subscribe: {home_id}/+/set     ❌ Deny (tidak perlu)
Publish: {home_id}/+/status    ❌ Deny (hanya device yang publish)
```

**Device credentials** (per-device - optional untuk production):
```
Device: esp32_light_outdoor_f9gv
Subscribe: mikohome/light_lamp_outdoor_f9gv/set     ✅ Allow only own topic
Publish: mikohome/light_lamp_outdoor_f9gv/status    ✅ Allow only own topic
Subscribe: mikohome/+/set                            ❌ Deny (tidak boleh listen device lain)
```

### Message Validation

**Backend harus validate** sebelum publish:
```python
def validate_command_payload(payload: dict) -> bool:
    if "state" not in payload:
        return False
    if payload["state"] not in ["on", "off"]:
        return False
    if "timestamp" not in payload:
        return False
    return True
```

**ESP32 harus validate** sebelum execute:
```cpp
bool validatePayload(JsonDocument& doc) {
  if (!doc.containsKey("state")) return false;
  String state = doc["state"];
  if (state != "on" && state != "off") return false;
  return true;
}
```

---

## 📈 Scaling Considerations

### Multiple Homes

**Isolasi per home**:
```
mikohome/+/status    → Backend instance 1 (Miko's home)
arinhome/+/status    → Backend instance 2 (Arin's home)
cheetahhome/+/status → Backend instance 3 (Cheetah's home)
```

Atau single backend subscribe all:
```
+/+/status           → Single backend (route by home_id in handler)
```

### Topic Length Limit

MQTT topic max length: **65535 bytes** (praktis: keep < 100 chars)

**OK**:
```
mikohome/light_lamp_outdoor_f9gv/status  (44 chars)
```

**Too long** (avoid):
```
mikohome/light_lamp_outdoor_very_long_location_name_with_serial_12345678/status
```

### Message Rate Limit

**HiveMQ Cloud Free Tier**:
- Max 100 messages/second
- Max 25 concurrent connections

**Jika exceed** → upgrade ke paid plan atau optimize:
- Batch status updates (send every 5s, not every 100ms)
- Use retained messages untuk last state
- Implement rate limiting di ESP32

---

## 🧪 Testing Checklist

- [ ] Backend subscribe `+/+/status` berhasil
- [ ] ESP32 subscribe `{home_id}/{device_id}/set` berhasil
- [ ] Publish command dari backend → ESP32 terima
- [ ] ESP32 publish status → Backend terima
- [ ] Payload JSON valid (test dengan JSON validator)
- [ ] Timestamp format correct (Unix epoch seconds)
- [ ] Device ID matching exact (case-sensitive)
- [ ] QoS level 1 (at least once delivery)
- [ ] Retained message untuk last status (optional)

---

## 📚 References

- [MQTT v3.1.1 Specification](https://mqtt.org/mqtt-specification/)
- [HiveMQ Documentation](https://www.hivemq.com/docs/)
- [PubSubClient Library (Arduino)](https://pubsubclient.knolleary.net/)
- [Project Architecture](ARCHITECTURE.md)
- [API Contract v3](smart-ai-iot-job-spec-v3.md)

---

**Last Updated**: 2026-09-14
