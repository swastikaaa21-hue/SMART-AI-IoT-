# Smart AI IoT — Job Spec & Integration Contract (v3 — PATEN)

> **STATUS: LOCKED.** Struktur topic MQTT dan REST API endpoint di dokumen ini adalah kontrak final.
> Tidak boleh diubah sepihak oleh siapapun (termasuk AI assistant lain / tools code-gen).
> Perubahan hanya lewat approval di file ini, versi naik jadi v4, dst.
>
> **Perubahan dari v2**: tambah logika intent classification — bedakan perintah eksekusi (butuh konfirmasi) vs obrolan biasa (langsung tampil, tanpa konfirmasi).

---

## 1. Shared Config (WAJIB SAMA untuk semua job)

```
MQTT_BROKER   = "xxxxxxxx.s1.eu.hivemq.cloud"
MQTT_PORT     = 8883                             # TLS wajib
MQTT_USERNAME = "smart_ai_iot_user"
MQTT_PASSWORD = "<simpan di .env, jangan hardcode>"
```

### 1.1 Topic Convention (PATEN)

#### Format Standar
```
/{home_id}/{device_id}/set       → Backend PUBLISH command ke device (perintah kontrol)
/{home_id}/{device_id}/status    → Device PUBLISH status ke backend (laporan status)
```

#### Contoh Konkret
```
mikohome/light_lamp_outdoor_f9gv/set       → Backend kirim command "nyalakan lampu"
mikohome/light_lamp_outdoor_f9gv/status    → ESP32 kirim status "lampu sudah nyala"

arinhome/fan_living_room_a3kx/set          → Backend kirim command "nyalakan kipas"
arinhome/fan_living_room_a3kx/status       → ESP32 kirim status "kipas sudah nyala"
```

#### Home IDs Aktif
- `mikohome` - Rumah Miko
- `arinhome` - Rumah Arin  
- `cheetahhome` - Rumah Cheetah

#### Device ID Naming Convention
Format: `{type}_{location}_{random_suffix}`

Contoh:
- `light_lamp_outdoor_f9gv` - Lampu outdoor dengan suffix random f9gv
- `fan_living_room_a3kx` - Kipas ruang tamu dengan suffix random a3kx
- `ac_bedroom_master_7j2p` - AC kamar utama dengan suffix random 7j2p

**PENTING**: Setiap device HARUS punya `device_id` yang UNIK di dalam satu `home_id`.

### 1.2 Payload JSON Standar (PATEN)

#### Command Payload (Backend → Device via `/set` topic)
```json
{
  "state": "on",
  "timestamp": 1735900000
}
```

**Field Explanation**:
- `state`: String `"on"` atau `"off"` - perintah nyalakan/matikan device
- `timestamp`: Unix timestamp (integer) - waktu command dikirim

#### Status Payload (Device → Backend via `/status` topic)
```json
{
  "state": "off",
  "timestamp": 1735900123
}
```

**Field Explanation**:
- `state`: String `"on"` atau `"off"` - status aktual device saat ini
- `timestamp`: Unix timestamp (integer) - waktu status dikirim

#### Supported States
- `"on"` - Device menyala/aktif
- `"off"` - Device mati/nonaktif

### 1.3 Device Registry
Device didaftarkan lewat tabel `devices` (bukan hardcode). Lihat § 2.5 endpoint admin.

---

## 2. REST API Contract (PATEN — v1)

Base URL: `https://<backend-domain>/api/v1`

| Method | Endpoint | Body | Fungsi |
|---|---|---|---|
| GET | `/homes/{home_id}/devices` | - | List device + status |
| POST | `/homes/{home_id}/devices/{device_id}/toggle` | `{"state":"on"}` | Kontrol manual |
| POST | `/homes/{home_id}/devices/{device_id}/timer` | `{"action":"off","datetime":"..."}` | Set timer manual |
| POST | `/homes/{home_id}/chat` | `{"message":"..."}` | Kirim prompt AI |
| POST | `/homes/{home_id}/chat/confirm` | `{"action_id":"...","confirm":true}` | **BARU** — konfirmasi/batalkan eksekusi AI |
| POST | `/homes/{home_id}/devices` (admin) | `{"device_id":"lamp2","device_type":"relay","room":"bedroom"}` | Tambah device baru |

