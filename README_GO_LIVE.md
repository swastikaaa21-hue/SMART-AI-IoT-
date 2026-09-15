# 🚀 Panduan Go Live - SMART AI IoT System

## 📋 Prerequisites

1. **Backend Dependencies**
   - Python 3.10+
   - Virtual environment sudah setup
   - File `.env` sudah dikonfigurasi

2. **Frontend Tools (Pilih salah satu)**
   - VSCode + Live Server Extension
   - Atau akses langsung via backend

3. **Services**
   - HiveMQ Cloud (MQTT Broker)
   - Google Gemini API
   - Supabase (Optional)

---

## 🎯 Metode 1: Menggunakan START_SYSTEM.bat (Recommended)

### Langkah:

1. **Double-click file `START_SYSTEM.bat`**
   - Script akan otomatis start backend
   - Terminal backend akan terbuka

2. **Pilih cara akses:**
   
   **A. Akses via Backend (Paling Mudah)**
   - Buka browser: `http://localhost:8000/ui`
   - ✅ Langsung bisa digunakan
   
   **B. Akses via Live Server (Development)**
   - Buka VSCode
   - Buka folder `frontend`
   - Klik kanan `index.html` → "Open with Live Server"
   - Browser otomatis buka di `http://127.0.0.1:5500` atau `http://localhost:5500`

---

## 🎯 Metode 2: Manual Start (Full Control)

### Terminal 1 - Backend:
```powershell
cd "D:\SMART AI IoT\backend"
.\venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2 - Frontend (Optional):
```powershell
cd "D:\SMART AI IoT"
python -m http.server 5500 --directory frontend
```

### Atau VSCode Live Server:
1. Install extension: "Live Server" by Ritwick Dey
2. Buka folder `frontend` di VSCode
3. Klik kanan `index.html`
4. Pilih "Open with Live Server"

---

## 🌐 URL Akses Sistem

| Service | URL | Keterangan |
|---------|-----|------------|
| **Frontend (Backend)** | http://localhost:8000/ui | ✅ Terintegrasi penuh |
| **Frontend (Live Server)** | http://localhost:5500 | Development mode |
| **API Documentation** | http://localhost:8000/docs | Swagger UI |
| **Health Check** | http://localhost:8000/health | Status monitoring |
| **API Endpoint** | http://localhost:8000/api/v1 | REST API |

---

## ✅ Verifikasi Sistem Running

### 1. Cek Backend:
```powershell
# Via PowerShell
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing

# Via Browser
# Buka: http://localhost:8000/health
```

**Expected Response:**
```json
{
    "status": "ok",
    "version": "1.0.0",
    "services": {
        "mqtt": "connected",
        "gemini": "ready",
        "websocket": "0 connections",
        "database": "configured",
        "supabase": "connected"
    }
}
```

### 2. Cek Ports:
```powershell
netstat -ano | Select-String ":8000|:5500"
```

Output yang benar:
```
TCP    0.0.0.0:8000    0.0.0.0:0    LISTENING    <PID>
TCP    127.0.0.1:5500  0.0.0.0:0    LISTENING    <PID>  (jika pakai Live Server)
```

---

## 🎮 Cara Menggunakan Sistem

### 1. **Akses UI Dashboard**
   - Buka `http://localhost:8000/ui`

### 2. **Register/Login**
   - Klik "GET STARTED"
   - Pilih "Setup & Create New Account"
   - Isi form registrasi
   - Atau login jika sudah punya akun

### 3. **Dashboard**
   - Lihat semua ruangan (Kamar, Ruang Tamu, Ruang Rapat, Studio)
   - Klik ruangan untuk melihat detail perangkat

### 4. **Kontrol Perangkat**
   - Toggle switch untuk nyalakan/matikan
   - Perubahan real-time via MQTT

### 5. **Chat dengan AI Assistant**
   - Klik icon robot di pojok kanan bawah
   - Ketik perintah natural language:
     - "halo"
     - "nyalakan lampu kamar"
     - "matikan semua lampu di ruang tamu"
     - "hidupkan AC kamar"
     - "berapa suhu di kamar?"

---

## 📱 Akses dari Device Lain (HP/Tablet)

### 1. Cari IP Komputer:
```powershell
ipconfig
# Cari "IPv4 Address", contoh: 192.168.1.100
```

