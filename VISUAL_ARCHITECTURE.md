# 🎨 Visual Guide - Dashboard Real-Time Architecture

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SMART HOME IoT SYSTEM                       │
│                         (Real-Time Dashboard)                    │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│              │         │              │         │              │
│  Dashboard   │◄───WS──►│   Backend    │◄──MQTT─►│ IoT Devices  │
│  (Browser)   │         │  (FastAPI)   │         │  (ESP32)     │
│              │         │              │         │              │
└──────────────┘         └──────────────┘         └──────────────┘
      │                         │                         │
      │                         │                         │
   Multiple                 SQLite DB              Physical Devices
    Tabs/Users              + Gemini AI             (Sensors, etc)
```

---

## 🔄 Real-Time Sync Flow

### Scenario 1: User Click Button

```
┌────────────────────────────────────────────────────────────────┐
│  USER CLICKS "ON" BUTTON IN BROWSER                             │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  STEP 1: OPTIMISTIC UPDATE (Instant - 0ms)                     │
│  ✓ UI berubah immediately                                       │
│  ✓ Save previous state untuk rollback                          │
│  ✓ Audio feedback (beep)                                        │
│  ✓ Visual: Border gray → blue                                   │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  STEP 2: SEND COMMAND TO BACKEND (50-100ms)                    │
│  POST /api/v1/commands/{device_id}                             │
│  Body: { action: "turn_on", value: null }                      │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  STEP 3: BACKEND PROCESSES (20ms)                              │
│  ✓ Update database (Device.state = "on")                       │
│  ✓ Create command log                                          │
│  ✓ Publish MQTT: home/{room}/{device_id}/set                   │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  STEP 4: MQTT BROKER (10-20ms)                                 │
│  ✓ Broadcast to subscribed devices                             │
│  ✓ IoT device receives command                                 │
│  ✓ Device publishes status update                              │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  STEP 5: WEBSOCKET BROADCAST (10ms)                            │
│  ws_manager.broadcast_device_status()                          │
│  ✓ Send to ALL connected browser tabs                          │
│  ✓ Message type: "device_status_update"                        │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  STEP 6: DASHBOARD RECEIVES CONFIRMATION                       │
│  ✓ Original tab: Show success toast                            │
│  ✓ Other tabs: Update UI + highlight animation                 │
│  ✓ All tabs: Audio beep + ring animation                       │
└────────────────────────────────────────────────────────────────┘

TOTAL TIME: ~150ms (but user sees 0ms due to optimistic update)
```

---

### Scenario 2: Multi-Tab Synchronization

```
┌──────────────┐                           ┌──────────────┐
│   TAB 1      │                           │   TAB 2      │
│  (Active)    │                           │  (Passive)   │
└──────────────┘                           └──────────────┘
      │                                            │
      │  User clicks "ON"                         │
      │────────►                                   │
      │                                            │
      │  Optimistic Update                        │
      │  (instant)                                 │
      │                                            │
      │  Send to Backend                          │
      │──────────────────────┐                    │
      │                      ↓                     │
      │              ┌──────────────┐              │
      │              │   Backend    │              │
      │              │   (FastAPI)  │              │
      │              └──────────────┘              │
      │                      │                     │
      │              WebSocket Broadcast           │
      │                      ├─────────────────────┤
      │                      │                     │
      │◄─────────────────────┤                     │
      │                      │                     ↓
      │  Confirmation        │          Update Received!
      │  "✅ Success"        │          updateDeviceStateFromWS()
      │                      │                     │
      │                      │                     ↓
      │                      │          ┌──────────────────────┐
      │                      │          │ 1. Update UI         │
      │                      │          │ 2. Ring Animation    │
      │                      │          │ 3. Toast: "🔔 ON"   │
      │                      │          │ 4. Audio Beep        │
      │                      │          └──────────────────────┘
      │                      │                     │
      ↓                      ↓                     ↓
  [Device ON]          [MQTT Broker]         [Device ON]
   Blue Border                              Blue Border
   with Ring                                with Ring
