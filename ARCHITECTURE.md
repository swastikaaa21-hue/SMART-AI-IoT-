# 🏗️ Architecture Overview - Smart AI IoT

Dokumentasi arsitektur lengkap untuk memahami bagaimana semua komponen bekerja bersama.

## 📐 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                        │
├─────────────────────────────────────────────────────────────────────┤
│  Frontend (HTML/JS)                                                 │
│  - Device Dashboard (device cards with status)                      │
│  - Chat Interface (AI assistant)                                    │
│  - Confirmation Bubbles (untuk AI commands)                         │
│  - WebSocket Client (real-time updates)                             │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ HTTP REST API + WebSocket
                             │
┌────────────────────────────┴────────────────────────────────────────┐
│                      BACKEND ORCHESTRATOR LAYER                     │
├─────────────────────────────────────────────────────────────────────┤
│  FastAPI Application (Python)                                       │
│  ┌───────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  REST API     │  │  WebSocket   │  │  MQTT Handler          │  │
│  │  Endpoints    │  │  Manager     │  │  (Subscribe/Publish)   │  │
│  └───────┬───────┘  └──────┬───────┘  └──────┬─────────────────┘  │
│          │                  │                  │                     │
│  ┌───────┴──────────────────┴──────────────────┴─────────────────┐ │
│  │              Service Layer                                     │ │
│  │  - Gemini AI Service (function calling)                       │ │
│  │  - MQTT Service (async TLS client)                            │ │
│  │  - Device Service (CRUD + status management)                  │ │
│  │  - Action Cache (pending_actions for confirmation)            │ │
│  └────────────────────────────┬──────────────────────────────────┘ │
│                                │                                     │
│  ┌─────────────────────────────┴────────────────────────────────┐  │
│  │              Database Layer (SQLAlchemy async)               │  │
│  │  - Users, Homes, Devices, Timers tables                      │  │
│  │  - SQLite (dev) / PostgreSQL (production)                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ MQTT Protocol (TLS 8883)
                             │
┌────────────────────────────┴────────────────────────────────────────┐
│                      MQTT BROKER LAYER                              │
├─────────────────────────────────────────────────────────────────────┤
│  HiveMQ Cloud (Managed MQTT Broker)                                 │
│  - Topic routing: {home_id}/{device_id}/{set|status}                │
│  - TLS encryption (port 8883)                                       │
│  - Message persistence & QoS                                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ MQTT Protocol (TLS 8883)
                             │
┌────────────────────────────┴────────────────────────────────────────┐
│                      IoT DEVICE LAYER                               │
├─────────────────────────────────────────────────────────────────────┤
│  ESP32 Devices (C++/Arduino)                                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │  Device 1       │  │  Device 2       │  │  Device N       │    │
│  │  - WiFi Client  │  │  - WiFi Client  │  │  - WiFi Client  │    │
│  │  - MQTT Client  │  │  - MQTT Client  │  │  - MQTT Client  │    │
│  │  - Relay GPIO   │  │  - Relay GPIO   │  │  - Relay GPIO   │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow Patterns

### Pattern 1: Manual Device Control (Toggle Button)

```
User clicks toggle button
         │
         ▼
Frontend: POST /api/v1/homes/{home_id}/devices/{device_id}/toggle
         │ Body: {"state": "on"}
         ▼
Backend: Validate request
         │
         ├─ Update database (device.state = "on")
         │
         ├─ MQTT PUBLISH to topic: {home_id}/{device_id}/set
         │  Payload: {"state": "on", "timestamp": 1735900000}
         │
         └─ Return success response to frontend
         
         ▼ (MQTT Broker forwards message)
         
ESP32: SUBSCRIBE callback triggered
         │
         ├─ Parse JSON payload
         ├─ digitalWrite(RELAY_PIN, HIGH)  → Relay closes → Device ON
         │
         └─ MQTT PUBLISH to topic: {home_id}/{device_id}/status
            Payload: {"state": "on", "timestamp": 1735900123}
            
         ▼ (MQTT Broker forwards message)
         
Backend: SUBSCRIBE callback triggered (handle_device_status)
         │
         ├─ Update database (device.last_seen = now)
         │
         └─ WebSocket broadcast to all connected clients
         
         ▼
         
Frontend: WebSocket onMessage
         │
         └─ Update device card UI (icon → yellow, state → ON)
```

**Karakteristik**:
- ✅ Langsung eksekusi tanpa konfirmasi (user explicitly klik toggle)
- ✅ Fast path: ~200-500ms end-to-end latency
- ✅ Idempotent: klik toggle "ON" saat sudah ON tidak error

