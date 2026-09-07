# 🧪 Testing Guide - Real-Time Dashboard

## Quick Start Testing

### 1. Jalankan Backend
```bash
cd backend
python main.py
# Backend akan berjalan di http://localhost:8000
```

### 2. Buka Dashboard
```bash
# Buka di browser:
http://localhost:8000/
# atau jika menggunakan Live Server:
http://localhost:5500/index.html
```

### 3. Cek Koneksi Real-Time
1. Buka browser **DevTools** (F12)
2. Lihat **Console** tab
3. Anda harus melihat:
   ```
   🟢 WebSocket Connected - Real-time updates active
   ✅ WebSocket acknowledged: Connected to SMART AI IoT real-time stream
   ```

4. Buka tab **Settings** di dashboard
5. Di bagian "WebSocket Realtime" harus tertulis: **🟢 Tersambung Real-Time**

---

## Test Scenarios

### ✅ TEST 1: Basic Device Control (Single Tab)

**Langkah:**
1. Buka dashboard Home
2. Klik salah satu Room Card (misalnya "Kamar")
3. Toggle salah satu device (klik tombol ON/OFF)

**Expected Result:**
- ✅ UI langsung berubah (tidak delay)
- ✅ Toast notification muncul: "✅ Lampu Kamar: ON"
- ✅ Audio feedback terdengar
- ✅ Di console muncul: `📩 WebSocket message: device_status_update`
- ✅ Border device card berubah warna (biru untuk ON)
- ✅ Indicator dot berubah dari abu-abu ke hijau dengan pulse animation

**Screenshot Console:**
```
🔄 Device Lampu Kamar updated to ON via real-time sync
📩 WebSocket message: device_status_update {device_id: "dev-km-1", state: "on", ...}
```

---

### ✅ TEST 2: Multi-Tab Sync

**Langkah:**
1. Buka dashboard di **2 tab berbeda** (Tab A dan Tab B)
2. Di **Tab A**: Navigate ke Room "Kamar"
3. Di **Tab A**: Nyalakan "Lampu Kamar" (klik ON)
4. Lihat **Tab B** (jangan refresh)

**Expected Result:**
- ✅ **Tab B** otomatis update tanpa refresh
- ✅ **Tab B** menampilkan toast: "🔔 Lampu Kamar → ON"
- ✅ Device card di **Tab B** ter-highlight dengan ring animation
- ✅ Jumlah "aktif" di Room Card update otomatis

**How to Verify:**
```
Tab A Console:
✅ Lampu Kamar: ON

Tab B Console:
📩 WebSocket message: device_status_update
🔄 Device Lampu Kamar updated to ON via real-time sync
🔔 Lampu Kamar → ON
```

---

### ✅ TEST 3: AI Command Real-Time Sync

**Langkah:**
1. Pastikan semua lampu di "Kamar" dalam status OFF
2. Buka dashboard di **Tab A** - lihat view "Remote"
3. Buka dashboard di **Tab B** - buka "AI Assistant" (klik ikon 🎙️)
4. Di **Tab B AI**: ketik `Nyalakan lampu kamar` dan submit

**Expected Result:**
- ✅ **Tab B**: AI merespons "Beres, lampu Kamar udah dinyalakan!"
- ✅ **Tab A**: Tanpa refresh, lampu kamar otomatis menyala
- ✅ **Tab A**: Device card ter-highlight dengan ring animation
- ✅ **Tab A**: Toast notification: "🔔 Lampu Kamar → ON"

---

### ✅ TEST 4: Temperature Control Sync

**Langkah:**
1. Buka **2 tab** berbeda
2. **Tab A**: Navigate ke Room "Kamar"
3. **Tab A**: Nyalakan AC Kamar terlebih dahulu (klik ON)
4. **Tab A**: Klik tombol `+` untuk menaikkan suhu AC dari 24°C ke 26°C
5. Lihat **Tab B**

**Expected Result:**
- ✅ **Tab A**: Suhu langsung update ke 26°C (optimistic)
- ✅ **Tab A**: Toast: "❄️ AC Kamar suhu: 26°C"
- ✅ **Tab B**: Suhu AC otomatis update ke 26°C
- ✅ **Tab B**: Toast: "🔔 AC Kamar → ON" (dengan temperature update)

---

### ✅ TEST 5: Scene Activation

**Langkah:**
1. Navigate ke Room "Kamar"
2. Pastikan beberapa device dalam status ON (misalnya Lampu dan TV)
3. Klik tombol **"Aktifkan Scene"** di bagian "Mode Ruangan"

**Expected Result:**
- ✅ Toast: "🎬 Mengaktifkan Mode Tidur..."
- ✅ Semua lampu dan TV mati
- ✅ AC menyala dan set ke 24°C
- ✅ Setelah 0.5 detik: Toast "✨ Scene Mode Tidur aktif!"
- ✅ Multiple WebSocket messages di console untuk setiap device
- ✅ Visual update smooth untuk semua devices

---

### ✅ TEST 6: WebSocket Reconnection

**Langkah:**
1. Buka dashboard (pastikan WebSocket connected)
2. **Stop backend server** (Ctrl+C di terminal)
3. Lihat dashboard

**Expected Result:**
- ✅ Toast: Connection lost
- ✅ Status di Settings berubah: "🔄 Menghubungkan ulang..."
- ✅ Console: `🔴 WebSocket Disconnected - attempting reconnect...`

