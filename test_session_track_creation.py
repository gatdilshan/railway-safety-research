#!/usr/bin/env python3
"""
Test script to demonstrate session track creation functionality
"""

import requests
import json
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

def test_session_track_creation():
    """
    Test the new functionality to create track sections from session GPS data
    """
    print("🧪 Testing Session Track Creation Functionality")
    print("=" * 50)
    
    # Sample GPS data from the user's request
    sample_gps_data = [
        {
            "latitude": 6.495799061,
            "longitude": 80.06233458,
            "satellites": 11,
            "hdop": 0.88,
            "accuracy": 2.64,
            "timestamp": "2025-10-05 14:50:56 UTC",
            "device_id": "ESP32_GPS_01",
            "received_at": datetime.utcnow().isoformat()
        },
        {
            "latitude": 6.495830371,
            "longitude": 80.0623273,
            "satellites": 12,
            "hdop": 0.78,
            "accuracy": 2.34,
            "timestamp": "2025-10-05 14:51:40 UTC",
            "device_id": "ESP32_GPS_01",
            "received_at": datetime.utcnow().isoformat()
        },
        {
            "latitude": 6.495818797,
            "longitude": 80.06232984,
            "satellites": 12,
            "hdop": 0.88,
            "accuracy": 2.64,
            "timestamp": "2025-10-05 14:52:01 UTC",
            "device_id": "ESP32_GPS_01",
            "received_at": datetime.utcnow().isoformat()
        },
        {
            "latitude": 6.495833501,
            "longitude": 80.06230887,
            "satellites": 12,
            "hdop": 0.86,
            "accuracy": 2.58,
            "timestamp": "2025-10-05 14:52:16 UTC",
            "device_id": "ESP32_GPS_01",
            "received_at": datetime.utcnow().isoformat()
        },
        {
            "latitude": 6.495857444,
            "longitude": 80.06227864,
            "satellites": 12,
            "hdop": 0.77,
            "accuracy": 2.31,
            "timestamp": "2025-10-05 14:52:29 UTC",
            "device_id": "ESP32_GPS_01",
            "received_at": datetime.utcnow().isoformat()
        },
        {
            "latitude": 6.49587185,
            "longitude": 80.06225845,
            "satellites": 12,
            "hdop": 0.78,
            "accuracy": 2.34,
            "timestamp": "2025-10-05 14:52:46 UTC",
            "device_id": "ESP32_GPS_01",
            "received_at": datetime.utcnow().isoformat()
        },
        {
            "latitude": 6.495862358,
            "longitude": 80.06226416,
            "satellites": 12,
            "hdop": 0.72,
            "accuracy": 2.16,
            "timestamp": "2025-10-05 14:52:59 UTC",
            "device_id": "ESP32_GPS_01",
            "received_at": datetime.utcnow().isoformat()
        }
    ]
    
    try:
        # Step 1: Create a new session
        print("📝 Step 1: Creating a new session...")
        session_data = {
            "start_point": "colombo",
            "end_point": "kaluthara"
        }
        
        response = requests.post(f"{BASE_URL}/api/sessions", json=session_data)
        if response.status_code == 200:
            session_info = response.json()
            session_id = session_info["data"]["id"]
            print(f"✅ Session created: {session_id}")
            print(f"   Route: {session_data['start_point']} → {session_data['end_point']}")
        else:
            print(f"❌ Failed to create session: {response.text}")
            return
        
        # Step 2: Start the session
        print("\n▶️ Step 2: Starting the session...")
        response = requests.post(f"{BASE_URL}/api/sessions/{session_id}/start")
        if response.status_code == 200:
            print("✅ Session started successfully")
        else:
            print(f"❌ Failed to start session: {response.text}")
            return
        
        # Step 3: Send GPS data to the session
        print("\n📍 Step 3: Sending GPS data...")
        for i, gps_point in enumerate(sample_gps_data):
            response = requests.post(f"{BASE_URL}/api/gps", json=gps_point)
            if response.status_code == 200:
                print(f"✅ GPS point {i+1}/{len(sample_gps_data)} sent: {gps_point['latitude']}, {gps_point['longitude']}")
            else:
                print(f"❌ Failed to send GPS point {i+1}: {response.text}")
        
        # Step 4: Stop the session (this should trigger track section creation)
        print("\n⏹️ Step 4: Stopping the session...")
        response = requests.post(f"{BASE_URL}/api/sessions/{session_id}/stop")
        if response.status_code == 200:
            result = response.json()
            print("✅ Session stopped successfully")
            if result.get("track_section_created"):
                print("🛤️ Track section created automatically from session data!")
            else:
                print("⚠️ No track section was created")
        else:
            print(f"❌ Failed to stop session: {response.text}")
        
        # Step 5: Verify the track section was created
        print("\n🔍 Step 5: Verifying track section creation...")
        response = requests.get(f"{BASE_URL}/api/tracks")
        if response.status_code == 200:
            tracks = response.json()
            print(f"✅ Found {tracks['count']} track(s) in the system")
            
            # Look for the newly created track
            for track in tracks['tracks']:
                if "real time recorded data" in track.get('filename', '').lower():
                    print(f"🛤️ Found real-time recorded track:")
                    print(f"   Track ID: {track['track_id']}")
                    print(f"   Name: {track['name']}")
                    print(f"   Filename: {track['filename']}")
                    print(f"   Points: {track['points_count']}")
                    print(f"   Route: {track.get('start_station', 'N/A')} → {track.get('end_station', 'N/A')}")
                    
                    # Get the coordinates to verify they contain only lat/lon
                    coord_response = requests.get(f"{BASE_URL}/api/tracks/{track['track_id']}/coordinates")
                    if coord_response.status_code == 200:
                        track_data = coord_response.json()
                        coordinates = track_data['track']['coordinates']
                        print(f"   Coordinates: {len(coordinates)} points")
                        if coordinates:
                            sample_coord = coordinates[0]
                            print(f"   Sample coordinate: {sample_coord}")
                            # Verify only lat/lon are stored
                            if set(sample_coord.keys()) == {'latitude', 'longitude'}:
                                print("✅ Coordinates contain only latitude and longitude as requested")
                            else:
                                print(f"⚠️ Coordinates contain extra fields: {list(sample_coord.keys())}")
                    break
        else:
            print(f"❌ Failed to fetch tracks: {response.text}")
        
        print("\n🎉 Test completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    test_session_track_creation()
