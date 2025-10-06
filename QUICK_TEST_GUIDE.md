# Quick Test Guide - Collision Detection System

## Prerequisites

- Python environment with dependencies installed
- MongoDB connection working
- CSV file: `actual train line 1 data.csv` in project root

## Quick Start (5 Minutes)

### Step 1: Start the Server

```bash
python server.py
```

Expected output:

```
✅ Connected to MongoDB
✅ Train details collection initialized
✅ Loaded track data: 190 GPS points
   Track ID: track_01
   Route: Panadura → Kalutara
🚀 Starting GPS Tracker FastAPI Server...
🛤️  Collision Detection System Active
```

### Step 2: Test Collision Scenario (One Command!)

```bash
curl http://localhost:8000/api/simulate/scenario/collision
```

**What this does:**

1. Resets all tracks and trains
2. Simulates TRAIN_01 entering track (20 GPS points)
3. Simulates TRAIN_02 entering same track (overlapping)
4. Returns collision status

**Expected Response:**

```json
{
  "success": true,
  "message": "Collision scenario simulated",
  "collision_detected": true,
  "train1": {
    "train_id": "TRAIN_01",
    "active": true,
    "collision_detected": true,
    "collision_with": ["TRAIN_02"]
  },
  "train2": {
    "train_id": "TRAIN_02",
    "active": true,
    "collision_detected": true,
    "collision_with": ["TRAIN_01"]
  },
  "track_status": {
    "track_id": "track_01",
    "locked": true,
    "lock_count": 2,
    "collision_risk": true
  }
}
```

✅ **If you see `"collision_detected": true` - System is working!**

## Manual Testing (Step by Step)

### 1. Reset System

```bash
curl -X POST http://localhost:8000/api/tracks/reset
```

### 2. Send Train 1 onto Track

```bash
curl -X POST http://localhost:8000/api/simulate/gps \
  -H "Content-Type: application/json" \
  -d '{"device_id": "ESP32_GPS_01", "start_index": 0, "num_points": 10}'
```

**Server logs should show:**

```
📍 GPS Data saved...
✅ Track match: consecutive=1
✅ Track match: consecutive=2
...
✅ Track match: consecutive=5
🔒 Track track_01 locked by TRAIN_01
```

### 3. Check Train 1 Status

```bash
curl "http://localhost:8000/api/train/status?device_id=ESP32_GPS_01"
```

**Expected:** `"active": true, "current_track": "track_01"`

### 4. Send Train 2 onto Same Track

```bash
curl -X POST http://localhost:8000/api/simulate/gps \
  -H "Content-Type: application/json" \
  -d '{"device_id": "ESP32_GPS_02", "start_index": 5, "num_points": 10}'
```

**Server logs should show:**

```
🔒 Track track_01 locked by TRAIN_02
🚨 COLLISION DETECTED on track_01!
   Trains involved: ['TRAIN_01', 'TRAIN_02']
```

### 5. Verify Collision

```bash
curl http://localhost:8000/api/tracks/track_01/status
```

**Expected:** `"collision_risk": true, "lock_count": 2`

## Configuration Testing

### Test Different Match Thresholds

Edit `server.py`:

```python
GPS_MATCH_THRESHOLD_METERS = 50.0  # Increase from 30m
```

Restart server and re-test. More GPS points should match.

### Test Match Requirements

Edit `server.py`:

```python
REQUIRED_CONSECUTIVE_MATCHES = 3  # Reduce from 5
```

Track locks faster with fewer matches required.

## Using Postman or Browser

### View All Tracks

```
GET http://localhost:8000/api/tracks
```

### View All Trains

```
GET http://localhost:8000/api/train/status
```

### Get Specific Train Status

```
GET http://localhost:8000/api/train/status?device_id=ESP32_GPS_01
```

### Reset Everything

```
POST http://localhost:8000/api/tracks/reset
```

## Testing with Real ESP32 Devices

### Device Setup

1. **Update sketch_sep28a.ino:**

```cpp
// Device 1
const char* DEVICE_ID = "ESP32_GPS_01";
const char* mongoAPIEndpoint = "http://192.168.1.9:8000/api/gps";
const char* trainStatusEndpoint = "http://192.168.1.9:8000/api/train/status";
```

2. **Upload to both devices** (change DEVICE_ID for second device)

3. **Create session via dashboard or API:**

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"start_point": "Panadura", "end_point": "Kalutara"}'