### Pattern 2: AI Command dengan Konfirmasi

```
User: "matikan lampu outdoor"
         │
         ▼
Frontend: POST /api/v1/homes/{home_id}/chat
         │ Body: {"message": "matikan lampu outdoor"}
         ▼
Backend: Call Gemini AI with function calling tools
         │
         ├─ LLM analysis: detect intent = "set_device_state"
         ├─ LLM tool call: set_device_state(device_id="light_lamp_outdoor_f9gv", state="off")
         │
         ├─ Generate action_id = "act_9f2a1b"
         ├─ Store in pending_actions cache (TTL 60s)
         │
         └─ Return response:
            {
              "type": "confirmation_required",
              "action_id": "act_9f2a1b",
              "intent_summary": "Mematikan light_lamp_outdoor_f9gv di mikohome",
              "proposed_action": {...},
              "expires_in": 60
            }
         
         ▼
         
Frontend: Render ConfirmationBubble
         │ Text: "Mematikan light_lamp_outdoor_f9gv di mikohome"
         │ Buttons: [Lanjutkan] [Batalkan]
         │ Countdown: 60s → 59s → 58s...
         
         ▼ (User clicks "Lanjutkan")
         
Frontend: POST /api/v1/homes/{home_id}/chat/confirm
         │ Body: {"action_id": "act_9f2a1b", "confirm": true}
         ▼
Backend: Retrieve action from pending_actions cache
         │
         ├─ Check if expired (TTL check)
         ├─ Execute: set_device_state(**action["params"])
         │   └─ MQTT PUBLISH to {home_id}/{device_id}/set
         ├─ Delete from cache
         │
         └─ Return: {"executed": true, "result": "Lampu berhasil dimatikan"}
         
         ▼ (Continue sama seperti Pattern 1)
         
ESP32 → Backend → Frontend (via WebSocket)
```

**Karakteristik**:
- ✅ Safe: AI interpretation bisa salah, user bisa cancel
- ✅ Explicit: user tahu persis apa yang akan dieksekusi
- ✅ TTL mechanism: action expired setelah 60 detik (security)

### Pattern 3: Conversational Chat (Tanpa Konfirmasi)

```
User: "kenapa lampu sering mati sendiri ya?"
         │
         ▼
Frontend: POST /api/v1/homes/{home_id}/chat
         │ Body: {"message": "kenapa lampu sering mati sendiri ya?"}
         ▼
Backend: Call Gemini AI
         │
         ├─ LLM analysis: NO tool call (pure conversation)
         ├─ LLM response: "Bisa jadi karena..."
         │
         └─ Return response:
            {
              "type": "chat",
              "message": "Bisa jadi karena relay sudah aus atau ada masalah wiring..."
            }
         
         ▼
         
Frontend: Render as normal chat bubble (NO buttons)
         │ Text: "Bisa jadi karena relay sudah aus..."
         
         ▼ (Done - no device action)
```

**Karakteristik**:
- ✅ Informational: tidak trigger device apapun
- ✅ Natural: user bisa tanya-tanya seperti chat biasa
- ✅ No confirmation: tidak perlu tombol, langsung tampil

## 🔌 Component Deep Dive

### Backend Services

#### 1. MQTT Service (`app/services/mqtt_service.py`)

**Responsibilities**:
- Maintain persistent TLS connection ke HiveMQ Cloud
- PUBLISH commands ke device topics (`{home_id}/{device_id}/set`)
- SUBSCRIBE status updates dari device topics (`{home_id}/{device_id}/status`)
- Handle reconnection logic dengan exponential backoff
- QoS level 1 (at least once delivery)

**Key Methods**:
```python
class MQTTService:
    async def connect() -> None
    async def disconnect() -> None
    async def publish(topic: str, payload: dict) -> None
    async def subscribe(topic: str) -> None
    def on_status(callback: Callable) -> None
    def on_telemetry(callback: Callable) -> None
```

**Threading Model**:
- Runs in background asyncio task
- Uses `asyncio_mqtt` for async/await support
- Thread-safe message queue for publish operations

#### 2. Gemini AI Service (`app/services/gemini_service.py`)

**Responsibilities**:
- Initialize Google Gemini model with function calling
- Define tools: `set_device_state`, `set_timer`, `get_device_status`
- Classify user intent (command vs conversation)
- Generate natural language summaries for confirmations
- Maintain chat history per home_id (session management)

