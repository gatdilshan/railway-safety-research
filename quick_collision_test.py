#!/usr/bin/env python3
"""
Quick Collision Test
====================
"""

import requests
import time

def test_collision():
    print("🔍 Testing GPS Matching Logic")
    print("=" * 35)

    # Reset system
    requests.post('http://localhost:8000/api/tracks/reset', timeout=10)

    # Create session
    session_data = {'start_point': 'Test A', 'end_point': 'Test B'}
    r = requests.post('http://localhost:8000/api/sessions', json=session_data, timeout=10)
    session_id = r.json()['data']['id']
    requests.post(f'http://localhost:8000/api/sessions/{session_id}/start', timeout=10)

    print("1. Simulating Train 1 with more consecutive points...")
    # Send more consecutive points for Train 1
    for i in range(10):
        gps1 = {
            'device_id': 'ESP32_GPS_01', 
            'track_id': 'track_02', 
            'start_index': i, 
            'num_points': 1
        }
        r = requests.post('http://localhost:8000/api/simulate/gps', json=gps1, timeout=10)
        print(f"   Point {i+1}: {r.status_code}")
        time.sleep(0.5)

    print("2. Checking Train 1 status...")
    r = requests.get('http://localhost:8000/api/train/status?device_id=ESP32_GPS_01', timeout=10)
    if r.status_code == 200:
        data = r.json()
        print(f"   Active: {data.get('active', False)}")
        print(f"   Track: {data.get('current_track', 'None')}")
        print(f"   Collision: {data.get('collision_detected', False)}")

    print("3. Simulating Train 2 with overlapping points...")
    # Send overlapping points for Train 2
    for i in range(8, 18):  # Overlapping with Train 1
        gps2 = {
            'device_id': 'ESP32_GPS_02', 
            'track_id': 'track_02', 
            'start_index': i, 
            'num_points': 1
        }
        r = requests.post('http://localhost:8000/api/simulate/gps', json=gps2, timeout=10)
        print(f"   Point {i-7}: {r.status_code}")
        time.sleep(0.5)

    time.sleep(2)

    print("4. Final collision check...")
    r1 = requests.get('http://localhost:8000/api/train/status?device_id=ESP32_GPS_01', timeout=10)
    r2 = requests.get('http://localhost:8000/api/train/status?device_id=ESP32_GPS_02', timeout=10)

    if r1.status_code == 200 and r2.status_code == 200:
        data1 = r1.json()
        data2 = r2.json()
        
        print(f"   Train 1: Active={data1.get('active', False)}, Collision={data1.get('collision_detected', False)}")
        print(f"   Train 2: Active={data2.get('active', False)}, Collision={data2.get('collision_detected', False)}")
        
        if data1.get('collision_detected', False) and data2.get('collision_detected', False):
            print("   🚨 COLLISION DETECTED!")
            print("   🔊 BUZZER SYSTEM WORKING!")
            return True
        else:
            print("   ⚠️ Still no collision detected")
            print("   ℹ️ Check GPS matching parameters in server.py")
            return False
    else:
        print(f"   ❌ Status check failed: {r1.status_code}, {r2.status_code}")
        return False

if __name__ == "__main__":
    test_collision()