# Get session ID from response, then start it:
curl -X POST http://localhost:8000/api/sessions/{SESSION_ID}/start
```

4. **Monitor both devices:**
   - Open Serial Monitor for both
   - Place devices near actual track (Panadura-Kalutara area)
   - Watch for collision detection messages

### Expected Device Output (Collision)

```
🚂 Train Status: ACTIVE
🚨 COLLISION DETECTED! ⚠️⚠️⚠️
   Collision with: TRAIN_02
   Current Track: track_01
🔊 BUZZER ACTIVATED - COLLISION WARNING!
```

## Troubleshooting Quick Checks

### ❌ CSV Not Loading

```bash
# Check file exists
ls -la "actual train line 1 data.csv"

# Check first few lines
head -5 "actual train line 1 data.csv"
```

### ❌ MongoDB Not Connected

```bash
# Check logs for connection string
# Verify: mongodb+srv://oshen:oshen@cluster0...

# Test with manual query
curl http://localhost:8000/api/train/status
```

### ❌ GPS Not Matching

```bash
# View track coordinates
curl http://localhost:8000/api/tracks

# Check first coordinate: lat=6.5780798, lon=79.9621372
# Your GPS must be within 30m of these points
```

### ❌ No Collision Detected

```bash
# Verify both trains locked track
curl http://localhost:8000/api/tracks/track_01/status

# Should show lock_count: 2
# If lock_count: 1, second train didn't match track
```

## Success Indicators

✅ **Server starts successfully**

- All collections initialized
- Track data loaded (190 points)

✅ **Simulation works**

- `/api/simulate/scenario/collision` returns collision=true
- Both trains show active=true, collision_detected=true

✅ **Real devices work** (if using physical ESP32)

- Devices connect to WiFi
- GPS data sent to server
- Status polled every 5 seconds
- Buzzer activates on collision

## Common Test Scenarios

### Scenario 1: Normal Operation (No Collision)

```bash
# Train 1 goes first 50 points
curl -X POST http://localhost:8000/api/simulate/gps \
  -d '{"device_id": "ESP32_GPS_01", "start_index": 0, "num_points": 50}'

# Train 2 goes next 50 points (no overlap)
curl -X POST http://localhost:8000/api/simulate/gps \
  -d '{"device_id": "ESP32_GPS_02", "start_index": 100, "num_points": 50}'

# Check: collision_detected should be FALSE
```

### Scenario 2: Head-on Collision

```bash
# Train 1 from start
curl -X POST http://localhost:8000/api/simulate/gps \
  -d '{"device_id": "ESP32_GPS_01", "start_index": 0, "num_points": 20}'

# Train 2 from start (same section!)
curl -X POST http://localhost:8000/api/simulate/gps \
  -d '{"device_id": "ESP32_GPS_02", "start_index": 0, "num_points": 20}'

# Check: collision_detected should be TRUE
```

### Scenario 3: Chase Collision

```bash
# Train 1 ahead
curl -X POST http://localhost:8000/api/simulate/gps \
  -d '{"device_id": "ESP32_GPS_01", "start_index": 30, "num_points": 20}'

# Train 2 behind, catching up
curl -X POST http://localhost:8000/api/simulate/gps \
  -d '{"device_id": "ESP32_GPS_02", "start_index": 25, "num_points": 20}'

# Check: collision_detected should be TRUE (overlapping ranges)
```

## Performance Metrics

Monitor server logs for timing:

```
📍 GPS Data saved: 6.5780798, 79.9621372
✅ Track match calculated in ~2ms
🔒 Track locked in ~5ms
🚨 Collision detected in ~3ms
```

Total processing time per GPS point: **~10ms**

## Next Steps

After successful testing:

1. ✅ Review `COLLISION_DETECTION_GUIDE.md` for full documentation
2. ✅ Configure for production deployment (if needed)
3. ✅ Add more track sections (CSV files)
4. ✅ Integrate with web dashboard for visualization

## Quick Command Reference

```bash
# Start server
python server.py

# Full collision test
curl http://localhost:8000/api/simulate/scenario/collision

# Reset system
curl -X POST http://localhost:8000/api/tracks/reset

# Check status
curl http://localhost:8000/api/train/status
curl http://localhost:8000/api/tracks/track_01/status

# Simulate single train
curl -X POST http://localhost:8000/api/simulate/gps \
  -H "Content-Type: application/json" \
  -d '{"device_id": "ESP32_GPS_01", "start_index": 0, "num_points": 10}'
```

---

**Need help?** Check `COLLISION_DETECTION_GUIDE.md` for detailed troubleshooting.
