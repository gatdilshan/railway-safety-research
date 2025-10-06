# Track Data Management System - User Guide

## 🎯 Overview

You can now **upload, manage, and switch between multiple track datasets** directly from the dashboard! No more manual file editing.

## ✨ New Features

### 1. **Upload CSV Track Data** 📤

- Upload any CSV file with GPS coordinates
- Supports standard format (lat, lon columns)
- Automatically stores in MongoDB
- No server restart needed!

### 2. **List All Tracks** 📋

- View all uploaded track datasets
- See which track is currently active
- Shows GPS point count, upload date, and route info
- Organized and easy to browse

### 3. **Activate/Use Track** ✅

- Click "Use This Track" to switch active dataset
- Active track is used for collision detection
- Automatically resets collision states
- Instant switching - no downtime

### 4. **Delete Tracks** 🗑️

- Remove unwanted track datasets
- Automatically activates another track if needed
- Cleans up associated data

## 🖥️ How to Use

### Step 1: Access Track Data Tab

1. Open dashboard: `http://localhost:8000/dashboard`
2. Click on **"🛤️ Track Data"** tab
3. You'll see the Track Data Management page

### Step 2: Upload New Track Data

1. **Fill in the form:**

   - **Track Name\*** (Required): e.g., "Panadura - Kalutara Section"
   - **Start Station** (Optional): e.g., "Panadura"
   - **End Station** (Optional): e.g., "Kalutara"
   - **CSV File\*** (Required): Select your CSV file

2. **CSV File Format:**

   ```csv
   lat,lon
   6.5780798,79.9621372
   6.5784595,79.9619199
   6.5788819,79.9616463
   ...
   ```

3. **Click "📤 Upload Track Data"**

4. **Success!** You'll see:
   - Confirmation message with track ID
   - GPS points count
   - Track appears in the list

### Step 3: View All Tracks

The track list shows:

- **Track Name** with status badge (✅ ACTIVE or inactive)
- **Track ID**: Unique identifier (track_01, track_02, etc.)
- **Filename**: Original CSV filename
- **Route**: Start → End stations
- **GPS Points**: Number of coordinates
- **Uploaded**: Date and time

**Active Track Example:**

```
┌─────────────────────────────────────────────────────┐
│ 🛤️ Panadura - Kalutara Section   ✅ ACTIVE         │
│                                                     │
│ Track ID: track_01                                  │
│ Filename: actual train line 1 data.csv             │
│ Route: Panadura → Kalutara                         │
│ GPS Points: 190 coordinates                         │
│ Uploaded: 10/5/2025, 2:30:45 PM                    │
│                                                     │
│ Currently in use for collision detection            │
│ [🗑️ Delete]                                         │
└─────────────────────────────────────────────────────┘
```

**Inactive Track Example:**

```
┌─────────────────────────────────────────────────────┐
│ 🛤️ Colombo - Galle Main Line                       │
│                                                     │
│ Track ID: track_02                                  │
│ Filename: colombo_galle.csv                         │
│ Route: Colombo Fort → Galle                        │
│ GPS Points: 450 coordinates                         │
│ Uploaded: 10/5/2025, 3:15:20 PM                    │
│                                                     │
│ [✅ Use This Track]  [🗑️ Delete]                    │
└─────────────────────────────────────────────────────┘
```

### Step 4: Switch Active Track

1. Find the track you want to use
2. Click **"✅ Use This Track"** button
3. Confirm the action

**What happens:**

- ✅ Selected track becomes active
- 🔄 All collision states reset
- 🔓 All track locks cleared
- 🚂 All trains deactivated
- 📍 New track used for GPS matching

### Step 5: Delete Track

1. Find the track to delete
2. Click **"🗑️ Delete"** button
3. Confirm deletion

**What happens:**

- 🗑️ Track removed from database
- 🔓 Associated locks cleared
- ✅ If it was active, another track auto-activates

## 🔧 Backend API Endpoints

### Upload Track