**Langkah Lanjutan:**
4. **Start backend server** kembali (`python main.py`)
5. Tunggu beberapa detik

**Expected Result:**
- ✅ WebSocket otomatis reconnect
- ✅ Toast: "🔗 Real-time sync aktif!"
- ✅ Status: "🟢 Tersambung Real-Time"
- ✅ Console: `🟢 WebSocket Connected - Real-time updates active`

---

### ✅ TEST 7: Offline Graceful Handling

**Langkah:**
1. Disconnect internet / matikan WiFi
2. Coba toggle device di dashboard

**Expected Result:**
- ✅ UI tetap update (optimistic)
- ✅ Setelah timeout, muncul toast: "❌ Gagal mengontrol [Device Name]"
- ✅ Device state rollback ke kondisi sebelumnya
- ✅ Aplikasi tidak crash

---

### ✅ TEST 8: Visual Feedback & Animation

**What to Check:**
1. **Device Card Border**
   - OFF: Gray border
   - ON: Blue border (brand color) dengan shadow

2. **Status Indicator Dot**
   - OFF: Gray static dot
   - ON: Green dot dengan `pulse-subtle` animation

3. **Real-time Change Highlight**
   - Ketika device berubah dari remote: Ring animation selama 1.5 detik

4. **Temperature Display**
   - Ketika temperature update: Teks jadi biru bold selama 2 detik

5. **Button Press**
   - Active scale: `active:scale-95`
   - Audio feedback sesuai aksi (beep untuk ON, off sound untuk OFF)

---

## Debugging Tools

### Console Commands

Buka browser console dan ketik:

```javascript
// Cek status WebSocket
window.app._ws.readyState
// 0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED

// Cek jumlah devices
window.app.rooms.forEach(r => console.log(r.name, r.devices.length))

// Force reconnect WebSocket
window.app._ws.close()

// Trigger manual device update
window.app.updateDeviceStateFromWS({
  device_id: 'dev-km-1',
  state: 'on',
  brightness: 100
})

// Cek reconnection attempts
window.app._wsReconnectAttempts
```

### Network Tab (Chrome DevTools)

1. Open DevTools → Network tab
2. Filter: `WS` (WebSocket)
3. You should see: `ws://localhost:8000/api/v1/ws?token=...`
4. Click on it to see frames (messages)

**Healthy WebSocket:**
- Status: `101 Switching Protocols`
- Type: `websocket`
- Frames tab shows messages flowing

---

## Performance Checks

### Expected Behavior:

| Action | UI Update | Backend Call | WebSocket Broadcast | Total Time |
|--------|-----------|--------------|---------------------|------------|
| Toggle Device | Instant (0ms) | ~50-100ms | ~20ms | <150ms |
| AI Command | ~500ms | ~200ms | ~20ms | <800ms |
| Scene Activation | Instant | Batch 100ms | Multiple | <1s |
| Remote Update | N/A | N/A | Instant | <50ms |

### Warning Signs:

❌ WebSocket reconnecting setiap beberapa detik → Check MQTT/Backend
❌ Device tidak sync antar tab → Check browser console errors
❌ Toast tidak muncul → Check `showToast()` implementation
❌ Optimistic update tidak rollback saat error → Check try-catch blocks

---

## Common Issues & Solutions

### Issue: "WebSocket connection failed"
**Solution:**
1. Pastikan backend berjalan di port 8000
2. Check JWT token valid: `localStorage.getItem('smarthome_token')`
3. Coba re-login atau refresh halaman

### Issue: "Device update tidak real-time"
**Solution:**
1. Check WebSocket status di Settings tab
2. Pastikan `device_id` match antara frontend & backend
3. Check console untuk WebSocket messages

### Issue: "Multi-tab tidak sync"
**Solution:**
1. Pastikan kedua tab menggunakan user/token yang sama
2. Check kedua tab ter-connect ke WebSocket
3. Broadcast harus ke semua connections

### Issue: "Optimistic update stuck"
**Solution:**
1. Check network response (DevTools → Network)
2. Rollback mechanism harus di try-catch
3. Pastikan `previousState` tersimpan sebelum update

---

## Success Criteria ✅

Dashboard real-time dianggap **SUKSES** jika:

- [x] WebSocket connect otomatis saat dashboard load
- [x] Device toggle instant (optimistic update)
- [x] Perubahan di tab A langsung terlihat di tab B
- [x] AI command update dashboard tanpa refresh
- [x] Toast notification muncul untuk setiap aksi
- [x] Visual animation smooth dan responsive
- [x] Reconnect otomatis saat connection lost
- [x] Rollback otomatis jika command gagal
- [x] Telemetry update real-time (temperature, humidity)
- [x] Console logging jelas untuk debugging

---

## Next Steps (Optional Enhancements)

1. **Presence Indicator**: Show berapa tab/user yang online
2. **Command Queue**: Retry failed commands automatically
3. **Offline Mode**: Queue commands when offline, sync when online
4. **Push Notifications**: Browser notifications untuk perubahan penting
5. **Live Activity Log**: Real-time stream of all actions
6. **Device Health Monitor**: Auto-detect offline devices
7. **Conflict Resolution**: Handle simultaneous updates from multiple users

---

**Testing Completed**: ✅
**Ready for Production**: Yes (dengan backend & MQTT configured)