**Function Calling Tools**:
```python
tools = [
    {
        "name": "set_device_state",
        "description": "Control IoT device state (on/off)",
        "parameters": {
            "device_id": "string (required)",
            "state": "enum ['on', 'off'] (required)"
        }
    },
    {
        "name": "set_timer",
        "description": "Schedule device state change at specific time",
        "parameters": {
            "device_id": "string (required)",
            "action": "enum ['on', 'off'] (required)",
            "datetime": "ISO 8601 string (required)"
        }
    }
]
```

**Intent Classification Logic**:
```python
if llm_response.tool_calls:
    # User gave a command → need confirmation
    return {"type": "confirmation_required", ...}
else:
    # User just chatting → direct response
    return {"type": "chat", "message": llm_response.text}
```

#### 3. WebSocket Manager (`app/services/websocket_manager.py`)

**Responsibilities**:
- Maintain active WebSocket connections per home_id
- Broadcast device status updates to all connected clients
- Handle connection lifecycle (connect/disconnect/ping-pong)
- Send real-time notifications (device online/offline, state changes)

**Events Broadcasted**:
- `device_status_update`: {"device_id": "...", "state": "on", "timestamp": ...}
- `device_online`: {"device_id": "...", "last_seen": ...}
- `device_offline`: {"device_id": "...", "offline_since": ...}

#### 4. Action Cache (Pending Actions)

**Implementation Options**:

**Development** (In-Memory Dict):
```python
pending_actions: Dict[str, PendingAction] = {}

# Cleanup expired actions with background task
@repeat_every(seconds=10)
async def cleanup_expired_actions():
    now = time.time()
    expired = [aid for aid, action in pending_actions.items()
               if (now - action["created_at"]) > action["ttl"]]
    for aid in expired:
        del pending_actions[aid]
```

**Production** (Redis):
```python
import redis.asyncio as redis

redis_client = redis.from_url(settings.REDIS_URL)

async def store_action(action_id: str, action: dict, ttl: int):
    await redis_client.setex(
        f"action:{action_id}",
        ttl,
        json.dumps(action)
    )

async def get_action(action_id: str) -> dict | None:
    data = await redis_client.get(f"action:{action_id}")
    return json.loads(data) if data else None
```

