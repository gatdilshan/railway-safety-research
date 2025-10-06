#!/usr/bin/env python3
"""
Manual Buzzer Control
=====================
This script allows you to manually control the buzzer for testing
"""

from pymongo import MongoClient
from datetime import datetime
import time

# MongoDB connection
MONGODB_URI = "mongodb+srv://oshen:oshen@cluster0.h2my8yk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "gps_tracker"
TRAIN_DETAILS_COLLECTION = "train_details"

def control_buzzer(device_id, active=None, collision=None):
    """Control buzzer by updating train status"""
    try:
        client = MongoClient(MONGODB_URI)
        db = client[DATABASE_NAME]
        train_collection = db[TRAIN_DETAILS_COLLECTION]
        
        # Find the train
        train = train_collection.find_one({"device_id": device_id})
        if not train:
            print(f"❌ Train with device_id '{device_id}' not found")
            return False
        
        # Prepare update
        update_data = {"updated_at": datetime.utcnow()}
        if active is not None:
            update_data["active"] = active
        if collision is not None:
            update_data["collision_detected"] = collision
        
        # Update the train
        result = train_collection.update_one(
            {"device_id": device_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            # Get updated status
            updated_train = train_collection.find_one({"device_id": device_id})
            active_status = updated_train.get('active', False)
            collision_status = updated_train.get('collision_detected', False)
            buzzer_status = active_status or collision_status
            
            print(f"✅ Updated {device_id}:")
            print(f"   active: {active_status}")
            print(f"   collision_detected: {collision_status}")
            print(f"   🔊 Buzzer: {'ON' if buzzer_status else 'OFF'}")
            
            if buzzer_status:
                print("   🚨 BUZZER SHOULD BE ACTIVATED NOW!")
            
            return True
        else:
            print("❌ Failed to update train status")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        client.close()

def interactive_control():
    """Interactive buzzer control"""
    print("🎮 Interactive Buzzer Control")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Turn ON buzzer (active=true)")
        print("2. Turn OFF buzzer (active=false)")
        print("3. Simulate collision (collision=true)")
        print("4. Clear collision (collision=false)")
        print("5. Test both active and collision")
        print("6. Reset to normal (both false)")
        print("0. Exit")
        
        choice = input("\nEnter your choice (0-6): ").strip()
        
        if choice == "0":
            print("👋 Goodbye!")
            break
        elif choice == "1":
            control_buzzer("ESP32_GPS_01", active=True)
        elif choice == "2":
            control_buzzer("ESP32_GPS_01", active=False)
        elif choice == "3":
            control_buzzer("ESP32_GPS_01", collision=True)
        elif choice == "4":
            control_buzzer("ESP32_GPS_01", collision=False)
        elif choice == "5":
            control_buzzer("ESP32_GPS_01", active=True, collision=True)
            print("   🚨 COLLISION DETECTED! BUZZER ACTIVATED!")
        elif choice == "6":
            control_buzzer("ESP32_GPS_01", active=False, collision=False)
        else:
            print("❌ Invalid choice. Please try again.")

def quick_test():
    """Quick buzzer test sequence"""
    print("🚀 Quick Buzzer Test Sequence")
    print("=" * 35)
    
    device_id = "ESP32_GPS_01"
    
    print("1. Turning OFF buzzer...")
    control_buzzer(device_id, active=False, collision=False)
    time.sleep(2)
    
    print("\n2. Turning ON buzzer (active)...")
    control_buzzer(device_id, active=True, collision=False)
    time.sleep(3)
    
    print("\n3. Simulating collision...")
    control_buzzer(device_id, active=True, collision=True)
    time.sleep(3)
    
    print("\n4. Turning OFF buzzer...")
    control_buzzer(device_id, active=False, collision=False)
    
    print("\n✅ Test sequence completed!")
    print("🔊 Check your ESP32 - the buzzer should have been ON during steps 2 and 3")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            quick_test()
        elif sys.argv[1] == "on":
            control_buzzer("ESP32_GPS_01", active=True)
        elif sys.argv[1] == "off":
            control_buzzer("ESP32_GPS_01", active=False, collision=False)
        elif sys.argv[1] == "collision":
            control_buzzer("ESP32_GPS_01", active=True, collision=True)
        else:
            print("Usage: python manual_buzzer_control.py [test|on|off|collision]")
    else:
        interactive_control()