### 2.1 Response format standar (PATEN)
```json
{ "success": true, "data": { }, "error": null }
```

### 2.2 Response Schema `/chat` — DUA TIPE (PATEN, ini inti logika baru)

**Tipe A — Perintah eksekusi terdeteksi → butuh konfirmasi:**
```json
{
  "success": true,
  "data": {
    "type": "confirmation_required",
    "action_id": "act_9f2a1b",
    "intent_summary": "Mematikan lampu1 di mikohome",
    "proposed_action": {
      "tool": "set_device_state",
      "home_id": "mikohome",
      "device_id": "lamp1",
      "state": "off"
    },
    "expires_in": 60
  },
  "error": null
}
```
Atau untuk timer:
```json
{
  "data": {
    "type": "confirmation_required",
    "action_id": "act_7c31d0",
    "intent_summary": "Set timer mati jam 22:00 di mikohome lampu1",
    "proposed_action": {
      "tool": "set_timer",
      "home_id": "mikohome",
      "device_id": "lamp1",
      "action": "off",
      "datetime": "2026-09-05T22:00:00"
    },
    "expires_in": 60
  }
}
```

**Tipe B — Obrolan biasa (tanya-tanya/curhat) → langsung tampil, TANPA konfirmasi:**
```json
{
  "success": true,
  "data": {
    "type": "chat",
    "message": "Oh gitu, kalau lampu keseringan mati nyala emang bisa mempercepat kerusakan relay. Mau aku bantu cek jadwal pemakaiannya?"
  },
  "error": null
}
```

> **Field `type` ini yang jadi switch utama frontend** — bukan menebak dari isi teks. Backend yang wajib menentukan `type`, frontend tinggal render sesuai `type`.

### 2.3 Response `/chat/confirm`
```json
{
  "success": true,
  "data": {
    "executed": true,
    "result": "Lampu1 di mikohome berhasil dimatikan"
  },
  "error": null
}
```
Jika `confirm: false` (user batalkan):
```json
{
  "success": true,
  "data": { "executed": false, "result": "Perintah dibatalkan" },
  "error": null
}
```
Jika `action_id` sudah expired (lewat `expires_in`):
```json
{ "success": false, "data": null, "error": "action_expired" }
```

### 2.4 Aturan Integrasi
- Backend **wajib** klasifikasi intent dulu sebelum eksekusi apapun (lihat § 4.2 logic).
- Tombol manual (toggle/timer langsung dari UI) **tetap tanpa konfirmasi** — konfirmasi HANYA untuk hasil terjemahan AI dari chat, karena AI bisa salah interpretasi.
- `action_id` disimpan sementara (cache/Redis/DB dengan TTL, default 60 detik) — bukan langsung eksekusi ke MQTT saat `/chat` dipanggil.

### 2.5 Endpoint Admin (tambah device)
```
POST /homes/{home_id}/devices
Body: {"device_id":"lamp2","device_type":"relay","room":"bedroom"}
```

---

## 3. JOB 1 — FRONTEND (Next.js + Tailwind)

### 3.1 Tugas Dasar
1. Dashboard device: fetch `GET /homes/{home_id}/devices`, render `DeviceCard`
2. `TimerModal` → `POST /homes/{home_id}/devices/{device_id}/timer` (manual, langsung eksekusi, tanpa konfirmasi)
3. `ChatBox` fixed di bawah → `POST /homes/{home_id}/chat`

### 3.2 Logika Render Chat Response (BARU — wajib ikuti `type`)

