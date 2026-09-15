# 🚀 Panduan Deployment SMART AI IoT

## 📋 Persiapan

Pastikan sudah punya:
- Akun [Railway](https://railway.app)
- Akun [Vercel](https://vercel.com)
- Git repository sudah push ke GitHub

---

## 🔧 STEP 1: Deploy Backend ke Railway

### 1.1 Create New Project
1. Buka https://railway.app/dashboard
2. Klik **"New Project"**
3. Pilih **"Deploy from GitHub repo"**
4. Pilih repository **SMART-AI-IoT-**
5. Pilih **"Deploy Now"**

### 1.2 Set Environment Variables
Setelah project dibuat:

1. Klik tab **"Variables"**
2. Klik **"+ Add Variable"** atau **"RAW Editor"**
3. Copy paste semua variable dari file `backend/.env.railway.example`

⚠️ **LIHAT FILE `backend/.env.railway.example` UNTUK NILAI LENGKAP**

Variable yang wajib diset:
- `APP_ENV=production`
- `DEBUG=false`
- `MQTT_BROKER` (dari .env.railway.example)
- `MQTT_USERNAME` (dari .env.railway.example)
- `MQTT_PASSWORD` (dari .env.railway.example)
- `GEMINI_API_KEY` (dari .env.railway.example)
- `SECRET_KEY` (dari .env.railway.example)
- `SUPABASE_URL` (dari .env.railway.example)
- `SUPABASE_KEY` (dari .env.railway.example)
- `SUPABASE_SERVICE_KEY` (dari .env.railway.example)
- `BACKEND_CORS_ORIGINS=https://your-vercel-app.vercel.app,http://localhost:3000`

⚠️ **PENTING**: Jangan ubah `BACKEND_CORS_ORIGINS` dulu, nanti diupdate setelah dapat Vercel URL

4. Klik **"Save"**

### 1.3 Set Root Directory
1. Klik tab **"Settings"**
2. Scroll ke **"Service Settings"**
3. Di **"Root Directory"**, isi: `backend`
4. Klik **"Save"**

### 1.4 Generate Domain
1. Klik tab **"Settings"**
2. Scroll ke **"Networking"**
3. Klik **"Generate Domain"**
4. **COPY URL** yang dihasilkan (format: `xxx.up.railway.app`)

📝 **SIMPAN URL INI**, nanti dipakai di frontend!

### 1.5 Verifikasi Deployment
Tunggu 2-3 menit, lalu cek:
```
https://your-railway-url.up.railway.app/health
```

Harus return JSON:
```json
{
  "status": "ok",
  "version": "3.0.0",
  "environment": "production"
}
```

---

## 🌐 STEP 2: Deploy Frontend ke Vercel

### 2.1 Update Railway URL di Frontend
1. Buka file `frontend/index.html`
2. Cari baris 1094 (search: `RAILWAY_BACKEND_URL`)
3. Ganti URL:
```javascript
const RAILWAY_BACKEND_URL = 'https://your-railway-url.up.railway.app';
```
Ganti `your-railway-url.up.railway.app` dengan URL Railway dari Step 1.4

4. **COMMIT & PUSH**:
```bash
git add frontend/index.html
git commit -m "chore: update Railway backend URL"
git push
```

### 2.2 Deploy ke Vercel
1. Buka https://vercel.com/new
2. Klik **"Import Git Repository"**
3. Pilih repository **SMART-AI-IoT-**
4. Di **"Configure Project"**:
   - **Framework Preset**: Other
   - **Root Directory**: `frontend`
   - Klik **"Edit"** untuk Root Directory, pilih folder `frontend`
5. Klik **"Deploy"**

### 2.3 Copy Vercel URL
Setelah deployment selesai:
1. Vercel akan show URL (format: `xxx.vercel.app`)
2. **COPY URL INI**

---

## 🔗 STEP 3: Update CORS di Railway

Sekarang update CORS agar Railway accept request dari Vercel:

1. Buka Railway dashboard > project kamu
2. Klik tab **"Variables"**
3. Cari variable **"BACKEND_CORS_ORIGINS"**
4. Update value jadi:
```
https://your-vercel-url.vercel.app,http://localhost:3000
```
Ganti `your-vercel-url.vercel.app` dengan URL Vercel dari Step 2.3

5. Klik **"Save"**
6. Railway akan auto-redeploy (tunggu 1-2 menit)

---

## ✅ STEP 4: Test Connection

### 4.1 Test dari Browser
1. Buka URL Vercel kamu: `https://your-vercel-url.vercel.app`
2. Klik **"GET STARTED"**
3. Klik **"Server Settings"** (tab paling kanan)
4. Isi form server setup lalu klik **"Simpan & Buat Server"**
5. Kalau berhasil, tidak ada error **"Cannot connect to server"**

### 4.2 Cek di Browser Console
1. Buka Developer Tools (F12)
2. Tab **"Console"**
3. Tidak boleh ada error CORS atau Network Failed

### 4.3 Cek WebSocket
1. Login/register user
2. Cek status assistant di dashboard, harus **"Online"** (hijau)

---

## 🐛 Troubleshooting

### Error: "Cannot connect to server"
- Cek Railway deployment success: `https://your-railway-url.up.railway.app/health`
- Cek CORS sudah benar include Vercel URL
- Cek browser console untuk detail error

### Error: CORS policy blocked
- Update `BACKEND_CORS_ORIGINS` di Railway Variables
- Pastikan format: `https://xxx.vercel.app,http://localhost:3000`
- No trailing slash di URL

### WebSocket connection failed
- Railway URL di `frontend/index.html` sudah benar?
- WebSocket auto-detect https → wss
- Cek Railway logs ada error?

### Railway build failed
- Cek Root Directory = `backend`
- Cek `requirements.txt` ada
- Cek `Procfile` dan `railway.json` ada di folder backend

---

## 📝 Summary Checklist

- [ ] Railway project created
- [ ] Railway environment variables set (dari `.env.railway.example`)
- [ ] Railway Root Directory = `backend`
- [ ] Railway domain generated & copied
- [ ] Railway `/health` endpoint returns OK
- [ ] Frontend `index.html` updated with Railway URL
- [ ] Git commit & push perubahan frontend
- [ ] Vercel project deployed dengan Root Directory = `frontend`
- [ ] Vercel URL copied
- [ ] Railway CORS updated dengan Vercel URL
- [ ] Test frontend bisa konek ke backend
- [ ] WebSocket status "Online"

---

## 🎉 Selesai!

Aplikasi sudah online:
- **Frontend**: https://your-vercel-url.vercel.app
- **Backend**: https://your-railway-url.up.railway.app
- **API Docs**: https://your-railway-url.up.railway.app/docs
