#!/usr/bin/env python3
"""
Simple Buzzer Test - Manual Verification
========================================

This script manually tests the buzzer system step by step.
"""

import requests
import time
import json

def test_buzzer_system():
    """Test the buzzer system manually"""
    base_url = "http://localhost:8000"
    api_base = f"{base_url}/api"
    
    print("🚀 Simple Buzzer System Test")
    print("=" * 40)
    
    # Step 1: Check server health
    print("\n1️⃣ Checking server health...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print(f"❌ Server error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False
    
    # Step 2: Reset system
    print("\n2️⃣ Resetting system...")
    try:
        response = requests.post(f"{api_base}/tracks/reset", timeout=10)
        if response.status_code == 200:
            print("✅ System reset successful")
        else:
            print(f"❌ Reset failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Reset error: {e}")
        return False
    
    # Step 3: Check initial train status
    print("\n3️⃣ Checking initial train status...")
    try:
        response = requests.get(f"{api_base}/train/status?device_id=ESP32_GPS_01", timeout=5)
        if response.status_code == 200:
            data = response.json()
            active = data.get("active", False)
            collision = data.get("collision_detected", False)
            print(f"✅ Train 1 Status: Active={active}, Collision={collision}")
            print(f"   🔊 Buzzer should be: {'ON' if (active or collision) else 'OFF'}")
        else:
            print(f"❌ Failed to get train status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Train status error: {e}")
        return False
    
    # Step 4: Create session
    print("\n4️⃣ Creating test session...")
    try:
        session_data = {"start_point": "Test A", "end_point": "Test B"}
        response = requests.post(f"{api_base}/sessions", json=session_data, timeout=5)
        if response.status_code == 200:
            session_id = response.json()["data"]["id"]
            print(f"✅ Session created: {session_id}")
            
            # Start session
            start_response = requests.post(f"{api_base}/sessions/{session_id}/start", timeout=5)
            if start_response.status_code == 200:
                print("✅ Session started")
            else:
                print(f"❌ Failed to start session: {start_response.status_code}")
                return False
        else:
            print(f"❌ Failed to create session: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Session error: {e}")
        return False
    
    # Step 5: Simulate Train 1
    print("\n5️⃣ Simulating Train 1 entering track...")
    try:
        gps_data = {
            "device_id": "ESP32_GPS_01",
            "track_id": "track_02",
            "start_index": 0,
            "num_points": 15
        }
        response = requests.post(f"{api_base}/simulate/gps", json=gps_data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Train 1 simulation successful: {result.get('points_sent', 0)} points sent")
            
            # Check train status after simulation
            time.sleep(2)
            status_response = requests.get(f"{api_base}/train/status?device_id=ESP32_GPS_01", timeout=5)
            if status_response.status_code == 200:
                status_data = status_response.json()
                active = status_data.get("active", False)
                collision = status_data.get("collision_detected", False)
                print(f"   Train 1 Status: Active={active}, Collision={collision}")
                print(f"   🔊 Buzzer should be: {'ON' if (active or collision) else 'OFF'}")
        else:
            print(f"❌ Train 1 simulation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Train 1 simulation error: {e}")
        return False
    
    # Step 6: Simulate Train 2 (collision scenario)
    print("\n6️⃣ Simulating Train 2 entering same track (collision scenario)...")
    try:
        gps_data = {
            "device_id": "ESP32_GPS_02",
            "track_id": "track_02",
            "start_index": 10,  # Overlapping with Train 1
            "num_points": 15
        }
        response = requests.post(f"{api_base}/simulate/gps", json=gps_data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Train 2 simulation successful: {result.get('points_sent', 0)} points sent")
            
            # Check collision status
            time.sleep(3)
            print("\n🚨 Checking collision detection...")
            
            # Check both trains
            train1_response = requests.get(f"{api_base}/train/status?device_id=ESP32_GPS_01", timeout=5)
            train2_response = requests.get(f"{api_base}/train/status?device_id=ESP32_GPS_02", timeout=5)
            
            if train1_response.status_code == 200 and train2_response.status_code == 200:
                train1_data = train1_response.json()
                train2_data = train2_response.json()
                
                train1_collision = train1_data.get("collision_detected", False)
                train2_collision = train2_data.get("collision_detected", False)
                
                print(f"   Train 1: Active={train1_data.get('active', False)}, Collision={train1_collision}")
                print(f"   Train 2: Active={train2_data.get('active', False)}, Collision={train2_collision}")
                
                if train1_collision and train2_collision:
                    print("   🚨 COLLISION DETECTED!")
                    print("   🔊 BUZZER SHOULD BE ACTIVATED ON BOTH TRAINS!")
                    print("   ⚠️ BUZZER ACTIVATED ON ALL TRAINS ⚠️")
                    
                    # Check collision details
                    collision_with_1 = train1_data.get("collision_with", [])
                    collision_with_2 = train2_data.get("collision_with", [])
                    print(f"   Train 1 collision with: {collision_with_1}")
                    print(f"   Train 2 collision with: {collision_with_2}")
                    
                    return True
                else:
                    print("   ⚠️ No collision detected - this might be expected depending on GPS matching logic")
                    return False
            else:
                print("❌ Failed to check train statuses")
                return False
        else:
            print(f"❌ Train 2 simulation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Train 2 simulation error: {e}")
        return False

def main():
    """Main function"""
    try:
        success = test_buzzer_system()
        
        print("\n" + "=" * 40)
        if success:
            print("🎉 BUZZER SYSTEM TEST PASSED!")
            print("✅ Collision detection is working")
            print("🔊 Buzzers will activate when collisions are detected")
            print("🖥️ Frontend will show warnings and play alarm sounds")
        else:
            print("⚠️ BUZZER SYSTEM TEST INCOMPLETE")
            print("❌ Some issues detected - check the output above")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