```javascript
async function handleChatResponse(response) {
  const { data } = response;

  if (data.type === "chat") {
    // Tampilkan sebagai bubble teks biasa, SELESAI, tidak ada tombol apapun
    renderChatBubble(data.message);
    return;
  }

  if (data.type === "confirmation_required") {
    // Tampilkan bubble + intent_summary + 2 tombol: Lanjutkan / Batalkan
    renderConfirmationBubble({
      text: data.intent_summary,
      actionId: data.action_id,
      onConfirm: () => confirmAction(data.action_id, true),
      onCancel: () => confirmAction(data.action_id, false),
      expiresIn: data.expires_in
    });
  }
}

async function confirmAction(actionId, confirm) {
  const res = await fetch(`${API_BASE}/homes/${homeId}/chat/confirm`, {
    method: "POST",
    body: JSON.stringify({ action_id: actionId, confirm })
  });
  const result = await res.json();
  renderChatBubble(result.data.result); // tampilkan hasil eksekusi/pembatalan
}
```

### 3.3 Komponen UI Baru
- `ConfirmationBubble`: bubble chat khusus dengan 2 tombol (`Lanjutkan` / `Batalkan`) + countdown visual dari `expires_in`
- Kalau `expires_in` habis tanpa aksi user → tombol otomatis disable, tampilkan teks "Waktu konfirmasi habis"

### 3.4 Aturan Integrasi
- Frontend **tidak boleh** menebak sendiri apakah pesan itu perintah atau obrolan — 100% ikut field `type` dari backend.
- Tombol manual dashboard (toggle langsung) **tidak pernah** memunculkan `ConfirmationBubble` — itu hanya untuk hasil `/chat`.

### Deliverable
- Komponen baru: `ConfirmationBubble`
- Update `ChatBox` untuk switch render berdasarkan `data.type`

---

## 4. JOB 2 — BACKEND API (Python FastAPI)

### 4.1 Alur Logika `/chat` (BARU — inti perubahan)

```
User kirim message ke /chat
        │
        ▼
LLM (function calling) analisa message
        │
        ├─ LLM TIDAK panggil tool (pure text response)
        │       → berarti user cuma nanya/curhat/ngobrol
        │       → return { type: "chat", message: <teks dari LLM> }
        │       → tampilkan lalu jika user ingin chat lagi bisa disana langsung tanpa pindah
        │
        └─ LLM PANGGIL tool (set_device_state / set_timer)
                → JANGAN eksekusi langsung ke MQTT
                → simpan proposed_action + generate action_id (TTL 60s)
                → return { type: "confirmation_required", action_id, intent_summary, proposed_action }
                → tunggu user hit /chat/confirm
```

### 4.2 Implementasi (pseudocode)

```python
import uuid
import time

pending_actions = {}  # gunakan Redis di production, bukan dict in-memory

def handle_chat(home_id: str, message: str):
    llm_response = call_llm_with_tools(message, tools=[SET_DEVICE_STATE_TOOL, SET_TIMER_TOOL])

    if llm_response.tool_call is None:
        # User hanya ngobrol/tanya, bukan perintah
        return {
            "type": "chat",
            "message": llm_response.text
        }

    # User mengeluarkan perintah -> AI menerjemahkan ke tool call
    tool_call = llm_response.tool_call
    action_id = f"act_{uuid.uuid4().hex[:8]}"

    pending_actions[action_id] = {
        "home_id": home_id,
        "tool": tool_call.name,
        "params": tool_call.params,
        "created_at": time.time(),
        "ttl": 60
    }

    return {
        "type": "confirmation_required",
        "action_id": action_id,
        "intent_summary": generate_human_summary(tool_call),  # "Mematikan lampu1 di mikohome"
        "proposed_action": tool_call.params,
        "expires_in": 60
    }


def handle_chat_confirm(home_id: str, action_id: str, confirm: bool):
    action = pending_actions.get(action_id)

    if action is None or (time.time() - action["created_at"]) > action["ttl"]:
        return {"success": False, "error": "action_expired"}

    if not confirm:
        del pending_actions[action_id]
        return {"success": True, "data": {"executed": False, "result": "Perintah dibatalkan"}}

    # Eksekusi via fungsi inti yang SAMA dengan tombol manual
    if action["tool"] == "set_device_state":
        result = set_device_state(**action["params"])
    elif action["tool"] == "set_timer":
        result = set_timer(**action["params"])

    del pending_actions[action_id]
    return {"success": True, "data": {"executed": True, "result": result}}
```

### 4.3 Prompt System untuk LLM (penting — supaya klasifikasi akurat)

