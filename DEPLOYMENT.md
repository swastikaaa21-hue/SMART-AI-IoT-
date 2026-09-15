# SMART AI IoT - Deployment Guide

## Architecture

- **Backend (FastAPI)** → Railway (persistent, supports MQTT/WebSocket/Supabase)
- **Frontend (Static HTML)** → Vercel (static hosting)
- **Database** → Supabase (PostgreSQL, persistent, no data loss)

---

## Prerequisites

1. **Supabase Account** — [supabase.com](https://supabase.com)
2. **Railway Account** — [railway.app](https://railway.app)
3. **Vercel Account** — [vercel.com](https://vercel.com)
4. **HiveMQ Cloud Account** — [console.hivemq.cloud](https://console.hivemq.cloud)
5. **Google Gemini API Key** — [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

---

## Step 1: Setup Supabase Database

1. Create new project di Supabase Dashboard
2. Go to **SQL Editor** → **New Query**
3. Copy semua SQL dari `backend/supabase_schema.sql`
4. Paste dan **Run** query
5. Verify tables created: users, rooms, devices, telemetry_logs, command_logs, chat_sessions, chat_messages

### Get Supabase Credentials:

- Go to **Project Settings** → **API**
- Copy **URL** (e.g., `https://xxxxx.supabase.co`)
- Copy **service_role key** (secret) — jangan pakai `anon` key

---

## Step 2: Deploy Backend ke Railway

### 2.1. Push Code ke GitHub

```bash
cd "D:\SMART AI IoT"
git add .
git commit -m "Migrate to Supabase primary database"
git push origin main
```

### 2.2. Deploy via Railway Dashboard

1. Go to [railway.app](https://railway.app)
2. **New Project** → **Deploy from GitHub repo**
3. Select `SMART AI IoT` repo
4. **Root Directory**: `/backend`
5. Railway auto-detect `Procfile` dan `runtime.txt`

### 2.3. Set Environment Variables di Railway

Go to **Variables** tab:

```env
APP_ENV=production
DEBUG=false
PORT=8000

# Supabase (REQUIRED)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=<your-service-role-key>

# MQTT HiveMQ Cloud
MQTT_BROKER=0899f05ecad5437d93d7fbd8b9b96f70.s1.eu.hivemq.cloud
MQTT_PORT=8883
MQTT_USERNAME=SMART_AI_IoT
MQTT_PASSWORD=CHEETAHARINJATMIKO

# Google Gemini AI
GEMINI_API_KEY=<your-gemini-api-key>
GEMINI_MODEL=gemini-2.0-flash-exp

# JWT Security
JWT_SECRET_KEY=<generate-dengan: openssl rand -hex 32>
SECRET_KEY=<generate-dengan: openssl rand -hex 32>

# CORS - tambah URL Vercel frontend nanti
BACKEND_CORS_ORIGINS=https://smart-aiot.vercel.app,http://localhost:8000
```

### 2.4. Deploy & Get Railway URL

Railway akan auto-deploy. Setelah selesai:
- Go to **Settings** → **Networking** → **Generate Domain**
- Copy URL: `https://smart-aiot-backend-production.up.railway.app`

### 2.5. Test Backend

```bash
curl https://smart-aiot-backend-production.up.railway.app/health
```

Expected response:
```json
{
  "status": "ok",
  "services": {
    "supabase": "connected",
    "mqtt": "connected",
    "gemini": "ready"
  }
}
```

---

## Step 3: Deploy Frontend ke Vercel

### 3.1. Update Frontend API URL

Edit `frontend/index.html` line 1094:

```js
const RAILWAY_BACKEND_URL = 'https://smart-aiot-backend-production.up.railway.app';
```

Ganti dengan Railway URL kamu.

### 3.2. Deploy via Vercel CLI

```bash
cd frontend
npx vercel
```

Atau via **Vercel Dashboard**:
1. **Add New** → **Project**
2. Import GitHub repo `SMART AI IoT`
3. **Root Directory**: `frontend`
4. **Framework Preset**: Other
5. Deploy

### 3.3. Get Vercel URL

Setelah deploy selesai, copy URL: `https://smart-aiot.vercel.app`

### 3.4. Update CORS di Railway

Back to Railway Dashboard → Variables:

```env
BACKEND_CORS_ORIGINS=https://smart-aiot.vercel.app,http://localhost:8000
```

Redeploy backend (Railway auto-redeploy on variable change).

---

## Step 4: Test End-to-End

1. Open `https://smart-aiot.vercel.app`
2. Register akun baru
3. Login
4. Dashboard auto-seed 4 rooms + devices
5. Test control device via UI
6. Test voice chat (jika ada mic)
7. Check Supabase dashboard → Tables → verify data ada

---

## Step 5: Connect ESP32 Hardware

Edit `Hardware/config.py` (jangan commit file ini):

```python
# WiFi
WIFI_SSID = "YourWiFi"
WIFI_PASSWORD = "YourPassword"

# MQTT HiveMQ Cloud
MQTT_BROKER = "0899f05ecad5437d93d7fbd8b9b96f70.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "SMART_AI_IoT"
MQTT_PASSWORD = "CHEETAHARINJATMIKO"

# Device Info
HOME_ID = "kamar"  # room slug dari dashboard
DEVICE_ID = "dev-km-1"  # device_id dari dashboard
```

Upload ke ESP32:
```bash
ampy --port COM3 put Hardware/main.py
ampy --port COM3 put Hardware/config.py
```

---

## Troubleshooting

### Backend tidak connect ke Supabase
- Verify `SUPABASE_KEY` pakai **service_role** key, bukan `anon` key
- Check Railway logs: `railway logs`

### Frontend error 404 ke backend
- Verify `RAILWAY_BACKEND_URL` di `frontend/index.html` sudah benar
- Check Railway backend is running: `curl https://your-backend.up.railway.app/health`

### Data hilang setelah Railway redeploy
- Pastikan pakai **Supabase** sebagai database, bukan SQLite lokal
- Check Railway env var `SUPABASE_URL` dan `SUPABASE_KEY` sudah di-set

### MQTT devices tidak connect
- Verify `MQTT_USERNAME` dan `MQTT_PASSWORD` match dengan HiveMQ Cloud dashboard
- Check HiveMQ Cloud credentials di **Access Management**

---

## Local Development

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
cp .env.example .env
# Edit .env dengan Supabase credentials
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
python -m http.server 5500
# Or use VS Code Live Server
```

Open http://localhost:5500

---

## Maintenance

### Update Backend Code
```bash
git add backend/
git commit -m "Update backend"
git push origin main
```
Railway auto-redeploy on push.

### Update Frontend Code
```bash
git add frontend/
git commit -m "Update frontend"
git push origin main
cd frontend
vercel --prod
```

### Backup Supabase Data
Supabase Dashboard → **Database** → **Backups** → **Download**

---

## Cost Estimate

| Service | Free Tier | Paid (if exceed) |
|---|---|---|
| **Supabase** | 500MB DB, 2GB bandwidth/month | $25/month (Pro) |
| **Railway** | $5 credit/month (~500 hours) | $0.000463/GB-hour RAM |
| **Vercel** | 100GB bandwidth/month | $20/month (Pro) |
| **HiveMQ Cloud** | 100 connections, 10GB/month | Free tier cukup |
| **Google Gemini** | 15 requests/min free | Free tier cukup |

**Total for hobby project: $0-5/month**

---

## Security Notes

⚠️ **PENTING:**
1. Jangan commit file `.env` atau `Hardware/config.py` ke git
2. Rotate semua keys/passwords jika pernah ter-commit ke GitHub
3. Gunakan secret yang berbeda antara development dan production
4. Enable 2FA di Supabase, Railway, Vercel accounts

---

## Support

- Backend API Docs: `https://your-backend.up.railway.app/docs`
- Supabase Dashboard: `https://supabase.com/dashboard`
- Railway Dashboard: `https://railway.app/dashboard`
- Vercel Dashboard: `https://vercel.com/dashboard`
