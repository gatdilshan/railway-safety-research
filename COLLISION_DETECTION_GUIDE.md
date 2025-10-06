# Railway Collision Detection System - User Guide

## Overview

This system implements an intelligent collision detection mechanism for railway tracks using GPS tracking. When two trains enter the same track section, the system automatically detects the collision risk and activates warning buzzers on both trains.

## How It Works

### 1. Track Definition

- Track sections are defined with GPS coordinates (latitude/longitude)
- The system loads track data from `actual train line 1 data.csv`
- Currently configured: **Panadura to Kalutara** (track_01)

### 2. GPS Matching Algorithm

When a train's GPS device sends data:

1. System compares GPS coordinates with track section coordinates
2. Finds the closest point on the track using Haversine distance formula
3. If distance < 30 meters (configurable), it's considered a "match"
4. System counts **consecutive matches**

### 3. Track Locking

- After **5 consecutive matches** (configurable), the track is "locked" to that train
- Lock includes: `train_id`, `device_id`, `track_id`
- Track status becomes "Active" with the train information

### 4. Collision Detection

When a second train's GPS also matches the same track:

1. System detects multiple locks on the same track
2. **COLLISION RISK** is triggered
3. Both trains' `active` and `collision_detected` flags are set to `true`
4. ESP32 devices receive the status and activate buzzers

## Configuration Parameters

Edit these in `server.py`:

```python
GPS_MATCH_THRESHOLD_METERS = 30.0    # Distance threshold for matching
REQUIRED_CONSECUTIVE_MATCHES = 5     # Matches needed to lock track
GPS_BUFFER_SIZE = 10                 # GPS points buffer size
```

## System Components

### 1. Server (server.py)

**New Collections:**

- `track_sections` - Stores track GPS coordinates
- `track_locks` - Manages track locks and match counters

**New API Endpoints:**

#### Track Management

```
GET  /api/tracks                    # Get all track sections
GET  /api/tracks/{track_id}/status  # Get track lock status
POST /api/tracks/reset              # Reset all tracks (for testing)
```

#### Train Status (Enhanced)

```
GET /api/train/status                    # Get all trains
GET /api/train/status?device_id=ESP32_GPS_01  # Get specific train by device
GET /api/train/status?train_id=TRAIN_01       # Get specific train by ID
```

#### Simulation & Testing

```
POST /api/simulate/gps                   # Simulate GPS data
GET  /api/simulate/scenario/collision    # Simulate collision scenario
```

### 2. ESP32 Device (sketch_sep28a.ino)

**Enhanced Features:**

- Queries train status by `device_id`
- Displays collision warnings in serial monitor
- Shows which trains are involved in collision
- Activates buzzer on collision detection

**Supported Devices:**

- `ESP32_GPS_01` → `TRAIN_01`
- `ESP32_GPS_02` → `TRAIN_02`

## Testing the System

### Method 1: API Simulation (No Physical Devices Needed)

#### Test Complete Collision Scenario

```bash
curl http://localhost:8000/api/simulate/scenario/collision
```

This automatically:

1. Resets all tracks
2. Simulates Train 1 entering the track (20 GPS points)
3. Simulates Train 2 entering the same track (overlapping points)
4. Returns collision status for both trains

#### Manual Step-by-Step Simulation

1. **Reset System**

```bash
curl -X POST http://localhost:8000/api/tracks/reset
```

2. **Simulate Train 1**

```bash
curl -X POST http://localhost:8000/api/simulate/gps \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_GPS_01",
    "track_id": "track_01",
    "start_index": 0,
    "num_points": 10
  }'
```

3. **Check Train 1 Status**

```bash
curl "http://localhost:8000/api/train/status?device_id=ESP32_GPS_01"
```

4. **Simulate Train 2 (Overlapping)**

```bash
curl -X POST http://localhost:8000/api/simulate/gps \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_GPS_02",
    "track_id": "track_01",
    "start_index": 5,
    "num_points": 10
  }'
```

5. **Check Collision Status**

```bash
curl http://localhost:8000/api/tracks/track_01/status
```

Expected Response:

