#!/usr/bin/env python3
"""
Arduino Buzzer Test Script
==========================

This script simulates the Arduino's buzzer activation logic and tests
different scenarios to verify the buzzer system works correctly.
"""

import requests
import time
import json
from datetime import datetime

class ArduinoBuzzerTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        self.device_id = "ESP32_GPS_01"
    
    def simulate_arduino_status_check(self, expected_active: bool = False, 
                                    expected_collision: bool = False) -> bool:
        """Simulate Arduino checking train status (like in the Arduino code)"""
        print(f"  📡 Arduino checking train status for {self.device_id}...")
        
        try:
            # This simulates the Arduino's HTTP request to check train status
            url = f"{self.api_base}/train/status?device_id={self.device_id}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                active = data.get("active", False)
                collision = data.get("collision_detected", False)
                
                # Simulate Arduino buzzer logic: buzzer ON if active OR collision
                buzzer_on = active or collision
                
                print(f"    Server response: Active={active}, Collision={collision}")
                print(f"    Arduino logic: Buzzer={'ON' if buzzer_on else 'OFF'}")
                
                # Check if result matches expectations
                expected_buzzer = expected_active or expected_collision
                correct = buzzer_on == expected_buzzer
                
                if correct:
                    print(f"    ✅ Correct buzzer state: {'ON' if buzzer_on else 'OFF'}")
                else:
                    print(f"    ❌ Wrong buzzer state: Expected {'ON' if expected_buzzer else 'OFF'}, Got {'ON' if buzzer_on else 'OFF'}")
                
                return correct
                
            else:
                print(f"    ❌ HTTP Error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"    ❌ Connection Error: {e}")
            return False
    
    def test_scenario(self, scenario_name: str, setup_function, expected_active: bool, 
                     expected_collision: bool) -> bool:
        """Test a specific scenario"""
        print(f"\n🧪 Testing Scenario: {scenario_name}")
        print("-" * 40)
        
        # Setup the scenario
        if not setup_function():
            print("❌ Scenario setup failed")
            return False
        
        # Wait for system to process
        time.sleep(2)
        
        # Test Arduino status check
        success = self.simulate_arduino_status_check(expected_active, expected_collision)
        
        if success:
            print(f"✅ {scenario_name}: PASSED")
        else:
            print(f"❌ {scenario_name}: FAILED")
        
        return success
    
    def setup_normal_operation(self) -> bool:
        """Setup normal operation scenario"""
        # Reset system
        response = requests.post(f"{self.api_base}/tracks/reset")
        if response.status_code != 200:
            return False
        
        # Create and start session
        session_data = {"start_point": "Test A", "end_point": "Test B"}
        session_response = requests.post(f"{self.api_base}/sessions", json=session_data)
        if session_response.status_code != 200:
            return False
        
        session_id = session_response.json()["data"]["id"]
        requests.post(f"{self.api_base}/sessions/{session_id}/start")
        
        # Simulate single train
        gps_data = {
            "device_id": self.device_id,
            "track_id": "track_02",
            "start_index": 0,
            "num_points": 10
        }
        
        response = requests.post(f"{self.api_base}/simulate/gps", json=gps_data)
        return response.status_code == 200
    
    def setup_collision_scenario(self) -> bool:
        """Setup collision scenario"""
        # Reset system
        response = requests.post(f"{self.api_base}/tracks/reset")
        if response.status_code != 200:
            return False
        
        # Create and start session
        session_data = {"start_point": "Test A", "end_point": "Test B"}
        session_response = requests.post(f"{self.api_base}/sessions", json=session_data)
        if session_response.status_code != 200:
            return False
        
        session_id = session_response.json()["data"]["id"]
        requests.post(f"{self.api_base}/sessions/{session_id}/start")
        
        # Simulate Train 1
        gps_data1 = {
            "device_id": "ESP32_GPS_01",
            "track_id": "track_02",
            "start_index": 0,
            "num_points": 20
        }
        requests.post(f"{self.api_base}/simulate/gps", json=gps_data1)
        
        time.sleep(1)
        
        # Simulate Train 2 (collision)
        gps_data2 = {
            "device_id": "ESP32_GPS_02",
            "track_id": "track_02",
            "start_index": 10,  # Overlapping
            "num_points": 20
        }
        response = requests.post(f"{self.api_base}/simulate/gps", json=gps_data2)
        return response.status_code == 200
    
    def setup_inactive_train(self) -> bool:
        """Setup inactive train scenario"""
        # Just reset system - no active trains
        response = requests.post(f"{self.api_base}/tracks/reset")
        return response.status_code == 200
    
    def run_buzzer_tests(self) -> bool:
        """Run all buzzer tests"""
        print("🔊 Arduino Buzzer System Tests")
        print("=" * 40)
        
        # Test scenarios
        scenarios = [
            {
                "name": "Inactive Train",
                "setup": self.setup_inactive_train,
                "expected_active": False,
                "expected_collision": False
            },
            {
                "name": "Normal Operation",
                "setup": self.setup_normal_operation,
                "expected_active": True,
                "expected_collision": False
            },
            {
                "name": "Collision Detected",
                "setup": self.setup_collision_scenario,
                "expected_active": True,
                "expected_collision": True
            }
        ]
        
        results = []
        for scenario in scenarios:
            success = self.test_scenario(
                scenario["name"],
                scenario["setup"],
                scenario["expected_active"],
                scenario["expected_collision"]
            )
            results.append(success)
        
        # Summary
        print("\n" + "=" * 40)
        print("📊 BUZZER TEST SUMMARY")
        print("=" * 40)
        
        passed = sum(results)
        total = len(results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n🎉 All buzzer tests passed!")
            print("✅ Arduino buzzer logic is working correctly")
            print("🔊 Buzzers will activate appropriately:")
            print("   - OFF when train is inactive")
            print("   - ON when train is active (normal operation)")
            print("   - ON when collision is detected")
        else:
            print(f"\n⚠️ {total - passed} tests failed")
            print("❌ Arduino buzzer logic has issues")
        
        return passed == total

def main():
    """Main function"""
    print("Arduino Buzzer Test Suite")
    print("=========================")
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not running. Please start the server first.")
            return 1
    except:
        print("❌ Cannot connect to server. Please start the server first.")
        return 1
    
    tester = ArduinoBuzzerTester()
    
    try:
        success = tester.run_buzzer_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⏹️ Testing interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