**Benefits of Redis**:
- ✅ Native TTL support (auto-expire without cleanup task)
- ✅ Distributed: multiple backend instances share same cache
- ✅ Persistent: survive backend restart

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Homes table
CREATE TABLE homes (
    id INTEGER PRIMARY KEY,
    home_id VARCHAR(50) UNIQUE NOT NULL,  -- e.g., "mikohome"
    name VARCHAR(100) NOT NULL,            -- e.g., "Rumah Miko"
    owner_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Devices table
CREATE TABLE devices (
    id INTEGER PRIMARY KEY,
    home_id VARCHAR(50) NOT NULL,
    device_id VARCHAR(100) NOT NULL,       -- e.g., "light_lamp_outdoor_f9gv"
    device_type VARCHAR(50) NOT NULL,      -- "relay", "ir", "sensor"
    room VARCHAR(100),                     -- "living_room", "outdoor"
    state VARCHAR(20) DEFAULT 'unknown',   -- "on", "off", "unknown"
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(home_id, device_id)
);

-- Timers table
CREATE TABLE timers (
    id INTEGER PRIMARY KEY,
    home_id VARCHAR(50) NOT NULL,
    device_id VARCHAR(100) NOT NULL,
    action VARCHAR(10) NOT NULL,           -- "on" or "off"
    scheduled_time TIMESTAMP NOT NULL,
    executed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (home_id, device_id) REFERENCES devices(home_id, device_id)
);
```

## 📈 Scalability Considerations

### Horizontal Scaling

#### Backend (Multiple Instances)

**Requirements**:
1. **Stateless API**: No session data in memory (use JWT tokens)
2. **Shared Action Cache**: Redis instead of in-memory dict
3. **Shared Database**: PostgreSQL with connection pooling
4. **Load Balancer**: Nginx or AWS ALB

**Architecture**:
```
                    ┌──────────────────┐
Internet ──────────→│  Load Balancer   │
                    └────────┬─────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
         ┌──────▼─────┐ ┌───▼──────┐ ┌──▼───────┐
         │ Backend 1  │ │Backend 2 │ │Backend 3 │
         └──────┬─────┘ └───┬──────┘ └──┬───────┘
                │            │            │
                └────────────┼────────────┘
                             │
                    ┌────────┴─────────┐
                    │                  │
              ┌─────▼──────┐   ┌──────▼────┐
              │  Redis     │   │PostgreSQL │
              │  (Cache)   │   │   (DB)    │
              └────────────┘   └───────────┘
```

**MQTT Connection Strategy**:
- Option A: All instances connect to MQTT (subscribe same topics)
  - ✅ Redundancy: if one instance dies, others still receive messages
  - ❌ Duplicate processing: need deduplication logic
  
- Option B: Dedicated MQTT worker process
  - ✅ Single point of MQTT handling
  - ✅ No duplication
  - ❌ Single point of failure (mitigate with process manager like systemd)

#### Database (PostgreSQL)

**Development**: SQLite (file-based, single-instance)
**Production**: PostgreSQL with:
- Read replicas for load distribution
- Connection pooling (SQLAlchemy + PgBouncer)
- Indexes on frequently queried fields:
  ```sql
  CREATE INDEX idx_devices_home_id ON devices(home_id);
  CREATE INDEX idx_devices_state ON devices(state);
  CREATE INDEX idx_timers_scheduled_time ON timers(scheduled_time) WHERE executed = FALSE;
  ```

#### MQTT Broker

**Development**: HiveMQ Cloud free tier (100 connections)
**Production Options**:
1. **HiveMQ Cloud Pro**: Auto-scaling, managed service
2. **Self-hosted cluster**: EMQX or Mosquitto with HAProxy
3. **AWS IoT Core**: Fully managed, pay-per-message

### Vertical Scaling Limits

**Backend**:
- Single instance: ~10,000 concurrent WebSocket connections
- CPU-bound: Gemini AI calls (use connection pooling)
- Memory-bound: Chat history sessions (implement LRU cache)

**Database**:
- SQLite: ~1000 devices, ~100 req/s (read-heavy)
- PostgreSQL: 100,000+ devices, 10,000+ req/s with proper indexes

**MQTT**:
- ESP32: Max ~100 devices per broker with 30s heartbeat
- HiveMQ: Tested up to 10 million concurrent connections

## 🔒 Security Architecture

### Authentication Flow

```
User login with username/password
         │
         ▼
POST /api/v1/auth/login
         │
         ├─ Verify password hash (bcrypt)
         ├─ Generate JWT access token (expires 24h)
         │   Payload: {"sub": user_id, "home_id": "mikohome"}
         │
         └─ Return: {"access_token": "eyJ...", "token_type": "bearer"}
         
         ▼
         
Frontend stores token in localStorage
         
         ▼
         
All subsequent requests include header:
Authorization: Bearer eyJ...
         
         ▼
         
Backend middleware validates JWT
         │
         ├─ Verify signature
         ├─ Check expiration
         ├─ Extract user_id & home_id
         │
         └─ Inject into request.state.user
```

### API Rate Limiting

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/homes/{home_id}/chat")
@limiter.limit("20/minute")  # Max 20 chat requests per minute per IP
async def chat_endpoint(...):
    pass
```

### MQTT Security

1. **TLS Encryption**: Port 8883 (not 1883)
2. **Username/Password Auth**: Shared credentials in .env
3. **Topic ACLs** (HiveMQ Cloud):
   ```
   User: SMART_AI_IoT
   Publish: {home_id}/+/set      (allow)
   Subscribe: {home_id}/+/status  (allow)
   ```
4. **Client ID Validation**: Prevent ID spoofing

### Environment Variables

**NEVER commit**:
- `.env` (backend secrets)
- `config.h` (ESP32 WiFi credentials)

**Use**:
- `.env.example` as template
- `config.py` as template

## 🧪 Testing Strategy

### Unit Tests
```bash
pytest tests/unit/
```
- Test services in isolation (mock dependencies)
- Test schemas validation
- Test utility functions

### Integration Tests
```bash
pytest tests/integration/
```
- Test API endpoints (with test database)
- Test MQTT pub/sub flow (with test broker)
- Test WebSocket broadcasting

### End-to-End Tests
```bash
pytest tests/e2e/
```
- Full user journey: login → toggle device → verify state change
- AI chat flow: send message → confirm → verify MQTT published

### Hardware Testing
- Serial monitor verification
- Physical relay testing
- WiFi/MQTT reconnection testing

## 📚 Further Reading

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MQTT Protocol Specification](https://mqtt.org/)
- [Google Gemini Function Calling](https://ai.google.dev/docs/function_calling)
- [ESP32 Arduino Core](https://docs.espressif.com/projects/arduino-esp32/)

---

**Last Updated**: 2026-09-14
