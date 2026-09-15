# SMART AI IoT System - Quick Start Guide

## 🎯 Cara Tercepat Menjalankan Sistem

### Metode 1: Double-Click START_SYSTEM.bat ⚡ (RECOMMENDED)

```
1. Double-click file: START_SYSTEM.bat
2. Tunggu backend loading (5-10 detik)
3. Buka browser ke: http://localhost:8000/ui
4. Done! ✅
```

---

## 🌐 Akses Sistem

Setelah backend running, pilih salah satu:

### A. Akses via Backend (Paling Mudah)
**URL:** http://localhost:8000/ui
- ✅ Terintegrasi penuh
- ✅ No CORS issues
- ✅ WebSocket langsung connect

### B. Akses via Live Server (Development Only)
1. Buka VSCode
2. Install extension "Live Server"
3. Buka folder `frontend`
4. Klik kanan `index.html` → "Open with Live Server"
5. Browser buka otomatis di http://localhost:5500

---

## 🎮 Fitur Utama

### 1. Dashboard
- Lihat semua ruangan dan perangkat
- Status real-time via MQTT
- Kontrol on/off dengan toggle

### 2. AI Chat Assistant
- Klik icon robot di kanan bawah
- Ketik perintah natural language:
  - "halo"
  - "nyalakan lampu kamar"
  - "matikan semua lampu di ruang tamu"
  - "hidupkan AC"

### 3. Monitoring
- Temperature & Humidity sensor
- Device status (online/offline)
- Command logs

---

## 📊 Status Sistem Saat Ini

✅ Backend: Running (Port 8000)
✅ MQTT: Connected (HiveMQ Cloud)
✅ AI: Ready (Google Gemini)
✅ Database: Configured (SQLite)
✅ Supabase: Connected
✅ WebSocket: Active

**Sistem siap digunakan!**

---

## 🆘 Troubleshooting Cepat

### Backend tidak jalan?
```powershell
cd backend
.\venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Port 8000 sudah dipakai?
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Frontend tidak konek?
- Pastikan backend running
- Clear browser cache (Ctrl + Shift + Del)
- Refresh page (F5)

---

## 📱 Akses dari HP/Device Lain

1. Cari IP komputer: `ipconfig`
2. Buka di HP: `http://<IP_ANDA>:8000/ui`
3. Contoh: `http://192.168.1.100:8000/ui`

---

**Dokumentasi Lengkap:** Lihat `README_GO_LIVE.md`
