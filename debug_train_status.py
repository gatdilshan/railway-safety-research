#!/usr/bin/env python3
"""
Debug Train Status API
======================
"""

import requests
import json

def debug_train_status():
    print("🔍 Debugging Train Status API")
    print("=" * 40)
    
    # Test the train status API
    url = "https://73fb8402061f.ngrok-free.app/api/train/status?device_id=ESP32_GPS_01"
    
    try:
        print(f"📡 Testing URL: {url}")
        response = requests.get(url, timeout=10)
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📄 Response Headers: {dict(response.headers)}")
        print(f"📝 Response Body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n🔍 Parsed JSON:")
            print(f"   success: {data.get('success')}")
            print(f"   train_id: {data.get('train_id')}")
            print(f"   device_id: {data.get('device_id')}")
            print(f"   active: {data.get('active')}")
            print(f"   collision_detected: {data.get('collision_detected')}")
            print(f"   current_track: {data.get('current_track')}")
            print(f"   collision_with: {data.get('collision_with')}")
            
            # Check what Arduino should see
            active = data.get('active', False)
            collision = data.get('collision_detected', False)
            buzzer_should_be_on = active or collision
            
            print(f"\n🔊 Arduino Logic:")
            print(f"   active: {active}")
            print(f"   collision_detected: {collision}")
            print(f"   trainActive = active || collision = {buzzer_should_be_on}")
            print(f"   Buzzer should be: {'ON' if buzzer_should_be_on else 'OFF'}")
            
            if not buzzer_should_be_on:
                print("\n❌ PROBLEM IDENTIFIED:")
                print("   The API is returning active=False and collision_detected=False")
                print("   Even though you manually set them to true in the database")
                print("   This suggests the database update didn't work or the API is reading from wrong collection")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

def test_all_trains():
    print("\n🔍 Testing All Trains API")
    print("=" * 40)
    
    url = "https://73fb8402061f.ngrok-free.app/api/train/status"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📝 Response: {json.dumps(data, indent=2)}")
            
            if data.get('success') and data.get('trains'):
                for train in data['trains']:
                    print(f"\n🚂 Train: {train.get('train_id')}")
                    print(f"   device_id: {train.get('device_id')}")
                    print(f"   active: {train.get('active')}")
                    print(f"   collision_detected: {train.get('collision_detected')}")
                    print(f"   current_track: {train.get('current_track')}")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    debug_train_status()
    test_all_trains()
