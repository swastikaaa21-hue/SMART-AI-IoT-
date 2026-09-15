# Supabase Integration Setup Guide

Sistem SMART AI IoT sekarang terintegrasi dengan Supabase untuk remote database storage. Semua data user akan otomatis tersimpan di Supabase.

## Setup Steps

### 1. Buat Project Supabase

1. Buka https://supabase.com
2. Sign up / Login
3. Create New Project
4. Catat **Project URL** dan **API Keys**

### 2. Buat Tables di Supabase

Jalankan SQL berikut di Supabase SQL Editor:

```sql
-- Users Table
CREATE TABLE users (
    id VARCHAR(32) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Rooms Table
CREATE TABLE rooms (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    room_type VARCHAR(50),
    description TEXT,
    icon VARCHAR(50),
    owner_id VARCHAR(32) REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Devices Table
CREATE TABLE devices (
    id VARCHAR(36) PRIMARY KEY,
    device_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    device_type VARCHAR(50) NOT NULL,
    room_id VARCHAR(36) REFERENCES rooms(id) ON DELETE CASCADE,
    owner_id VARCHAR(32) REFERENCES users(id) ON DELETE CASCADE,
    state VARCHAR(20) DEFAULT 'off',
    is_online BOOLEAN DEFAULT false,
    firmware_version VARCHAR(50),
    description TEXT,
    extra_metadata JSONB,
    temperature FLOAT,
    humidity FLOAT,
    brightness INT,
    last_seen_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Telemetry Logs Table
CREATE TABLE telemetry_logs (
    id VARCHAR(36) PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    temperature FLOAT,
    humidity FLOAT,
    power_watts FLOAT,
    extra_data JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Command Logs Table
CREATE TABLE command_logs (
    id VARCHAR(36) PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    payload JSONB,
    source VARCHAR(50),
    status VARCHAR(20),
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Chat Sessions Table
CREATE TABLE chat_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(32) REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Chat Messages Table
CREATE TABLE chat_messages (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    function_call VARCHAR(100),
    function_response TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_rooms_owner ON rooms(owner_id);
CREATE INDEX idx_devices_room ON devices(room_id);
CREATE INDEX idx_devices_owner ON devices(owner_id);
CREATE INDEX idx_telemetry_device ON telemetry_logs(device_id);
CREATE INDEX idx_telemetry_timestamp ON telemetry_logs(timestamp DESC);
CREATE INDEX idx_commands_device ON command_logs(device_id);
CREATE INDEX idx_commands_timestamp ON command_logs(timestamp DESC);
CREATE INDEX idx_chat_sessions_user ON chat_sessions(user_id);
CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
```

### 3. Konfigurasi Environment Variables

Edit file `backend/.env`:

```env
# --- Supabase ---
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-anon-public-key-here
SUPABASE_SERVICE_KEY=your-service-role-key-here
```

**Cara mendapatkan keys:**
1. Buka Supabase Dashboard
2. Settings > API
3. Copy **Project URL** → `SUPABASE_URL`
4. Copy **anon public key** → `SUPABASE_KEY`
5. Copy **service_role key** → `SUPABASE_SERVICE_KEY` (hati-hati, jangan share!)

### 4. Test Koneksi

Jalankan backend:

```bash
cd backend
.\venv\Scripts\activate
uvicorn main:app --reload
```

Akses health check: http://localhost:8000/health

Response harus menunjukkan:
```json
{
  "status": "ok",
  "services": {
    "supabase": "connected",
    ...
  }
}
```

## Data Flow

Setiap operasi akan:
1. Simpan ke local SQLite (untuk performance)
2. Sync ke Supabase (untuk remote backup)
3. Jika Supabase gagal, operasi tetap berhasil (fail-safe)

### Data yang Tersimpan:

- ✅ User registration & profile updates
- ✅ Room create, update, delete
- ✅ Device create, update, delete
- ✅ Telemetry data (sensor readings)
- ✅ Command logs (device control history)
- ✅ Chat sessions & messages (AI conversations)

## Security Notes

- **SUPABASE_SERVICE_KEY** memiliki akses penuh, jangan commit ke git!
- Row Level Security (RLS) bisa diaktifkan di Supabase untuk keamanan ekstra
- Semua password di-hash sebelum disimpan

## Troubleshooting

**Supabase not configured:**
- Cek SUPABASE_URL dan SUPABASE_KEY sudah diisi di `.env`
- Restart backend setelah update `.env`

**Connection failed:**
- Cek internet connection
- Verify URL dan API key benar
- Cek quota Supabase project (free tier limit)

**Data tidak sync:**
- Cek logs di terminal backend
- Supabase sync bersifat optional, sistem tetap jalan jika gagal
- Data tetap tersimpan di local SQLite