```http
POST /api/tracks/upload
Content-Type: application/json

{
  "file_content": "lat,lon\n6.578,79.962\n...",
  "filename": "mytrack.csv",
  "name": "My Track Name",
  "start_station": "Station A",
  "end_station": "Station B"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Track data uploaded successfully",
  "track": {
    "track_id": "track_02",
    "name": "My Track Name",
    "filename": "mytrack.csv",
    "points_count": 190,
    "is_active": false
  }
}
```

### List All Tracks

```http
GET /api/tracks
```

**Response:**

```json
{
  "success": true,
  "count": 2,
  "tracks": [
    {
      "track_id": "track_01",
      "name": "Panadura - Kalutara Section",
      "filename": "actual train line 1 data.csv",
      "start_station": "Panadura",
      "end_station": "Kalutara",
      "points_count": 190,
      "is_active": true,
      "uploaded_at": "2025-10-05T10:00:00Z"
    }
  ]
}
```

### Activate Track

```http
POST /api/tracks/{track_id}/activate
```

**Response:**

```json
{
  "success": true,
  "message": "Track track_02 is now active",
  "track_id": "track_02",
  "name": "My Track Name"
}
```

### Delete Track

```http
DELETE /api/tracks/{track_id}
```

**Response:**

```json
{
  "success": true,
  "message": "Track deleted successfully",
  "track_id": "track_02"
}
```

## 📊 How It Works

### System Flow:

```
1. Upload CSV File
   ↓
2. Parse lat/lon coordinates
   ↓
3. Store in MongoDB (track_sections collection)
   ↓
4. Generate unique track_id (track_01, track_02, etc.)
   ↓
5. First upload is automatically active
   ↓
6. Click "Use This Track" to switch active
   ↓
7. Active track used for GPS matching
   ↓
8. Collision detection uses active track
```

### Collision Detection Integration:

```
ESP32 sends GPS data
   ↓
Server receives data
   ↓
Find ACTIVE track from database
   ↓
Compare GPS with active track coordinates
   ↓
If matched: Lock track to train
   ↓
If second train matches same track: COLLISION!
```

## 🧪 Testing the System

### Test Scenario 1: Upload New Track

1. **Prepare CSV file:**

   ```csv
   lat,lon
   6.9271,79.8612
   6.9275,79.8615
   6.9280,79.8618
   ```

2. **Upload via dashboard:**

   - Track Name: "Test Track 1"
   - Start Station: "Point A"
   - End Station: "Point B"
   - File: test_track.csv

3. **Verify:**
   - Track appears in list
   - Shows correct point count
   - Upload date is today

### Test Scenario 2: Switch Active Track

1. **Upload two different tracks**
2. **Note which is active** (green badge)
3. **Click "Use This Track"** on inactive one
4. **Verify:**
   - Badge moves to new track
   - Old track shows "Use This Track" button
   - Collision states reset

### Test Scenario 3: Delete Track

1. **Upload a test track**
2. **Click Delete button**
3. **Confirm deletion**
4. **Verify:**
   - Track removed from list
   - If it was active, another track activated
   - No errors in console

### Test Scenario 4: Collision with Custom Track

1. **Upload track covering specific area**
2. **Click "Use This Track"**
3. **Simulate collision:**
   ```bash
   curl http://localhost:8000/api/simulate/scenario/collision
   ```
4. **Verify:**
   - Uses new track for matching
   - Collision detected correctly
   - Dashboard shows collision alert

## 🔍 Database Structure

### track_sections Collection:

```json
{
  "_id": ObjectId("..."),
  "track_id": "track_01",
  "name": "Panadura - Kalutara Section",
  "filename": "actual train line 1 data.csv",
  "start_station": "Panadura",
  "end_station": "Kalutara",
  "coordinates": [
    {"latitude": 6.5780798, "longitude": 79.9621372},
    {"latitude": 6.5784595, "longitude": 79.9619199},
    ...
  ],
  "is_active": true,
  "uploaded_at": "2025-10-05T10:00:00Z",
  "created_at": "2025-10-05T10:00:00Z"
}
```