```json
{
  "success": true,
  "track_id": "track_01",
  "locked": true,
  "lock_count": 2,
  "collision_risk": true,
  "locks": [
    { "train_id": "TRAIN_01", "device_id": "ESP32_GPS_01" },
    { "train_id": "TRAIN_02", "device_id": "ESP32_GPS_02" }
  ]
}
```

### Method 2: Physical ESP32 Devices

#### Setup

1. **Configure Device IDs:**

   - Device 1: Change `DEVICE_ID` to `"ESP32_GPS_01"` in sketch
   - Device 2: Change `DEVICE_ID` to `"ESP32_GPS_02"` in sketch

2. **Update Server IP:**

```cpp
const char* mongoAPIEndpoint = "http://YOUR_IP:8000/api/gps";
const char* trainStatusEndpoint = "http://YOUR_IP:8000/api/train/status";
```

3. **Upload and Monitor:**

```bash
# Terminal 1 - Device 1
arduino-cli monitor -p COM3

# Terminal 2 - Device 2
arduino-cli monitor -p COM4
```

#### Testing Collision

1. Start server with session active
2. Place both devices near the actual track (Panadura-Kalutara area)
3. When both devices' GPS matches the track:
   - Console shows: `🔒 Track locked by TRAIN_XX`
   - When second train enters: `🚨 COLLISION DETECTED!`
   - Both buzzers activate automatically

### Method 3: Using Dashboard

1. Open dashboard: `http://localhost:8000/dashboard`
2. Create and start a session
3. Click "Simulate Collision" button (if added to dashboard)
4. View real-time status updates

## Expected Console Output

### Server Console (Collision Detected)

```
📍 GPS Data saved: 6.5780798, 79.9621372 from ESP32_GPS_01
✅ Track match: distance=12.5m, consecutive=5
🔒 Track track_01 locked by TRAIN_01

📍 GPS Data saved: 6.5784595, 79.9619199 from ESP32_GPS_02
✅ Track match: distance=15.2m, consecutive=5
🔒 Track track_01 locked by TRAIN_02
🚨 COLLISION DETECTED on track_01!
   Trains involved: ['TRAIN_01', 'TRAIN_02']
```

### ESP32 Console (Collision Detected)

```
🚂 Train Status: ACTIVE
🚨 COLLISION DETECTED! ⚠️⚠️⚠️
   Collision with: TRAIN_02
   Current Track: track_01
🔊 BUZZER ACTIVATED - COLLISION WARNING!
```

## Monitoring & Status

### Check Track Status

```bash
curl http://localhost:8000/api/tracks/track_01/status
```

### Check All Trains

```bash
curl http://localhost:8000/api/train/status
```

### View Track Data

```bash
curl http://localhost:8000/api/tracks
```

## Troubleshooting

### Issue: GPS Not Matching Track

**Symptoms:** `consecutive_matches` stays at 0-1
**Solutions:**

- Check if GPS coordinates are within 30m of track
- Verify CSV file is loaded: check server startup logs
- Increase `GPS_MATCH_THRESHOLD_METERS` if needed
- Check `actual train line 1 data.csv` has valid coordinates

### Issue: Track Not Locking

**Symptoms:** Matches detected but track doesn't lock
**Solutions:**

- Need 5 consecutive matches (check `REQUIRED_CONSECUTIVE_MATCHES`)
- Ensure device is moving along the track continuously
- Check if GPS accuracy is good (< 10m)
- Reduce `REQUIRED_CONSECUTIVE_MATCHES` for testing

### Issue: Collision Not Detected

**Symptoms:** Both trains on track but no collision alert
**Solutions:**

- Ensure both devices have different `device_id`
- Check both trains are mapped correctly in `train_collection`
- Verify both trains have >= 5 consecutive matches
- Check server logs for lock status

### Issue: Buzzer Not Activating

**Symptoms:** Collision detected but buzzer silent
**Solutions:**

- Check ESP32 is querying status (every 5 seconds)
- Verify buzzer wiring (GPIO 23)
- Check server train status endpoint returns `active: true`
- Test buzzer manually: `digitalWrite(BUZZER_PIN, HIGH)`

## Database Schema

### train_details Collection