### 2. Akses dari HP:
- Buka browser di HP
- Ketik: `http://192.168.1.100:8000/ui`
- **Pastikan HP dan PC dalam jaringan WiFi yang sama**

---

## 🔧 Troubleshooting

### Backend tidak jalan:
```powershell
# Cek apakah venv ada
cd backend
dir venv

# Jika tidak ada, buat baru:
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Port 8000 sudah dipakai:
```powershell
# Cari process yang pakai port
netstat -ano | findstr :8000

# Kill process (ganti <PID>)
taskkill /PID <PID> /F
```

### Frontend tidak konek ke backend:
1. Pastikan backend running di port 8000
2. Cek file `frontend/index.html` line 866-868:
   ```javascript
   const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
       ? 'http://localhost:8000/api/v1'
       : window.location.origin + '/api/v1';
   ```
3. Clear browser cache (Ctrl + Shift + Del)

### MQTT tidak connect:
- Cek file `backend/.env`
- Pastikan credentials HiveMQ Cloud benar:
  ```
  MQTT_BROKER=0899f05ecad5437d93d7fbd8b9b96f70.s1.eu.hivemq.cloud
  MQTT_PORT=8883
  MQTT_USERNAME=SMART_AI_IoT
  MQTT_PASSWORD=CHEETAHARINJATMIKO
  ```

### Gemini AI tidak respond:
- Cek `GEMINI_API_KEY` di `backend/.env`
- Pastikan API key valid dan tidak expired

---

## 🎯 Best Practice untuk Development

### 1. **Gunakan Backend Terintegrasi**
   - URL: `http://localhost:8000/ui`
   - Keuntungan:
     - Tidak perlu Live Server
     - CORS sudah handled
     - WebSocket langsung connect
     - Single port untuk semua

### 2. **Gunakan Live Server (Optional)**
   - Untuk development frontend only
   - Hot reload otomatis
   - URL: `http://localhost:5500`

### 3. **Terminal Management**
   - Buka 2 terminal terpisah:
     - Terminal 1: Backend
     - Terminal 2: Frontend (optional)

---

## 🛑 Cara Stop Sistem

### Stop Backend:
- Tekan `Ctrl + C` di terminal backend
- Atau tutup window terminal

### Stop Live Server:
- Tekan `Ctrl + C` di terminal
- Atau klik "Stop" di VSCode status bar

### Stop Semua (Force):
```powershell
# Kill all Python processes
Get-Process python | Stop-Process -Force

# Kill specific port
$process = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($process) { Stop-Process -Id $process.OwningProcess -Force }
```

---

## 📊 System Architecture

```
┌─────────────────┐
│   Frontend UI   │ (port 5500 atau via :8000/ui)
│  HTML/JS/CSS    │
└────────┬────────┘
         │ HTTP/WebSocket
         ▼
┌─────────────────┐
│  Backend API    │ (port 8000)
│    FastAPI      │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼
┌──────┐  ┌──────┐  ┌────────┐  ┌──────┐
│SQLite│  │ MQTT │  │ Gemini │  │Supa- │
│  DB  │  │HiveMQ│  │   AI   │  │ base │
└──────┘  └──────┘  └────────┘  └──────┘
```

---

## ✅ Checklist Go Live

- [ ] Backend `.env` sudah dikonfigurasi
- [ ] Virtual environment terinstall
- [ ] Dependencies terinstall (`pip install -r requirements.txt`)
- [ ] Database sudah ada (`smart_aiot.db`)
- [ ] MQTT credentials valid
- [ ] Gemini API key valid
- [ ] Backend running di port 8000
- [ ] Health check return status "ok"
- [ ] Frontend bisa akses backend
- [ ] Chat AI berfungsi
- [ ] Kontrol perangkat berfungsi
- [ ] WebSocket connect

---

## 📞 Support

Jika ada masalah:
1. Cek log di terminal backend
2. Cek browser console (F12)
3. Cek health endpoint: `http://localhost:8000/health`
4. Restart sistem dengan `START_SYSTEM.bat`

---

**Status Sistem Saat Ini:** ✅ **READY FOR GO LIVE**

Semua komponen sudah terintegrasi dan berfungsi dengan baik.
