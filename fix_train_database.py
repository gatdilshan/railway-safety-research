#!/usr/bin/env python3
"""
Fix Train Database
==================
This script fixes the train database by adding missing device_id fields
"""

from pymongo import MongoClient
from datetime import datetime

# MongoDB connection
MONGODB_URI = "mongodb+srv://oshen:oshen@cluster0.h2my8yk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "gps_tracker"
TRAIN_DETAILS_COLLECTION = "train_details"

def fix_train_database():
    print("🔧 Fixing Train Database")
    print("=" * 30)
    
    try:
        # Connect to MongoDB
        client = MongoClient(MONGODB_URI)
        db = client[DATABASE_NAME]
        train_collection = db[TRAIN_DETAILS_COLLECTION]
        
        print("✅ Connected to MongoDB")
        
        # Check current train documents
        trains = list(train_collection.find())
        print(f"📊 Found {len(trains)} train documents")
        
        for train in trains:
            print(f"\n🚂 Train: {train.get('train_id')}")
            print(f"   Current device_id: {train.get('device_id')}")
            print(f"   Current active: {train.get('active')}")
            print(f"   Current collision_detected: {train.get('collision_detected')}")
            
            # Fix missing device_id
            if not train.get('device_id'):
                device_id = None
                if train.get('train_id') == 'TRAIN_01':
                    device_id = 'ESP32_GPS_01'
                elif train.get('train_id') == 'TRAIN_02':
                    device_id = 'ESP32_GPS_02'
                
                if device_id:
                    # Update the document
                    result = train_collection.update_one(
                        {"_id": train["_id"]},
                        {
                            "$set": {
                                "device_id": device_id,
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    
                    if result.modified_count > 0:
                        print(f"   ✅ Added device_id: {device_id}")
                    else:
                        print(f"   ❌ Failed to update device_id")
                else:
                    print(f"   ⚠️ Unknown train_id, cannot assign device_id")
        
        # Verify the fix
        print(f"\n🔍 Verifying fix...")
        trains = list(train_collection.find())
        for train in trains:
            print(f"🚂 {train.get('train_id')}: device_id={train.get('device_id')}, active={train.get('active')}, collision_detected={train.get('collision_detected')}")
        
        # Now manually set active and collision_detected to true for testing
        print(f"\n🔧 Setting active=true and collision_detected=true for TRAIN_01...")
        result = train_collection.update_one(
            {"train_id": "TRAIN_01"},
            {
                "$set": {
                    "active": True,
                    "collision_detected": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            print("✅ Successfully updated TRAIN_01 status")
        else:
            print("❌ Failed to update TRAIN_01 status")
        
        # Final verification
        print(f"\n🔍 Final verification...")
        train = train_collection.find_one({"train_id": "TRAIN_01"})
        if train:
            print(f"🚂 TRAIN_01:")
            print(f"   device_id: {train.get('device_id')}")
            print(f"   active: {train.get('active')}")
            print(f"   collision_detected: {train.get('collision_detected')}")
            print(f"   updated_at: {train.get('updated_at')}")
            
            # Test Arduino logic
            active = train.get('active', False)
            collision = train.get('collision_detected', False)
            buzzer_should_be_on = active or collision
            print(f"\n🔊 Arduino Logic Test:")
            print(f"   active: {active}")
            print(f"   collision_detected: {collision}")
            print(f"   trainActive = active || collision = {buzzer_should_be_on}")
            print(f"   Buzzer should be: {'ON' if buzzer_should_be_on else 'OFF'}")
            
            if buzzer_should_be_on:
                print("✅ BUZZER SHOULD NOW BE ACTIVATED!")
            else:
                print("❌ Buzzer will still be OFF")
        
        client.close()
        print("\n✅ Database fix completed")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_train_database()
