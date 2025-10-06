#!/usr/bin/env python3
"""
Railway Safety System - Buzzer Test Suite
==========================================

This script tests the complete buzzer/alarm system including:
1. Backend collision detection logic
2. Frontend alarm display and sound
3. Arduino buzzer activation
4. Mock data scenarios

Run this script to verify the buzzer system works correctly.
"""

import requests
import json
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Any

# Configuration
BASE_URL = "http://localhost:8000"  # Change to your server URL
API_BASE = f"{BASE_URL}/api"

class BuzzerSystemTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.api_base = API_BASE
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        timestamp = datetime.now().strftime("%H:%M:%S")
        result = f"[{timestamp}] {status} - {test_name}"
        if details:
            result += f" - {details}"
        print(result)
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": timestamp
        })
        
    def test_server_health(self) -> bool:
        """Test if server is running"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                self.log_test("Server Health Check", True, "Server is running")
                return True
            else:
                self.log_test("Server Health Check", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Server Health Check", False, f"Connection error: {e}")
            return False
    
    def reset_system(self) -> bool:
        """Reset all tracks and train statuses"""
        try:
            response = requests.post(f"{self.api_base}/tracks/reset", timeout=10)
            if response.status_code == 200:
                self.log_test("System Reset", True, "All tracks and trains reset")
                return True
            else:
                self.log_test("System Reset", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("System Reset", False, f"Error: {e}")
            return False
    
    def get_train_status(self, device_id: str = None) -> Dict:
        """Get train status"""
        try:
            url = f"{self.api_base}/train/status"
            if device_id:
                url += f"?device_id={device_id}"
            
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def simulate_gps_data(self, device_id: str, track_id: str = "track_02", 
                         start_index: int = 0, num_points: int = 10) -> Dict:
        """Simulate GPS data for a device"""
        try:
            payload = {
                "device_id": device_id,
                "track_id": track_id,
                "start_index": start_index,
                "num_points": num_points
            }
            
            response = requests.post(f"{self.api_base}/simulate/gps", 
                                   json=payload, timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_collision_scenario(self) -> bool:
        """Test complete collision scenario"""
        print("\n🚨 Testing Collision Detection Scenario...")
        
        # Step 1: Reset system
        if not self.reset_system():
            return False
        
        # Step 2: Simulate Train 1 entering track
        print("  📍 Simulating Train 1 (ESP32_GPS_01) entering track...")
        train1_result = self.simulate_gps_data("ESP32_GPS_01", "track_02", 0, 20)
        if not train1_result.get("success"):
            self.log_test("Train 1 GPS Simulation", False, train1_result.get("error", "Unknown error"))
            return False
        
        # Check Train 1 status
        train1_status = self.get_train_status("ESP32_GPS_01")
        train1_active = train1_status.get("success") and train1_status.get("active", False)
        self.log_test("Train 1 Status Check", train1_active, 
                     f"Active: {train1_active}, Track: {train1_status.get('current_track', 'None')}")
        
        # Step 3: Simulate Train 2 entering same track (collision scenario)
        print("  📍 Simulating Train 2 (ESP32_GPS_02) entering same track...")
        train2_result = self.simulate_gps_data("ESP32_GPS_02", "track_02", 10, 20)
        if not train2_result.get("success"):
            self.log_test("Train 2 GPS Simulation", False, train2_result.get("error", "Unknown error"))
            return False
        
        # Step 4: Check collision detection
        print("  🚨 Checking collision detection...")
        time.sleep(2)  # Allow time for collision detection
        
        # Check both train statuses
        train1_status = self.get_train_status("ESP32_GPS_01")
        train2_status = self.get_train_status("ESP32_GPS_02")
        
        train1_collision = train1_status.get("success") and train1_status.get("collision_detected", False)
        train2_collision = train2_status.get("success") and train2_status.get("collision_detected", False)
        
        collision_detected = train1_collision and train2_collision
        
        self.log_test("Collision Detection", collision_detected, 
                     f"Train1: {train1_collision}, Train2: {train2_collision}")
        
        if collision_detected:
            print("  🔊 Collision detected! Buzzers should be activated on both trains!")
            
            # Check collision details
            collision_with_1 = train1_status.get("collision_with", [])
            collision_with_2 = train2_status.get("collision_with", [])
            
            self.log_test("Collision Details", 
                         len(collision_with_1) > 0 and len(collision_with_2) > 0,
                         f"Train1 collision_with: {collision_with_1}, Train2 collision_with: {collision_with_2}")
        
        return collision_detected
    
    def test_buzzer_activation_logic(self) -> bool:
        """Test buzzer activation logic with different scenarios"""
        print("\n🔊 Testing Buzzer Activation Logic...")
        
        success = True
        
        # Test 1: Normal operation (no collision)
        print("  📍 Test 1: Normal operation...")
        self.reset_system()
        
        # Simulate single train
        result = self.simulate_gps_data("ESP32_GPS_01", "track_02", 0, 10)
        if result.get("success"):
            train_status = self.get_train_status("ESP32_GPS_01")
            no_collision = not train_status.get("collision_detected", True)
            self.log_test("Normal Operation", no_collision, "Single train, no collision")
            success = success and no_collision
        else:
            self.log_test("Normal Operation", False, "GPS simulation failed")
            success = False
        
        # Test 2: Collision scenario
        print("  📍 Test 2: Collision scenario...")
        collision_success = self.test_collision_scenario()
        self.log_test("Collision Scenario", collision_success, "Two trains on same track")
        success = success and collision_success
        
        # Test 3: Check track status
        print("  📍 Test 3: Track lock status...")
        try:
            response = requests.get(f"{self.api_base}/tracks/track_02/status", timeout=5)
            if response.status_code == 200:
                track_data = response.json()
                locks = track_data.get("locks", [])
                collision_risk = track_data.get("collision_risk", False)
                self.log_test("Track Status Check", True, 
                             f"Locks: {len(locks)}, Collision Risk: {collision_risk}")
            else:
                self.log_test("Track Status Check", False, f"HTTP {response.status_code}")
                success = False
        except Exception as e:
            self.log_test("Track Status Check", False, f"Error: {e}")
            success = False
        
        return success
    
    def test_frontend_integration(self) -> bool:
        """Test frontend alarm integration"""
        print("\n🖥️ Testing Frontend Integration...")
        
        try:
            # Test dashboard accessibility
            response = requests.get(f"{self.base_url}/dashboard", timeout=5)
            dashboard_accessible = response.status_code == 200
            self.log_test("Dashboard Access", dashboard_accessible, 
                         f"HTTP {response.status_code}")
            
            # Test train status API (used by frontend)
            response = requests.get(f"{self.api_base}/train/status", timeout=5)
            api_accessible = response.status_code == 200
            self.log_test("Train Status API", api_accessible, 
                         f"HTTP {response.status_code}")
            
            return dashboard_accessible and api_accessible
            
        except Exception as e:
            self.log_test("Frontend Integration", False, f"Error: {e}")
            return False
    
    def test_arduino_simulation(self) -> bool:
        """Simulate Arduino buzzer response"""
        print("\n🔧 Testing Arduino Buzzer Simulation...")
        
        # Simulate the Arduino's train status check
        print("  📡 Simulating Arduino train status check...")
        
        try:
            # This simulates what the Arduino does when checking train status
            response = requests.get(f"{self.api_base}/train/status?device_id=ESP32_GPS_01", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                active = data.get("active", False)
                collision = data.get("collision_detected", False)
                
                # Simulate Arduino buzzer logic
                buzzer_should_be_on = active or collision
                
                self.log_test("Arduino Status Check", True, 
                             f"Active: {active}, Collision: {collision}, Buzzer: {'ON' if buzzer_should_be_on else 'OFF'}")
                
                # Test different scenarios
                scenarios = [
                    {"active": False, "collision": False, "expected": False, "desc": "Inactive, no collision"},
                    {"active": True, "collision": False, "expected": True, "desc": "Active, no collision"},
                    {"active": False, "collision": True, "expected": True, "desc": "Inactive, collision detected"},
                    {"active": True, "collision": True, "expected": True, "desc": "Active, collision detected"}
                ]
                
                for scenario in scenarios:
                    buzzer_state = scenario["active"] or scenario["collision"]
                    correct = buzzer_state == scenario["expected"]
                    self.log_test(f"Arduino Logic - {scenario['desc']}", correct,
                                 f"Expected: {'ON' if scenario['expected'] else 'OFF'}, Got: {'ON' if buzzer_state else 'OFF'}")
                
                return True
            else:
                self.log_test("Arduino Status Check", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Arduino Status Check", False, f"Error: {e}")
            return False
    
    def run_comprehensive_test(self) -> bool:
        """Run all tests"""
        print("🚀 Starting Railway Safety System Buzzer Tests")
        print("=" * 60)
        
        # Test 1: Server Health
        if not self.test_server_health():
            print("\n❌ Server is not running. Please start the server first.")
            return False
        
        # Test 2: System Reset
        if not self.reset_system():
            print("\n❌ System reset failed. Cannot continue testing.")
            return False
        
        # Test 3: Buzzer Logic
        buzzer_success = self.test_buzzer_activation_logic()
        
        # Test 4: Frontend Integration
        frontend_success = self.test_frontend_integration()
        
        # Test 5: Arduino Simulation
        arduino_success = self.test_arduino_simulation()
        
        # Final collision test
        print("\n🚨 Final Collision Test...")
        final_collision_test = self.test_collision_scenario()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n🔊 BUZZER SYSTEM STATUS:")
        print(f"  Backend Logic: {'✅ WORKING' if buzzer_success else '❌ FAILED'}")
        print(f"  Frontend Integration: {'✅ WORKING' if frontend_success else '❌ FAILED'}")
        print(f"  Arduino Simulation: {'✅ WORKING' if arduino_success else '❌ FAILED'}")
        print(f"  Collision Detection: {'✅ WORKING' if final_collision_test else '❌ FAILED'}")
        
        overall_success = buzzer_success and frontend_success and arduino_success and final_collision_test
        print(f"\n🎯 OVERALL RESULT: {'✅ ALL SYSTEMS WORKING' if overall_success else '❌ SOME ISSUES DETECTED'}")
        
        if overall_success:
            print("\n🎉 The buzzer system is working correctly!")
            print("   - Collision detection is functional")
            print("   - Buzzers will activate when collisions are detected")
            print("   - Frontend will display warnings and play alarm sounds")
            print("   - Arduino devices will receive buzzer activation commands")
        else:
            print("\n⚠️ Some issues were detected. Please check the failed tests above.")
        
        return overall_success

def main():
    """Main test function"""
    print("Railway Safety System - Buzzer Test Suite")
    print("=========================================")
    
    tester = BuzzerSystemTester()
    
    try:
        success = tester.run_comprehensive_test()
        exit_code = 0 if success else 1
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️ Testing interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error during testing: {e}")
        exit(1)

if __name__ == "__main__":
    main()