```
Kamu adalah asisten smart home. Tugasmu:
1. Jika user memberi PERINTAH untuk mengontrol device (nyalakan/matikan/set timer),
   panggil tool yang sesuai (set_device_state atau set_timer). JANGAN jawab teks biasa.
2. Jika user hanya bertanya, ngobrol, curhat, atau minta saran/informasi
   (bukan perintah kontrol device), JANGAN panggil tool apapun.
   Jawab natural sebagai teks biasa.
3. Kalau ragu apakah itu perintah atau bukan, anggap itu OBROLAN BIASA (tool tidak dipanggil) —
   lebih aman daripada salah eksekusi device tanpa konfirmasi eksplisit.
```

> Tool call dari LLM itulah yang jadi sinyal klasifikasi — bukan keyword matching manual (`if "matikan" in message`), karena kalimat natural bisa sangat variatif ("bisa tolong matiin lampu ga", "lampu ruang tamu nyala terus nih ganggu", dll).

### 4.4 Aturan Integrasi
- `set_device_state()` dan `set_timer()` dari § JOB 2 v2 **tetap fungsi yang sama**, hanya sekarang dipanggil dari `handle_chat_confirm()`, bukan langsung dari `handle_chat()`.
- Tombol manual (endpoint toggle/timer biasa di § 2) **tidak lewat `pending_actions`** — itu tetap direct execute seperti sebelumnya, karena user sudah eksplisit klik tombol (bukan hasil terjemahan AI yang bisa salah).
- Gunakan Redis (bukan dict Python) untuk `pending_actions` di production, supaya tahan restart server & scalable multi-instance.

### Deliverable
- `ai_tools.py`: definisi tool `set_device_state`, `set_timer` untuk LLM function calling
- `chat_handler.py`: `handle_chat()`, `handle_chat_confirm()`, `generate_human_summary()`
- Storage pending action: Redis dengan key `action:{action_id}`, TTL 60s (auto-expire native Redis, tidak perlu cron cleanup manual)

---

## 5. JOB 3 — IoT DEVICE (ESP32 + Relay/IR)

Tidak ada perubahan dari v2 — device tetap subscribe `/{home_id}/{device_id}/set`, publish `/{home_id}/{device_id}/status`. Logika konfirmasi sepenuhnya di layer Backend+Frontend, device tidak perlu tahu soal ini.

### 5.1 MQTT Flow untuk Pemula (Step by Step)

#### Scenario: User minta AI matikan lampu outdoor

**Step 1**: User chat di frontend
```
User: "matikan lampu outdoor"
```

**Step 2**: Frontend kirim ke backend
```http
POST /api/v1/homes/mikohome/chat
Body: {"message": "matikan lampu outdoor"}
```

**Step 3**: Backend + AI analisa → butuh konfirmasi
```json
Response: {
  "type": "confirmation_required",
  "action_id": "act_9f2a1b",
  "intent_summary": "Mematikan light_lamp_outdoor_f9gv di mikohome",
  "proposed_action": {
    "tool": "set_device_state",
    "home_id": "mikohome",
    "device_id": "light_lamp_outdoor_f9gv",
    "state": "off"
  }
}
```

**Step 4**: Frontend tampilkan bubble konfirmasi dengan 2 tombol

**Step 5**: User klik tombol "Lanjutkan"
```http
POST /api/v1/homes/mikohome/chat/confirm
Body: {"action_id": "act_9f2a1b", "confirm": true}
```

**Step 6**: Backend PUBLISH ke MQTT topic `/set`
```
Topic: mikohome/light_lamp_outdoor_f9gv/set
Payload: {"state": "off", "timestamp": 1735900000}
```

**Step 7**: ESP32 SUBSCRIBE topic `/set` → terima command
```cpp
// ESP32 callback function
void callback(char* topic, byte* payload, unsigned int length) {
  // Parse JSON: {"state": "off", "timestamp": 1735900000}
  String state = doc["state"];  // "off"
  
  if (state == "off") {
    digitalWrite(RELAY_PIN, LOW);  // Matikan relay
  }
  
  // Publish status update
  publishStatus("off");
}
```