## ⚙️ Configuration

### Default Track Loading:

- Server checks for existing tracks on startup
- If no tracks exist, loads from `actual train line 1 data.csv`
- Creates default track as active
- No manual intervention needed

### Track ID Generation:

- Automatically generates: `track_01`, `track_02`, `track_03`, etc.
- Sequential numbering
- No duplicates

### CSV Format Requirements:

- **Required columns:** `lat`, `lon`
- **Header row:** Must have column names
- **Data format:** Decimal degrees
- **Example:**
  ```csv
  lat,lon
  6.5780798,79.9621372
  6.5784595,79.9619199
  ```

## 🐛 Troubleshooting

### Issue: Upload Fails

**Solutions:**

- Check CSV format (must have lat, lon columns)
- Verify file is not empty
- Ensure coordinates are valid numbers
- Check browser console for errors

### Issue: Track Not Activating

**Solutions:**

- Refresh the page
- Check if server is running
- Verify track exists in database
- Look at server logs for errors

### Issue: Wrong Track Being Used

**Solutions:**

- Check which track has ✅ ACTIVE badge
- Click "Use This Track" on desired track
- Verify active track in database:
  ```bash
  curl http://localhost:8000/api/tracks
  ```

### Issue: Can't Delete Active Track

**Solution:**

- You CAN delete active tracks
- System auto-activates another track
- If it's the last track, collision detection won't work until you upload a new one

## 📝 Best Practices

1. **Naming Convention:**

   - Use descriptive names
   - Include start and end stations
   - Example: "Colombo Fort - Galle Main Line"

2. **Data Quality:**

   - Ensure GPS coordinates are accurate
   - Remove duplicate points
   - Keep points in sequential order

3. **Track Management:**

   - Keep backup CSV files
   - Document track routes
   - Test new tracks before production use

4. **Collision Detection:**
   - Always have one active track
   - Switch tracks only when safe
   - Reset collision states after switching

## 🎯 Use Cases

### Use Case 1: Multiple Routes

```
Track 1: Colombo - Galle (Main Line)
Track 2: Colombo - Kandy (Hill Country)
Track 3: Colombo - Batticaloa (East Line)

Switch between them as needed!
```

### Use Case 2: Testing

```
Track 1: Production Track (Active)
Track 2: Test Track (Inactive)
Track 3: Backup Track (Inactive)

Test with Track 2, switch back to Track 1
```

### Use Case 3: Different Time Periods

```
Track 1: Morning Route (Peak Hours)
Track 2: Evening Route (Off-Peak)
Track 3: Night Route (Limited Service)

Activate based on time of day
```

## ✅ Success Checklist

After implementation, verify:

- [ ] Can access Track Data tab
- [ ] Upload form appears correctly
- [ ] Can upload CSV file successfully
- [ ] Uploaded tracks appear in list
- [ ] Active track shows ✅ ACTIVE badge
- [ ] "Use This Track" button works
- [ ] Switching tracks resets collision states
- [ ] Delete button works
- [ ] Can upload multiple tracks
- [ ] Collision detection uses active track

## 🚀 Summary

**What You Can Do Now:**

1. ✅ Upload unlimited track datasets
2. ✅ Switch between tracks instantly
3. ✅ Delete unwanted tracks
4. ✅ See all tracks in one place
5. ✅ No server restart needed
6. ✅ All managed from dashboard
7. ✅ Collision detection uses active track

**Key Benefits:**

- 🎯 **Flexibility**: Multiple track support
- 🚀 **Easy Management**: All in dashboard
- 🔄 **Instant Switching**: No downtime
- 💾 **Persistent Storage**: MongoDB database
- 🛡️ **Safe Operations**: Automatic state resets
- 📊 **Visual Feedback**: Clear active indicator

---

**Ready to use!** Upload your first custom track and see it in action! 🎉

**Quick Start:** Go to Dashboard → Track Data Tab → Upload your CSV file!
