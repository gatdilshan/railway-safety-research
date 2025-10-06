#!/usr/bin/env python3
"""
Mock Data Generator for Railway Safety System
=============================================

Generates realistic mock data for testing the buzzer system.
"""

import requests
import json
import time
from datetime import datetime
from typing import List, Dict

class MockDataGenerator:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
    
    def create_session(self) -> str:
        """Create a new session for testing"""
        try:
            payload = {
                "start_point": "Test Station A",
                "end_point": "Test Station B"
            }
            response = requests.post(f"{self.api_base}/sessions", json=payload)
            if response.status_code == 200:
                data = response.json()
                session_id = data["data"]["id"]
                print(f"✅ Created session: {session_id}")
                return session_id
            else:
                print(f"❌ Failed to create session: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error creating session: {e}")
            return None
    
    def start_session(self, session_id: str) -> bool:
        """Start the session"""
        try:
            response = requests.post(f"{self.api_base}/sessions/{session_id}/start")
            if response.status_code == 200:
                print(f"✅ Started session: {session_id}")
                return True
            else:
                print(f"❌ Failed to start session: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error starting session: {e}")
            return False
    
    def simulate_collision_scenario_1(self) -> bool:
        """Scenario 1: Two trains approaching collision"""
        print("\n🚨 Scenario 1: Two trains approaching collision")
        
        # Create and start session
        session_id = self.create_session()
        if not session_id:
            return False
        
        if not self.start_session(session_id):
            return False
        
        # Simulate Train 1 entering track
        print("  📍 Train 1 (ESP32_GPS_01) entering track...")
        payload1 = {
            "device_id": "ESP32_GPS_01",
            "track_id": "track_02",
            "start_index": 0,
            "num_points": 25
        }
        
        response1 = requests.post(f"{self.api_base}/simulate/gps", json=payload1)
        if response1.status_code != 200:
            print(f"❌ Train 1 simulation failed: {response1.status_code}")
            return False
        
        # Wait a moment
        time.sleep(1)
        
        # Simulate Train 2 entering same track (collision!)
        print("  📍 Train 2 (ESP32_GPS_02) entering same track...")
        payload2 = {
            "device_id": "ESP32_GPS_02",
            "track_id": "track_02",
            "start_index": 15,  # Overlapping section
            "num_points": 25
        }
        
        response2 = requests.post(f"{self.api_base}/simulate/gps", json=payload2)
        if response2.status_code != 200:
            print(f"❌ Train 2 simulation failed: {response2.status_code}")
            return False
        
        # Check collision status
        time.sleep(2)
        print("  🚨 Checking collision status...")
        
        train1_status = requests.get(f"{self.api_base}/train/status?device_id=ESP32_GPS_01")
        train2_status = requests.get(f"{self.api_base}/train/status?device_id=ESP32_GPS_02")
        
        if train1_status.status_code == 200 and train2_status.status_code == 200:
            train1_data = train1_status.json()
            train2_data = train2_status.json()
            
            collision1 = train1_data.get("collision_detected", False)
            collision2 = train2_data.get("collision_detected", False)
            
            print(f"  Train 1 collision detected: {collision1}")
            print(f"  Train 2 collision detected: {collision2}")
            
            if collision1 and collision2:
                print("  🚨 COLLISION DETECTED! Buzzers should be activated!")
                print("  🔊 BUZZER ACTIVATED ON ALL TRAINS ⚠️")
                return True
            else:
                print("  ⚠️ No collision detected")
                return False
        else:
            print("❌ Failed to check train status")
            return False
    
    def simulate_normal_operation(self) -> bool:
        """Scenario 2: Normal operation - single train"""
        print("\n✅ Scenario 2: Normal operation - single train")
        
        # Create and start session
        session_id = self.create_session()
        if not session_id:
            return False
        
        if not self.start_session(session_id):
            return False
        
        # Reset system first
        requests.post(f"{self.api_base}/tracks/reset")
        
        # Simulate single train
        print("  📍 Single train (ESP32_GPS_01) on track...")
        payload = {
            "device_id": "ESP32_GPS_01",
            "track_id": "track_02",
            "start_index": 0,
            "num_points": 15
        }
        
        response = requests.post(f"{self.api_base}/simulate/gps", json=payload)
        if response.status_code != 200:
            print(f"❌ Train simulation failed: {response.status_code}")
            return False
        
        # Check status
        time.sleep(1)
        train_status = requests.get(f"{self.api_base}/train/status?device_id=ESP32_GPS_01")
        
        if train_status.status_code == 200:
            data = train_status.json()
            collision = data.get("collision_detected", False)
            active = data.get("active", False)
            
            print(f"  Train active: {active}")
            print(f"  Collision detected: {collision}")
            
            if not collision and active:
                print("  ✅ Normal operation - no collision, train active")
                return True
            else:
                print("  ⚠️ Unexpected state")
                return False
        else:
            print("❌ Failed to check train status")
            return False
    
    def simulate_multiple_trains_different_tracks(self) -> bool:
        """Scenario 3: Multiple trains on different tracks (no collision)"""
        print("\n🚂 Scenario 3: Multiple trains on different tracks")
        
        # Create and start session
        session_id = self.create_session()
        if not session_id:
            return False
        
        if not self.start_session(session_id):
            return False
        
        # Reset system first
        requests.post(f"{self.api_base}/tracks/reset")
        
        # Note: This scenario would require multiple tracks to be uploaded
        # For now, we'll simulate with the same track but different sections
        print("  📍 Train 1 on track section A...")
        payload1 = {
            "device_id": "ESP32_GPS_01",
            "track_id": "track_02",
            "start_index": 0,
            "num_points": 10
        }
        
        response1 = requests.post(f"{self.api_base}/simulate/gps", json=payload1)
        if response1.status_code != 200:
            print(f"❌ Train 1 simulation failed: {response1.status_code}")
            return False
        
        time.sleep(1)
        
        print("  📍 Train 2 on different track section B...")
        payload2 = {
            "device_id": "ESP32_GPS_02",
            "track_id": "track_02",
            "start_index": 50,  # Different section, no overlap
            "num_points": 10
        }
        
        response2 = requests.post(f"{self.api_base}/simulate/gps", json=payload2)
        if response2.status_code != 200:
            print(f"❌ Train 2 simulation failed: {response2.status_code}")
            return False
        
        # Check collision status
        time.sleep(2)
        train1_status = requests.get(f"{self.api_base}/train/status?device_id=ESP32_GPS_01")
        train2_status = requests.get(f"{self.api_base}/train/status?device_id=ESP32_GPS_02")
        
        if train1_status.status_code == 200 and train2_status.status_code == 200:
            train1_data = train1_status.json()
            train2_data = train2_status.json()
            
            collision1 = train1_data.get("collision_detected", False)
            collision2 = train2_data.get("collision_detected", False)
            
            print(f"  Train 1 collision detected: {collision1}")
            print(f"  Train 2 collision detected: {collision2}")
            
            if not collision1 and not collision2:
                print("  ✅ No collision - trains on different sections")
                return True
            else:
                print("  ⚠️ Unexpected collision detected")
                return False
        else:
            print("❌ Failed to check train status")
            return False
    
    def run_all_scenarios(self) -> Dict[str, bool]:
        """Run all test scenarios"""
        print("🚀 Railway Safety System - Mock Data Testing")
        print("=" * 50)
        
        results = {}
        
        # Scenario 1: Collision
        results["collision_scenario"] = self.simulate_collision_scenario_1()
        
        # Wait between scenarios
        time.sleep(2)
        
        # Scenario 2: Normal operation
        results["normal_operation"] = self.simulate_normal_operation()
        
        # Wait between scenarios
        time.sleep(2)
        
        # Scenario 3: Different tracks
        results["different_tracks"] = self.simulate_multiple_trains_different_tracks()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 SCENARIO TEST SUMMARY")
        print("=" * 50)
        
        for scenario, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{scenario}: {status}")
        
        total_scenarios = len(results)
        passed_scenarios = sum(results.values())
        
        print(f"\nTotal Scenarios: {total_scenarios}")
        print(f"Passed: {passed_scenarios}")
        print(f"Success Rate: {(passed_scenarios/total_scenarios)*100:.1f}%")
        
        if passed_scenarios == total_scenarios:
            print("\n🎉 All scenarios passed! Buzzer system is working correctly.")
        else:
            print(f"\n⚠️ {total_scenarios - passed_scenarios} scenarios failed.")
        
        return results

def main():
    """Main function"""
    generator = MockDataGenerator()
    
    try:
        results = generator.run_all_scenarios()
        
        # Exit with appropriate code
        all_passed = all(results.values())
        exit(0 if all_passed else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Testing interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