```

---

### Scenario 3: AI Command Integration

```
┌────────────────────────────────────────────────────────────────┐
│  USER: "Nyalakan lampu kamar"                                  │
│  (Typed in AI Assistant modal)                                 │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  POST /api/v1/chat/message                                     │
│  Body: { message: "Nyalakan lampu kamar" }                     │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  BACKEND: Gemini AI Processing (200-500ms)                     │
│  ✓ Parse intent: CONTROL_DEVICE                                │
│  ✓ Extract: device="lampu kamar", action="turn_on"            │
│  ✓ Function call: control_device()                             │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  DEVICE COMMAND EXECUTION                                       │
│  ✓ Update DB: Device.state = "on"                             │
│  ✓ Publish MQTT                                                │
│  ✓ WebSocket Broadcast                                         │
└────────────────────────────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────┐
│  ALL DASHBOARD TABS UPDATE                                      │
│  ✓ Home view: Device count update                              │
│  ✓ Room view: Device card update + animation                   │
│  ✓ Remote view: Device card update + animation                 │
│  ✓ AI chat: Reply "Beres, lampu kamar udah dinyalakan!"       │
└────────────────────────────────────────────────────────────────┘
```

---

## 🎭 UI State Transitions

### Device Card Visual States

```
┌─────────────────────────────────────────────────────────────┐
│  STATE: OFF (Initial)                                       │
├─────────────────────────────────────────────────────────────┤
│  Border: border-surface-border (gray)                       │
│  Indicator: ⚫ (gray static dot)                            │
│  Shadow: none                                               │
│  Button: "OFF" (gray background)                            │
└─────────────────────────────────────────────────────────────┘
                        ↓ (User clicks)
┌─────────────────────────────────────────────────────────────┐
│  STATE: TRANSITIONING (Optimistic)                          │
├─────────────────────────────────────────────────────────────┤
│  Border: border-brand/40 (blue)                             │
│  Indicator: 🟢 (green pulsing)                             │
│  Shadow: shadow-card-hover                                  │
│  Button: "ON" (brand blue background)                       │
│  Animation: transition-all duration-300                     │
└─────────────────────────────────────────────────────────────┘
                        ↓ (Backend confirms)
┌─────────────────────────────────────────────────────────────┐
│  STATE: ON (Confirmed)                                      │
├─────────────────────────────────────────────────────────────┤
│  Border: border-brand/40 (blue)                             │
│  Indicator: 🟢 (green pulsing)                             │
│  Shadow: shadow-card-hover                                  │
│  Button: "ON" (brand blue)                                  │
│  Toast: "✅ Lampu Kamar: ON"                                │
└─────────────────────────────────────────────────────────────┘
                        ↓ (Remote change detected)
┌─────────────────────────────────────────────────────────────┐
│  STATE: ON + HIGHLIGHT (Remote Update)                      │
├─────────────────────────────────────────────────────────────┤
│  Border: border-brand/40 + ring-2 ring-brand               │
│  Indicator: 🟢 (green pulsing)                             │
│  Shadow: shadow-card-hover                                  │
│  Animation: Ring pulse for 1.5s                             │
│  Toast: "🔔 Lampu Kamar → ON"                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔌 WebSocket Connection States

```
┌─────────────────────────────────────────────────────────────┐
│  CONNECTING (readyState = 0)                                │
├─────────────────────────────────────────────────────────────┤
│  Status: "Menghubungkan..."                                 │
│  Color: Amber/Orange                                        │
│  Action: Waiting for handshake                              │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  OPEN (readyState = 1) ✅                                   │
├─────────────────────────────────────────────────────────────┤
│  Status: "🟢 Tersambung Real-Time"                          │
│  Color: Green                                               │
│  Action: Sending/Receiving messages                         │
│  Toast: "🔗 Real-time sync aktif!"                         │
└─────────────────────────────────────────────────────────────┘
                        ↓ (Connection lost)
┌─────────────────────────────────────────────────────────────┐
│  CLOSING (readyState = 2)                                   │
├─────────────────────────────────────────────────────────────┤
│  Status: "Terputus..."                                      │
│  Color: Red                                                 │
│  Action: Cleanup                                            │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  CLOSED (readyState = 3)                                    │
├─────────────────────────────────────────────────────────────┤
│  Status: "🔄 Menghubungkan ulang..."                        │
│  Color: Amber                                               │
│  Action: Exponential backoff retry                          │
│  Delays: 2s → 4s → 8s → 16s → 30s (max)                    │
└─────────────────────────────────────────────────────────────┘
                        ↓ (Retry successful)
                    [Back to OPEN]
```

---

## 🎯 Data Flow Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                    FRONTEND (Browser)                          │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  [User Action] → [Optimistic Update] → [API Call]            │
│       ↓                                      ↓                 │
│  [Save Prev State]              [POST /api/v1/commands]       │
│       ↓                                      ↓                 │
│  [UI Update]                          [Try-Catch]             │
│       ↓                                      ↓                 │
│  [Audio Beep]                         [Success/Error]         │
│                                              ↓                 │
│                                    ┌─────────────────┐        │
│                                    │  On Success:     │        │
│                                    │  - Keep UI       │        │
│                                    │  - Show toast    │        │
│                                    │                  │        │
│                                    │  On Error:       │        │
│                                    │  - Rollback UI   │        │
│                                    │  - Error toast   │        │
│                                    └─────────────────┘        │
│                                                                │
│  [WebSocket Listener]                                         │
│       ↓                                                        │
│  [onmessage] → [Parse JSON] → [Route by type]                │
│                                      ↓                         │
│                         ┌────────────┼────────────┐           │
│                         ↓            ↓            ↓           │
│                  [Status Update] [Telemetry] [Other]         │
│                         ↓            ↓            ↓           │
│                  [Update Device] [Update Temp] [Handle]      │
│                         ↓            ↓                        │
│                  [Render All]  [Animate Change]              │
│                         ↓            ↓                        │
│                  [Highlight]   [Toast Notify]                │
│                                                                │
└───────────────────────────────────────────────────────────────┘
                              ↕ WebSocket
