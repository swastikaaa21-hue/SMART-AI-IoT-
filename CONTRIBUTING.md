# 🤝 Contributing Guide

Panduan untuk developer yang ingin berkontribusi atau extend Smart AI IoT platform.

## 🎯 Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ (untuk frontend development)
- Git
- ESP32 development environment
- PostgreSQL (optional, untuk production testing)

### Setup Development Environment

```bash
# Clone repository
git clone <repository-url>
cd smarthome-AIoT

# Setup backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env dengan credentials

# Run migrations
alembic upgrade head

# Start backend dengan auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Run Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# With coverage
pytest --cov=app --cov-report=html

# View coverage
open htmlcov/index.html
```

## 📁 Project Structure

```
smarthome-AIoT/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints (RESTful routes)
│   │   │   ├── endpoints/   # Individual endpoint modules
│   │   │   └── router.py    # Main API router
│   │   ├── core/            # Core configuration
│   │   │   ├── config.py    # Settings & environment
│   │   │   ├── database.py  # Database connection
│   │   │   └── logging.py   # Logging setup
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic layer
│   │   │   ├── gemini_service.py     # AI integration
│   │   │   ├── mqtt_service.py       # MQTT client
│   │   │   ├── mqtt_handler.py       # MQTT message handlers
│   │   │   ├── device_service.py     # Device CRUD
│   │   │   └── websocket_manager.py  # WebSocket hub
│   │   └── middleware/      # Custom middleware
│   ├── alembic/             # Database migrations
│   ├── tests/               # Test suites
│   └── main.py              # Application entry point
│
├── Hardware/
│   ├── config.py            # Template (copy to config.h)
│   ├── main.py              # Arduino sketch (rename to .ino)
│   └── README.md
│
├── frontend/
│   └── index.html           # Single-page dashboard
│
└── docs/                    # Documentation (this level)
    ├── README.md
    ├── ARCHITECTURE.md
    ├── GETTING_STARTED.md
    └── ...
```

## 🔧 Adding New Features

### 1. Add New Device Type

**Step 1: Update Database Model** (`backend/app/models/device.py`)
```python
# Add new type to enum
device_type = Column(String(50), nullable=False)  # relay, ir, sensor, dimmer, rgb
```

**Step 2: Create Migration**
```bash
alembic revision --autogenerate -m "Add dimmer device type"
alembic upgrade head
```

**Step 3: Update Device Service** (`backend/app/services/device_service.py`)
```python
async def set_dimmer_level(device_id: str, level: int):
    # Implementation for dimmer control
    payload = {"level": level, "timestamp": int(time.time())}
    await mqtt_service.publish(f"{home_id}/{device_id}/set", payload)
```

**Step 4: Add API Endpoint** (`backend/app/api/v1/endpoints/devices.py`)
```python
@router.post("/{device_id}/dimmer")
async def set_dimmer(device_id: str, level: int):
    await device_service.set_dimmer_level(device_id, level)
    return {"success": True}
```

**Step 5: Update ESP32 Code**
```cpp
// Handle dimmer command
if (doc.containsKey("level")) {
  int level = doc["level"];
  analogWrite(DIMMER_PIN, level);  // 0-255
}
```

---

### 2. Add New AI Tool (Function Calling)

**Step 1: Define Tool Schema** (`backend/app/services/gemini_service.py`)
```python
GET_ENERGY_USAGE_TOOL = {
    "name": "get_energy_usage",
    "description": "Get energy consumption statistics for a device",
    "parameters": {
        "type": "object",
        "properties": {
            "device_id": {"type": "string"},
            "period": {"type": "string", "enum": ["today", "week", "month"]}
        },
        "required": ["device_id", "period"]
    }
}

# Add to tools list
tools = [SET_DEVICE_STATE_TOOL, SET_TIMER_TOOL, GET_ENERGY_USAGE_TOOL]
```

**Step 2: Implement Tool Handler**
```python
def handle_tool_call(tool_name: str, params: dict):
    if tool_name == "get_energy_usage":
        return get_energy_usage(**params)
    # ... other tools
```

**Step 3: Test Tool**
```bash
curl -X POST "http://localhost:8000/api/v1/homes/mikohome/chat" \
  -d '{"message": "berapa konsumsi listrik lampu outdoor minggu ini?"}'
```

---

### 3. Add New MQTT Topic Pattern

**Step 1: Define Topic** (follow convention)
```
/{home_id}/{device_id}/telemetry  # For sensor data streaming
```

**Step 2: Backend Subscribe** (`backend/app/services/mqtt_service.py`)
```python
async def connect(self):
    # ... existing code
    await self._client.subscribe(f"{home_id}/+/telemetry")
```

**Step 3: Add Handler** (`backend/app/services/mqtt_handler.py`)
```python
async def handle_device_telemetry(topic: str, payload: dict):
    # Parse topic: mikohome/sensor_temp_bedroom/telemetry
    parts = topic.split("/")
    device_id = parts[1]
    
    # Store telemetry data
    await db.save_telemetry(device_id, payload)
```

**Step 4: ESP32 Publish**
```cpp
void publishTelemetry() {
  StaticJsonDocument<256> doc;
  doc["temperature"] = dht.readTemperature();
  doc["humidity"] = dht.readHumidity();
  doc["timestamp"] = getUnixTime();
  
  char buffer[256];
  serializeJson(doc, buffer);
  mqttClient.publish("mikohome/sensor_temp_bedroom/telemetry", buffer);
}
```