```json
{
  "train_id": "TRAIN_01",
  "device_id": "ESP32_GPS_01",
  "active": true,
  "collision_detected": true,
  "current_track": "track_01",
  "collision_with": ["TRAIN_02"],
  "updated_at": "2025-10-05T10:30:00Z"
}
```

### track_sections Collection

```json
{
  "track_id": "track_01",
  "name": "Panadura - Kalutara Section",
  "start_station": "Panadura",
  "end_station": "Kalutara",
  "coordinates": [
    {"latitude": 6.5780798, "longitude": 79.9621372},
    {"latitude": 6.5784595, "longitude": 79.9619199},
    ...
  ],
  "created_at": "2025-10-05T10:00:00Z"
}
```

### track_locks Collection

```json
{
  "lock_type": "track_lock",
  "track_id": "track_01",
  "train_id": "TRAIN_01",
  "device_id": "ESP32_GPS_01",
  "locked": true,
  "locked_at": "2025-10-05T10:30:00Z",
  "updated_at": "2025-10-05T10:30:15Z"
}
```

## Adding More Tracks

To add additional track sections:

1. Create CSV file with GPS coordinates (lat,lon format)
2. Modify `load_track_data_from_csv()` to load multiple files
3. Update collision detection logic to check all tracks

Example for multiple tracks:

```python
# In receive_gps_data function
for track in track_sections_collection.find():
    track_id = track["track_id"]
    match_result = check_gps_match_track(device_id, track_id, lat, lon)
    if match_result.get("locked"):
        # Process collision detection
```

## Safety Notes

⚠️ **This is a prototype system for research and demonstration purposes.**

- GPS accuracy affects detection reliability (typical: ±5-10 meters)
- System requires active WiFi connection
- Delays in status checking (5-second interval)
- Should be supplemented with additional safety systems in production
- Test thoroughly before any real-world deployment

## System Flow Diagram

```
ESP32 Device 1          Server                 ESP32 Device 2
     |                     |                          |
     |--GPS Data---------->|                          |
     |                     |--Check Track Match       |
     |                     |--5 Matches: Lock Track   |
     |<--Track Locked------|                          |
     |                     |                          |
     |                     |<--------GPS Data---------|
     |                     |--Check Track Match-------|
     |                     |--Already Locked!---------|
     |                     |--COLLISION DETECTED------|
     |<--Collision Alert---|                          |
     |--Activate Buzzer    |--Collision Alert-------->|
     |                     |        Activate Buzzer <-|
```

## API Response Examples

### GPS Data Response (With Collision)

```json
{
  "success": true,
  "message": "GPS data saved successfully",
  "data": {
    "latitude": 6.5780798,
    "longitude": 79.9621372,
    "device_id": "ESP32_GPS_01"
  },
  "track_match": {
    "matched": true,
    "distance": 12.5,
    "consecutive_matches": 5,
    "locked": true
  },
  "collision": {
    "collision": true,
    "track_id": "track_01",
    "trains_involved": ["TRAIN_01", "TRAIN_02"],
    "devices_involved": ["ESP32_GPS_01", "ESP32_GPS_02"],
    "warning": "⚠️ COLLISION DETECTED! Multiple trains on same track!"
  }
}
```

## Performance Considerations

- **GPS Update Rate:** 15 seconds (configurable in Arduino)
- **Status Check Rate:** 5 seconds (configurable in Arduino)
- **Track Matching:** O(n) where n = number of track points (~190 for track_01)
- **Collision Check:** O(1) database query

For high-frequency updates, consider:

- Indexing track coordinates with geospatial queries
- Caching track data in memory
- Using Redis for real-time status updates

## Future Enhancements

1. **Web Dashboard Integration**

   - Real-time track visualization
   - Alert history
   - Manual override controls

2. **Advanced Features**

   - Speed-based collision prediction
   - Multi-track support
   - Historical track data analysis
   - SMS/Email alerts

3. **Optimization**
   - Geospatial indexing (MongoDB GeoJSON)
   - WebSocket for real-time updates
   - Track segmentation for faster matching

## Support

For issues or questions:

1. Check server logs for detailed error messages
2. Verify MongoDB connection
3. Test with simulation endpoints first
4. Review troubleshooting section above

---

**Last Updated:** October 2025
**Version:** 2.0 - Collision Detection System
