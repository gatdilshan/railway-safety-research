#!/usr/bin/env python3
"""
Test script to demonstrate CSV upload functionality
"""

import requests
import json

def test_csv_upload():
    """Test uploading the CSV file"""
    
    # Read the CSV file
    with open('actual train line 1 data.csv', 'r') as f:
        csv_content = f.read()
    
    # Prepare the upload data
    upload_data = {
        "file_content": csv_content,
        "filename": "actual train line 1 data.csv",
        "name": "Panadura to Kalutara Track",
        "start_station": "Panadura",
        "end_station": "Kalutara"
    }
    
    try:
        # Make the upload request
        response = requests.post(
            "http://localhost:8000/api/tracks/upload",
            json=upload_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Upload successful!")
            print(f"   Track ID: {result['track']['track_id']}")
            print(f"   Points: {result['track']['points_count']}")
            print(f"   Active: {result['track']['is_active']}")
        else:
            print(f"❌ Upload failed: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_csv_upload()