┌───────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                           │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  [API Endpoint] → [Auth Check] → [Device Manager]            │
│                                         ↓                      │
│                             [Update DB] + [MQTT Publish]      │
│                                         ↓                      │
│                             [ws_manager.broadcast()]           │
│                                         ↓                      │
│                         [Send to all connected clients]       │
│                                                                │
│  [MQTT Handler] → [Parse Topic] → [Device Manager]           │
│                                         ↓                      │
│                             [Update DB] + [WebSocket]         │
│                                         ↓                      │
│                             [ws_manager.broadcast()]           │
│                                                                │
│  [WebSocket Endpoint]                                         │
│       ↓                                                        │
│  [JWT Validation] → [ws_manager.connect()]                   │
│       ↓                                                        │
│  [Keep-Alive Loop] → [Listen for client messages]            │
│       ↓                                                        │
│  [Broadcast Updates] → [All connected tabs]                  │
│                                                                │
└───────────────────────────────────────────────────────────────┘
                              ↕ MQTT
┌───────────────────────────────────────────────────────────────┐
│                  MQTT BROKER (HiveMQ Cloud)                    │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  Topics:                                                       │
│  - home/{room}/{device_id}/set      (Commands)               │
│  - home/{room}/{device_id}/status   (Status Updates)         │
│  - home/{room}/{device_id}/telemetry (Sensor Data)           │
│                                                                │
└───────────────────────────────────────────────────────────────┘
                              ↕ MQTT
┌───────────────────────────────────────────────────────────────┐
│                   IoT DEVICES (ESP32, etc)                     │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  [Receive Command] → [Execute Action] → [Publish Status]     │
│  [Read Sensors] → [Publish Telemetry]                        │
│                                                                │
└───────────────────────────────────────────────────────────────┘
```

---

## 📱 Multi-Tab Interaction Visual

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     TAB 1       │  │     TAB 2       │  │     TAB 3       │
│   (Home View)   │  │  (Room View)    │  │  (Remote View)  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                   │                     │
         │                   │                     │
         └───────────────────┼─────────────────────┘
                             │
                    ┌────────┴────────┐
                    │   WebSocket     │
                    │   (Single       │
                    │   Connection    │
                    │   per tab)      │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    │   BACKEND       │
                    │   Broadcast     │
                    │   Manager       │
                    │                 │
                    └────────┬────────┘
                             │
         ┌───────────────────┼─────────────────────┐
         │                   │                     │
         ↓                   ↓                     ↓
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Update Summary │  │  Update Device  │  │  Update Card    │
│  + Animation    │  │  + Ring Flash   │  │  + Highlight    │
│  + Toast        │  │  + Toast        │  │  + Toast        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## ⚡ Performance Timeline

```
Time (ms)    Action                              Visual Feedback
────────────────────────────────────────────────────────────────
0            User clicks "ON" button             -
0            Optimistic UI update                ✓ Button changes instantly
0            Audio feedback                      ✓ Beep sound plays
0            Save previous state                 -
50           POST request sent                   -
100          Backend receives & processes        -
120          Database updated                    -
130          MQTT publish                        -
150          Backend response received           -
160          Success toast shown                 ✓ "✅ Success"
170          WebSocket broadcast sent            -
180          Other tabs receive update           ✓ Ring animation
180          Other tabs show toast               ✓ "🔔 Device ON"
200          MQTT delivered to device            -
220          Device executes action              ✓ Physical LED ON
250          Device publishes status             -
270          Backend receives MQTT status        -
280          WebSocket confirmation broadcast    -
300          Final sync complete                 ✓ All in sync

Total perceived latency for user: 0ms (optimistic update)
Total actual sync time: 300ms
```

---

## 🎨 Color Coding

```
🟢 Green   = Connected / Online / Success
🔵 Blue    = Active / Selected / Brand
🟡 Yellow  = Warning / Transitioning
🔴 Red     = Error / Offline / Failed
⚫ Gray    = Inactive / Disabled / OFF
```

---

**Visual Guide Complete!**

📚 Use this with other documentation for full understanding.