---

## 🧪 Testing Guidelines

### Unit Tests

**Test Service Layer** (`tests/unit/test_device_service.py`)
```python
import pytest
from app.services.device_service import DeviceService

@pytest.mark.asyncio
async def test_toggle_device():
    service = DeviceService()
    result = await service.toggle_device("mikohome", "light_test", "on")
    assert result["success"] is True
```

### Integration Tests

**Test API Endpoints** (`tests/integration/test_devices_api.py`)
```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_list_devices():
    response = client.get("/api/v1/homes/mikohome/devices")
    assert response.status_code == 200
    assert "data" in response.json()
```

### Hardware Tests

**Test ESP32 MQTT** (manual checklist)
- [ ] WiFi connection stable (no disconnects dalam 10 menit)
- [ ] MQTT reconnect otomatis jika putus
- [ ] Relay respond < 500ms setelah command
- [ ] Status publish dalam 1 detik setelah execute
- [ ] JSON payload valid (test dengan validator)

---

## 📝 Code Style

### Python (Backend)

**Use Black formatter**:
```bash
black app/ --line-length 100
```

**Use isort for imports**:
```bash
isort app/ --profile black
```

**Naming conventions**:
```python
# Variables & functions: snake_case
device_id = "light_001"
async def get_device_status(device_id: str):
    pass

# Classes: PascalCase
class DeviceService:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30
```

**Type hints required**:
```python
# Good
async def toggle_device(device_id: str, state: str) -> dict:
    return {"success": True}

# Bad
async def toggle_device(device_id, state):
    return {"success": True}
```

### C++ (ESP32)

**Follow Arduino style**:
```cpp
// Functions: camelCase
void publishStatus(String state) {
    // ...
}

// Constants: UPPER_SNAKE_CASE
const int RELAY_PIN = 4;
const char* MQTT_BROKER = "broker.example.com";

// Variables: camelCase
String deviceId = "light_001";
int connectionTimeout = 5000;
```

---

## 🔀 Git Workflow

### Branch Naming

```
feature/add-dimmer-support
fix/mqtt-reconnection-bug
docs/update-getting-started
refactor/device-service-cleanup
```

### Commit Messages

**Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples**:
```
feat(api): add dimmer control endpoint

Add POST /devices/{id}/dimmer endpoint for controlling
dimmer devices with level 0-255.

Closes #42

---

fix(mqtt): handle reconnection on network drop

Previously, MQTT client would crash on network drop.
Now implements exponential backoff retry.

Fixes #38
```

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
```

---

## 🚀 Deployment

### Production Checklist

**Backend**:
- [ ] Use PostgreSQL, not SQLite
- [ ] Use Redis for action cache
- [ ] Enable HTTPS (nginx + Let's Encrypt)
- [ ] Set `DEBUG=false` in `.env`
- [ ] Use gunicorn with multiple workers
- [ ] Setup systemd service for auto-restart
- [ ] Configure log rotation
- [ ] Setup monitoring (Prometheus + Grafana)

**MQTT**:
- [ ] Use production HiveMQ plan (or self-hosted cluster)
- [ ] Enable TLS certificate validation (not `setInsecure()`)
- [ ] Setup per-device credentials (not shared)
- [ ] Configure topic ACLs
- [ ] Enable message persistence

**Hardware**:
- [ ] Use proper SSL certificates on ESP32
- [ ] Implement OTA (Over-The-Air) updates
- [ ] Add watchdog timer for auto-reset
- [ ] Add local fallback (work without internet)

---

## 📚 Resources

### Backend Development
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pydantic V2](https://docs.pydantic.dev/latest/)

### Hardware Development
- [ESP32 Arduino Core](https://docs.espressif.com/projects/arduino-esp32/)
- [PubSubClient Library](https://pubsubclient.knolleary.net/)
- [ArduinoJson](https://arduinojson.org/)

### MQTT
- [MQTT Essentials](https://www.hivemq.com/mqtt-essentials/)
- [HiveMQ Documentation](https://www.hivemq.com/docs/)

### AI Integration
- [Google Gemini Function Calling](https://ai.google.dev/docs/function_calling)

---

## 🐛 Bug Reports

When reporting bugs, include:

1. **Environment**:
   - OS (Windows 10, macOS 13, Ubuntu 22.04)
   - Python version (`python --version`)
   - Backend version (from `app/core/config.py`)

2. **Steps to Reproduce**:
   - Exact commands/actions
   - Expected vs actual result

3. **Logs**:
   ```bash
   # Backend logs
   cat backend/logs/app.log
   
   # ESP32 serial output
   # Copy from Serial Monitor
   ```

4. **Screenshots** (jika UI issue)

---

## 💡 Feature Requests

Feature request template:

```markdown
## Feature Description
Clear description of proposed feature

## Use Case
Why is this needed? What problem does it solve?

## Proposed Solution
How would this work? Any implementation ideas?

## Alternatives
Other approaches considered?

## Additional Context
Screenshots, mockups, references, etc.
```

---

## 📄 License

This project is licensed under [LICENSE TYPE]. See LICENSE file for details.

---

**Happy Contributing!** 🎉

If you have questions, open a GitHub Discussion or contact the maintainers.

---

**Last Updated**: 2026-09-14