**Step 8**: ESP32 PUBLISH status ke topic `/status`
```
Topic: mikohome/light_lamp_outdoor_f9gv/status
Payload: {"state": "off", "timestamp": 1735900123}
```

**Step 9**: Backend SUBSCRIBE topic `/status` → terima status
```python
# Backend handler
async def handle_device_status(topic: str, payload: dict):
    # topic = "mikohome/light_lamp_outdoor_f9gv/status"
    # payload = {"state": "off", "timestamp": 1735900123}
    
    # Update database
    await db.update_device_status(device_id, payload["state"])
    
    # Notify frontend via WebSocket
    await ws_manager.broadcast_status_update(device_id, payload["state"])
```

**Step 10**: Frontend update UI via WebSocket
```javascript
// Frontend WebSocket listener
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Update device card: lampu outdoor → OFF (grey icon)
  updateDeviceCard(data.device_id, data.state);
};
```

### 5.2 MQTT Subscribe/Publish Summary

#### ESP32 Device Role

**SUBSCRIBE** (Terima command dari backend):
```cpp
// Di setup()
mqttClient.subscribe("mikohome/light_lamp_outdoor_f9gv/set");

// Callback saat ada message
void callback(char* topic, byte* payload, unsigned int length) {
  // Parse JSON dan eksekusi command
  // Jika state="on" → digitalWrite(RELAY_PIN, HIGH)
  // Jika state="off" → digitalWrite(RELAY_PIN, LOW)
}
```

**PUBLISH** (Kirim status ke backend):
```cpp
void publishStatus(String state) {
  StaticJsonDocument<128> doc;
  doc["state"] = state;
  doc["timestamp"] = getUnixTimestamp();
  
  char buffer[128];
  serializeJson(doc, buffer);
  
  mqttClient.publish("mikohome/light_lamp_outdoor_f9gv/status", buffer);
}
```

#### Backend Role

**PUBLISH** (Kirim command ke device):
```python
# Saat user konfirmasi AI action atau klik tombol manual
await mqtt_service.publish(
    topic=f"{home_id}/{device_id}/set",
    payload={"state": "off", "timestamp": int(time.time())}
)
```

**SUBSCRIBE** (Terima status dari device):
```python
# Register handler saat startup
mqtt_service.on_status(handle_device_status)

# Handler dipanggil otomatis saat device publish status
async def handle_device_status(topic: str, payload: dict):
    # Update DB dan broadcast ke frontend
    pass
```

### 5.3 Deliverable Hardware

- `main.ino`: ESP32 Arduino sketch lengkap
- `config.h`: Template konfigurasi (WiFi, MQTT, Device ID)
- `README.md`: Setup guide lengkap dengan wiring diagram
- Testing checklist:
  - [ ] WiFi connect berhasil (Serial Monitor)
  - [ ] MQTT connect berhasil (Serial Monitor)
  - [ ] Subscribe topic `/set` berhasil
  - [ ] Terima command test → relay bekerja
  - [ ] Publish status ke `/status` berhasil
  - [ ] Backend terima status update

---

## 6. Checklist Sinkronisasi Antar Job (update v3)

- [ ] Backend selalu return field `type` (`"chat"` atau `"confirmation_required"`) di setiap response `/chat`
- [ ] Frontend switch render 100% berdasarkan `type`, tidak menebak sendiri dari isi teks
- [ ] Tombol manual dashboard tidak pernah trigger `ConfirmationBubble`
- [ ] `action_id` punya TTL (default 60 detik) dan expired dengan benar di backend
- [ ] LLM system prompt sudah diuji dengan variasi kalimat casual vs perintah (uji minimal 10 contoh masing-masing)
- [ ] Testing: user tanya "kenapa listrik boros ya" → harus jadi `type: chat`, TIDAK ada tombol konfirmasi
- [ ] Testing: user bilang "matikan lampu1 mikohome" → `type: confirmation_required`, klik Lanjutkan → device eksekusi
- [ ] Testing: user bilang "set timer mati jam 10 rumahmiko lampu1" → `type: confirmation_required` dengan `intent_summary` benar → klik Batalkan → tidak ada perubahan di device
