# Real-Time Track Creation from Session Data

## Overview

This feature automatically creates track sections in the `track_sections` collection when a GPS recording session is completed. The track section is created from the GPS data collected during the session, storing only latitude and longitude coordinates as requested.

## How It Works

### 1. Session Lifecycle

- **Create Session**: A new session is created with start and end points
- **Start Session**: Session becomes active and starts recording GPS data
- **GPS Data Collection**: GPS points are collected and stored in the session's `gps_data` array
- **Stop Session**: When stopped, the system automatically creates a track section from the collected GPS data

### 2. Track Section Creation Process

When a session is stopped (via `POST /api/sessions/{session_id}/stop`), the system:

1. **Extracts GPS Coordinates**: Retrieves all GPS data from the session
2. **Filters Data**: Extracts only `latitude` and `longitude` from each GPS point
3. **Generates Track ID**: Creates a unique track ID (`track_1`, `track_2`, etc.) based on existing tracks
4. **Creates Track Section**: Stores the track in the `track_sections` collection with:
   - `track_id`: Auto-generated (e.g., "track_1", "track_2")
   - `name`: "Real-time Recorded Data - {start_point} to {end_point}"
   - `filename`: "real time recorded data track id {number}"
   - `start_station`: Session start point
   - `end_station`: Session end point
   - `coordinates`: Array containing only latitude/longitude pairs
   - `is_active`: False (not activated by default)
   - `source_session_id`: Reference to the original session

## API Endpoints

### Automatic Track Creation

- **POST** `/api/sessions/{session_id}/stop` - Stops session and automatically creates track section

### Manual Track Creation

- **POST** `/api/sessions/{session_id}/create-track` - Manually create track section from existing session

## Example Usage

### 1. Create and Record a Session

```bash
# Create session
curl -X POST "http://localhost:8000/api/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "start_point": "colombo",
    "end_point": "kaluthara"
  }'

# Start session
curl -X POST "http://localhost:8000/api/sessions/{session_id}/start"

# Send GPS data (multiple points)
curl -X POST "http://localhost:8000/api/gps" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 6.495799061,
    "longitude": 80.06233458,
    "satellites": 11,
    "hdop": 0.88,
    "accuracy": 2.64,
    "timestamp": "2025-10-05 14:50:56 UTC",
    "device_id": "ESP32_GPS_01"
  }'

# Stop session (triggers track creation)
curl -X POST "http://localhost:8000/api/sessions/{session_id}/stop"
```

### 2. Verify Track Creation

```bash
# List all tracks
curl -X GET "http://localhost:8000/api/tracks"

# Get specific track coordinates
curl -X GET "http://localhost:8000/api/tracks/{track_id}/coordinates"
```

## Track Section Structure

The created track section follows this structure:

```json
{
  "track_id": "track_2",
  "name": "Real-time Recorded Data - colombo to kaluthara",
  "filename": "real time recorded data track id 2",
  "start_station": "colombo",
  "end_station": "kaluthara",
  "coordinates": [
    {
      "latitude": 6.495799061,
      "longitude": 80.06233458
    },
    {
      "latitude": 6.495830371,
      "longitude": 80.0623273
    }
    // ... more coordinates
  ],
  "is_active": false,
  "uploaded_at": "2025-10-05T14:53:10.297Z",
  "created_at": "2025-10-05T14:53:10.297Z",
  "source_session_id": "session_object_id",
  "gps_count": 7
}
```

## Key Features

### ✅ Requirements Met

- **Track ID Generation**: Automatically generates `track_1`, `track_2`, etc.
- **Filename Format**: Uses "real time recorded data track id {number}" format
- **Coordinates Only**: Stores only latitude and longitude (no satellites, hdop, accuracy, etc.)
- **Automatic Creation**: Triggered when session is stopped
- **Session Integration**: Links track to original session via `source_session_id`

### 🔧 Additional Features

- **Manual Creation**: Option to create track from existing session
- **Error Handling**: Graceful handling of sessions without GPS data
- **Logging**: Detailed console output for debugging
- **Validation**: Checks for valid coordinates before creating track

## Testing

Use the provided test script to verify functionality:

```bash
python test_session_track_creation.py
```

This script:

1. Creates a session with the provided GPS data
2. Starts the session
3. Sends GPS data points
4. Stops the session (triggers track creation)
5. Verifies the track section was created correctly

## Error Handling

The system handles various error conditions:

- **No GPS Data**: If session has no GPS data, track creation is skipped
- **Invalid Coordinates**: GPS points without lat/lon are filtered out
- **MongoDB Issues**: Connection problems are logged and handled gracefully
- **Session Not Found**: Proper error responses for invalid session IDs

## Integration with Existing System

This feature integrates seamlessly with the existing collision detection system:

- Created tracks can be activated using existing track management endpoints
- Track sections work with the GPS matching and collision detection logic
- No changes required to existing track upload or management functionality
