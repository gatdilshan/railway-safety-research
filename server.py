from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import uvicorn
import os
import csv
import math

app = FastAPI(title="GPS Tracker API")

# CORS middleware to allow requests from dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==== MongoDB Connection ====
MONGODB_URI = "mongodb+srv://oshen:oshen@cluster0.h2my8yk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "gps_tracker"
COLLECTION_NAME = "gpsdata"
TRAIN_DETAILS_COLLECTION = "train_details"
SESSIONS_COLLECTION = "sessions"
TRACK_SECTIONS_COLLECTION = "track_sections"
TRACK_LOCKS_COLLECTION = "track_locks"

client = None
db = None
collection = None
train_collection = None
sessions_collection = None
track_sections_collection = None
track_locks_collection = None

try:
    client = MongoClient(MONGODB_URI)
    # Test the connection
    client.admin.command('ping')
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]
    train_collection = db[TRAIN_DETAILS_COLLECTION]
    sessions_collection = db[SESSIONS_COLLECTION]
    track_sections_collection = db[TRACK_SECTIONS_COLLECTION]
    track_locks_collection = db[TRACK_LOCKS_COLLECTION]
    
    # Initialize train details for multiple trains
    if train_collection.count_documents({}) == 0:
        train_collection.insert_many([
            {
                "train_id": "TRAIN_01",
                "device_id": "ESP32_GPS_01",
                "active": False,
                "collision_detected": False,
                "current_track": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "train_id": "TRAIN_02",
                "device_id": "ESP32_GPS_02",
                "active": False,
                "collision_detected": False,
                "current_track": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ])
    
    print("✅ Connected to MongoDB")
    print("✅ Train details collection initialized")
    print("✅ Sessions collection initialized")
    print("✅ Track sections collection initialized")
    print("✅ Track locks collection initialized")
except Exception as e:
    print(f"❌ MongoDB connection error: {e}")
    # Optional: Exit the application if MongoDB connection fails
    # import sys
    # sys.exit(1)

# Add this function to check MongoDB connection
def check_mongodb():
    if not collection:
        raise HTTPException(
            status_code=500,
            detail="MongoDB connection is not available"
        )

# ==== Pydantic Models ====
class GPSData(BaseModel):
    latitude: float
    longitude: float
    satellites: int = 0
    hdop: float = 0.0
    accuracy: float = 0.0  # Kalman filter accuracy in meters
    timestamp: str
    device_id: str

class GPSDataResponse(GPSData):
    id: str
    received_at: datetime

    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

class TrainDetails(BaseModel):
    train_id: str = "TRAIN_01"
    active: bool

class TrainDetailsResponse(BaseModel):
    train_id: str
    active: bool
    updated_at: datetime

    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

class SessionCreate(BaseModel):
    start_point: str
    end_point: str

class Session(BaseModel):
    id: Optional[str] = None
    start_point: str
    end_point: str
    status: str  # "created", "active", "completed"
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    gps_count: int = 0

    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

class RealTestingStartRequest(BaseModel):
    train_id: str
    track_id: str

class RealTestingStopRequest(BaseModel):
    train_id: str
    track_id: Optional[str] = None

class TrackPoint(BaseModel):
    latitude: float
    longitude: float

class TrackSection(BaseModel):
    track_id: str
    name: str
    start_station: str
    end_station: str
    coordinates: List[TrackPoint]

class TrackUploadRequest(BaseModel):
    file_content: str
    filename: str
    name: str
    start_station: str = ""
    end_station: str = ""

# ==== GPS Matching Configuration ====
GPS_MATCH_THRESHOLD_METERS = 30.0  # Distance threshold to consider a point "matched"
REQUIRED_CONSECUTIVE_MATCHES = 5   # Number of consecutive matches needed to lock track
GPS_BUFFER_SIZE = 10              # Keep last N GPS points for matching

# ==== Helper Functions ====

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two GPS coordinates using Haversine formula
    Returns distance in meters
    """
    R = 6371000  # Earth's radius in meters
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    distance = R * c
    return distance

def find_closest_track_point(gps_lat: float, gps_lon: float, track_coords: List[Dict]) -> tuple:
    """
    Find the closest point in the track to the given GPS coordinate
    Returns (closest_index, distance_in_meters)
    """
    min_distance = float('inf')
    closest_index = -1
    
    for idx, point in enumerate(track_coords):
        distance = calculate_distance(gps_lat, gps_lon, point['latitude'], point['longitude'])
        if distance < min_distance:
            min_distance = distance
            closest_index = idx
    
    return closest_index, min_distance

def check_gps_match_track(device_id: str, track_id: str, gps_lat: float, gps_lon: float) -> Dict:
    """
    Check if GPS point matches the track and update match counter
    Returns match information including consecutive matches count
    """
    # Check if MongoDB is connected
    if track_sections_collection is None:
        return {"matched": False, "reason": "MongoDB not connected"}
    
    # Get active track data if track_id not specified, otherwise get specific track
    if track_id:
        track = track_sections_collection.find_one({"track_id": track_id})
    else:
        track = track_sections_collection.find_one({"is_active": True})
    
    if not track:
        return {"matched": False, "reason": "No active track found"}
    
    # Find closest point on track
    closest_idx, distance = find_closest_track_point(gps_lat, gps_lon, track['coordinates'])
    
    # Check if within threshold
    if distance <= GPS_MATCH_THRESHOLD_METERS:
        # Get or create match tracking for this device
        match_key = f"{device_id}_match_counter"
        match_counter = track_locks_collection.find_one({"match_key": match_key})
        
        if not match_counter:
            # Create new counter
            track_locks_collection.insert_one({
                "match_key": match_key,
                "device_id": device_id,
                "track_id": track_id,
                "consecutive_matches": 1,
                "last_matched_index": closest_idx,
                "updated_at": datetime.utcnow()
            })
            consecutive = 1
        else:
            # Update counter
            consecutive = match_counter['consecutive_matches'] + 1
            track_locks_collection.update_one(
                {"match_key": match_key},
                {
                    "$set": {
                        "consecutive_matches": consecutive,
                        "last_matched_index": closest_idx,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        
        return {
            "matched": True,
            "distance": distance,
            "track_index": closest_idx,
            "consecutive_matches": consecutive,
            "locked": consecutive >= REQUIRED_CONSECUTIVE_MATCHES
        }
    else:
        # Reset counter if no match
        match_key = f"{device_id}_match_counter"
        track_locks_collection.delete_one({"match_key": match_key})
        
        return {
            "matched": False,
            "distance": distance,
            "reason": f"Distance {distance:.1f}m exceeds threshold {GPS_MATCH_THRESHOLD_METERS}m"
        }

def lock_track(train_id: str, device_id: str, track_id: str) -> bool:
    """
    Lock a track to a specific train
    Returns True if successfully locked, False if already locked by another train
    """
    # Check if MongoDB is connected
    if track_locks_collection is None:
        print("⚠️ MongoDB not connected - cannot lock track")
        return False
        
    existing_lock = track_locks_collection.find_one({
        "lock_type": "track_lock",
        "track_id": track_id,
        "locked": True
    })
    
    if existing_lock:
        # Track already locked by another train
        if existing_lock['train_id'] != train_id:
            return False
        # Same train, update timestamp
        track_locks_collection.update_one(
            {"_id": existing_lock["_id"]},
            {"$set": {"updated_at": datetime.utcnow()}}
        )
        return True
    
    # Lock the track
    track_locks_collection.insert_one({
        "lock_type": "track_lock",
        "track_id": track_id,
        "train_id": train_id,
        "device_id": device_id,
        "locked": True,
        "locked_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    # Update train record - Do NOT set active=True here
    # Active flag should ONLY be set when collision is detected
    train_collection.update_one(
        {"train_id": train_id},
        {
            "$set": {
                "current_track": track_id,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return True

def detect_collision(train_id: str, device_id: str, track_id: str) -> Dict:
    """
    Check if there's a collision (another train on the same track)
    Returns collision status and details
    """
    # Find all locks for this track
    locks = list(track_locks_collection.find({
        "lock_type": "track_lock",
        "track_id": track_id,
        "locked": True
    }))
    
    if len(locks) >= 2:
        # Collision detected!
        collision_trains = [lock['train_id'] for lock in locks]
        collision_devices = [lock['device_id'] for lock in locks]
        
        # Activate buzzers for all trains on this track
        for train in collision_trains:
            train_collection.update_one(
                {"train_id": train},
                {
                    "$set": {
                        "active": True,
                        "collision_detected": True,
                        "collision_with": [t for t in collision_trains if t != train],
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        
        return {
            "collision": True,
            "track_id": track_id,
            "trains_involved": collision_trains,
            "devices_involved": collision_devices,
            "warning": "⚠️ COLLISION DETECTED! Multiple trains on same track!"
        }
    
    return {"collision": False}

# ==== Real Testing Trip Lifecycle ====

@app.post("/api/real-testing/start")
async def start_real_testing(request: RealTestingStartRequest):
    """
    Start a real-world testing trip for a train on a specific track.
    Locks the track and stores the selected track on the train.
    """
    try:
        if track_sections_collection is None or train_collection is None or track_locks_collection is None:
            raise HTTPException(
                status_code=503,
                detail="MongoDB not connected - service unavailable"
            )

        # Validate track exists
        track = track_sections_collection.find_one({"track_id": request.track_id})
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")

        # Set selected track on train
        train_doc = train_collection.find_one({"train_id": request.train_id})
        if not train_doc:
            raise HTTPException(status_code=404, detail="Train not found")

        # Try to lock track to this train
        locked = lock_track(request.train_id, train_doc.get("device_id", ""), request.track_id)
        if not locked:
            raise HTTPException(status_code=409, detail="Track already locked by another train")

        # Persist selected track - Do NOT set active=True here
        # Active flag should ONLY be set when collision is detected
        train_collection.update_one(
            {"train_id": request.train_id},
            {
                "$set": {
                    "selected_track_id": request.track_id,
                    "current_track": request.track_id,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        # Mark track as active for visibility (does not deactivate others)
        track_sections_collection.update_one(
            {"track_id": request.track_id},
            {"$set": {"is_active": True}}
        )

        return {
            "success": True,
            "message": "Real testing started",
            "train_id": request.train_id,
            "track_id": request.track_id
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error starting real testing: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start real testing: {str(e)}"
        )

@app.post("/api/real-testing/stop")
async def stop_real_testing(request: RealTestingStopRequest):
    """
    Stop a real-world testing trip: unlock track and clear selection.
    """
    try:
        if train_collection is None or track_locks_collection is None:
            raise HTTPException(
                status_code=503,
                detail="MongoDB not connected - service unavailable"
            )

        # If track_id not provided, try to use the train's selected/current track
        track_id = request.track_id
        if not track_id:
            train_doc = train_collection.find_one({"train_id": request.train_id})
            track_id = (train_doc or {}).get("selected_track_id") or (train_doc or {}).get("current_track")

        # Clear track lock(s) for this train and track
        if track_id:
            track_locks_collection.delete_many({
                "lock_type": "track_lock",
                "track_id": track_id,
                "train_id": request.train_id
            })

        # Clear selected track from train and deactivate
        train_collection.update_one(
            {"train_id": request.train_id},
            {
                "$unset": {"selected_track_id": ""},
                "$set": {
                    "active": False,
                    "current_track": None,
                    "collision_detected": False,
                    "collision_with": [],
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return {
            "success": True,
            "message": "Real testing stopped",
            "train_id": request.train_id,
            "track_id": track_id
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error stopping real testing: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop real testing: {str(e)}"
        )

def parse_csv_data(csv_content: str):
    """
    Parse CSV content and return coordinates
    """
    import io
    coordinates = []
    csv_file = io.StringIO(csv_content)
    csv_reader = csv.DictReader(csv_file)
    
    for row in csv_reader:
        try:
            lat = float(row['lat'])
            lon = float(row['lon'])
            coordinates.append({"latitude": lat, "longitude": lon})
        except (ValueError, KeyError) as e:
            print(f"⚠️ Skipping invalid row: {e}")
            continue
    
    return coordinates

def load_default_track_data():
    """
    Load default track data from CSV file if no tracks exist
    """
    # Check if MongoDB is connected
    if track_sections_collection is None:
        print("⚠️ MongoDB not connected - skipping track data loading")
        return
        
    csv_path = os.path.join(os.path.dirname(__file__), "actual train line 1 data.csv")
    
    # Check if any tracks exist
    if track_sections_collection.count_documents({}) > 0:
        print("✅ Track data already exists")
        return
    
    if not os.path.exists(csv_path):
        print(f"⚠️ Default CSV file not found: {csv_path}")
        return
    
    try:
        with open(csv_path, 'r') as file:
            csv_content = file.read()
            coordinates = parse_csv_data(csv_content)
        
        if coordinates:
            track_section = {
                "track_id": "track_01",
                "name": "Panadura - Kalutara Section",
                "filename": "actual train line 1 data.csv",
                "start_station": "Panadura",
                "end_station": "Kalutara",
                "coordinates": coordinates,
                "is_active": True,
                "uploaded_at": datetime.utcnow(),
                "created_at": datetime.utcnow()
            }
            
            track_sections_collection.insert_one(track_section)
            print(f"✅ Loaded default track data: {len(coordinates)} GPS points")
            print(f"   Track ID: track_01")
            print(f"   Route: Panadura → Kalutara")
        else:
            print("⚠️ No valid coordinates found in default CSV")
    except Exception as e:
        print(f"❌ Error loading default track: {e}")

async def create_track_section_from_session(session_doc):
    """
    Create a track section from session GPS data when session is completed
    """
    try:
        # Check if MongoDB is connected
        if track_sections_collection is None:
            print("⚠️ MongoDB not connected - cannot create track section")
            return False
        
        # Only create track section if session has GPS data
        gps_data = session_doc.get("gps_data", [])
        if not gps_data:
            print("⚠️ No GPS data in session - skipping track section creation")
            return False
        
        # Extract only latitude and longitude coordinates
        coordinates = []
        for gps_point in gps_data:
            if "latitude" in gps_point and "longitude" in gps_point:
                coordinates.append({
                    "latitude": gps_point["latitude"],
                    "longitude": gps_point["longitude"]
                })
        
        if not coordinates:
            print("⚠️ No valid coordinates found in session GPS data")
            return False
        
        # Generate track ID (track_01, track_02, etc. based on existing tracks)
        existing_tracks = track_sections_collection.count_documents({})
        track_id = f"track_{existing_tracks + 1:02d}"
        
        # Create track section document
        track_section = {
            "track_id": track_id,
            "name": f"Real-time Recorded Data - {session_doc['start_point']} to {session_doc['end_point']}",
            "filename": f"real time recorded data track id {existing_tracks + 1:02d}",
            "start_station": session_doc["start_point"],
            "end_station": session_doc["end_point"],
            "coordinates": coordinates,
            "is_active": False,  # Don't activate by default
            "uploaded_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "source_session_id": str(session_doc["_id"]),
            "gps_count": len(coordinates)
        }
        
        result = track_sections_collection.insert_one(track_section)
        print(f"✅ Created track section: {track_id} with {len(coordinates)} coordinates")
        print(f"   Route: {session_doc['start_point']} → {session_doc['end_point']}")
        print(f"   Filename: real time recorded data track id {existing_tracks + 1:02d}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating track section from session: {e}")
        return False

# ==== API Routes ====

@app.get("/")
async def root():
    """Serve the dashboard HTML file"""
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {"message": "GPS Tracker API is running", "status": "OK"}

@app.get("/dashboard")
async def dashboard():
    """Serve the dashboard HTML file"""
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    raise HTTPException(status_code=404, detail="Dashboard not found")

@app.get("/health")
async def health_check():
    return {"status": "OK", "message": "GPS Tracker API is running"}

@app.post("/api/gps")
async def receive_gps_data(gps_data: GPSData):
    """
    Receive GPS data from ESP32, check for track matching and collision detection
    """
    try:
        # Check if MongoDB is connected
        if collection is None or sessions_collection is None:
            raise HTTPException(
                status_code=503,
                detail="MongoDB not connected - service unavailable"
            )
        
        # Validate required fields
        if not gps_data.latitude or not gps_data.longitude:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: latitude and longitude"
            )

        # Check if there's an active session
        active_session = sessions_collection.find_one({"status": "active"})
        
        if not active_session:
            print(f"⚠️ No active session - GPS data not saved: {gps_data.latitude}, {gps_data.longitude}")
            return {
                "success": False,
                "message": "No active session. GPS data not stored.",
                "data": None
            }

        # Prepare GPS data document
        gps_document = {
            "latitude": gps_data.latitude,
            "longitude": gps_data.longitude,
            "satellites": gps_data.satellites,
            "hdop": gps_data.hdop,
            "accuracy": gps_data.accuracy,
            "timestamp": gps_data.timestamp,
            "device_id": gps_data.device_id,
            "received_at": datetime.utcnow()
        }

        # Push GPS data into session's gps_data array and increment count
        sessions_collection.update_one(
            {"_id": active_session["_id"]},
            {
                "$push": {"gps_data": gps_document},
                "$inc": {"gps_count": 1}
            }
        )
        # Insert into MongoDB
        result = collection.insert_one(gps_document)
        gps_document["_id"] = str(result.inserted_id)

        # ==== COLLISION DETECTION LOGIC ====
        # Find which train this device belongs to
        train_doc = train_collection.find_one({"device_id": gps_data.device_id})
        
        collision_info = {"collision": False}
        track_match_info = {}
        
        if train_doc:
            train_id = train_doc["train_id"]
            
            # Prefer explicitly selected track for real testing if present
            selected_track_id = train_doc.get("selected_track_id")
            if selected_track_id:
                track_id = selected_track_id
            else:
                # Fallback to active track for collision detection
                active_track = track_sections_collection.find_one({"is_active": True})
                if not active_track:
                    # If no active track, get the first track
                    active_track = track_sections_collection.find_one()
                
                track_id = active_track["track_id"] if active_track else None
            
            if track_id:
                match_result = check_gps_match_track(
                    gps_data.device_id,
                    track_id,
                    gps_data.latitude,
                    gps_data.longitude
                )
            else:
                match_result = {"matched": False, "reason": "No track data available"}
            
            track_match_info = match_result
            
            # If enough consecutive matches, lock the track ONLY during real testing
            if match_result.get("locked", False):
                # Only lock when a real testing trip is active and the matched track
                # equals the train's explicitly selected track
                if selected_track_id and selected_track_id == track_id:
                    # Try to lock the track
                    lock_success = lock_track(train_id, gps_data.device_id, track_id)
                    
                    if lock_success:
                        print(f"🔒 Track {track_id} locked by {train_id}")
                    else:
                        print(f"⚠️ Track {track_id} already locked by another train!")
                    
                    # Check for collision
                    collision_info = detect_collision(train_id, gps_data.device_id, track_id)
                    
                    if collision_info.get("collision", False):
                        print(f"🚨 COLLISION DETECTED on {track_id}!")
                        print(f"   Trains involved: {collision_info['trains_involved']}")

        print(f"📍 GPS Data saved: {gps_data.latitude}, {gps_data.longitude} from {gps_data.device_id} (Session: {active_session['_id']})")

        return {
            "success": True,
            "message": "GPS data saved successfully",
            "data": gps_document,
            "track_match": track_match_info,
            "collision": collision_info
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error saving GPS data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save GPS data: {str(e)}"
        )

@app.get("/api/gps")
async def get_gps_data(limit: int = 100):
    """
    Retrieve GPS data (latest records first)
    """
    try:
        # Fetch data from MongoDB
        cursor = collection.find().sort("received_at", -1).limit(limit)
        gps_data_list = []

        for doc in cursor:
            doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
            gps_data_list.append(doc)

        return {
            "success": True,
            "count": len(gps_data_list),
            "data": gps_data_list
        }

    except Exception as e:
        print(f"Error fetching GPS data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch GPS data: {str(e)}"
        )

@app.get("/api/gps/{device_id}")
async def get_gps_data_by_device(device_id: str, limit: int = 100):
    """
    Retrieve GPS data for a specific device
    """
    try:
        # Fetch data from MongoDB for specific device
        cursor = collection.find({"device_id": device_id}).sort("received_at", -1).limit(limit)
        gps_data_list = []

        for doc in cursor:
            doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
            gps_data_list.append(doc)

        return {
            "success": True,
            "count": len(gps_data_list),
            "data": gps_data_list
        }

    except Exception as e:
        print(f"Error fetching GPS data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch GPS data: {str(e)}"
        )

@app.get("/api/devices")
async def get_devices():
    """
    Get list of all unique device IDs that have sent data
    """
    try:
        # Get distinct device IDs from the collection
        device_ids = collection.distinct("device_id")
        
        # Get last update time for each device
        devices = []
        for device_id in device_ids:
            last_data = collection.find_one(
                {"device_id": device_id},
                sort=[("received_at", -1)]
            )
            if last_data:
                devices.append({
                    "device_id": device_id,
                    "last_seen": last_data.get("received_at", datetime.utcnow()),
                    "last_location": {
                        "latitude": last_data.get("latitude"),
                        "longitude": last_data.get("longitude")
                    }
                })
        
        return {
            "success": True,
            "count": len(devices),
            "devices": devices
        }
    
    except Exception as e:
        print(f"Error fetching devices: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch devices: {str(e)}"
        )

# ==== Train Details API Routes ====

@app.get("/api/train/status")
async def get_train_status(device_id: Optional[str] = None, train_id: Optional[str] = None):
    """
    Get the current train active status by device_id or train_id
    """
    try:
        query = {}
        if device_id:
            query["device_id"] = device_id
        elif train_id:
            query["train_id"] = train_id
        else:
            # Return all trains if no filter
            trains = list(train_collection.find())
            for train in trains:
                train["_id"] = str(train["_id"])
            return {
                "success": True,
                "trains": trains
            }
        
        train_doc = train_collection.find_one(query)
        
        if not train_doc:
            return {
                "success": False,
                "message": "Train not found",
                "active": False,
                "collision_detected": False
            }
        
        return {
            "success": True,
            "train_id": train_doc["train_id"],
            "device_id": train_doc["device_id"],
            "active": train_doc.get("active", False),
            "collision_detected": train_doc.get("collision_detected", False),
            "current_track": train_doc.get("current_track"),
            "selected_track_id": train_doc.get("selected_track_id"),
            "collision_with": train_doc.get("collision_with", []),
            "updated_at": train_doc.get("updated_at", datetime.utcnow())
        }
    
    except Exception as e:
        print(f"Error fetching train status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch train status: {str(e)}"
        )

@app.post("/api/train/status")
async def update_train_status(train_details: TrainDetails):
    """
    Update the train active status
    """
    try:
        # Update the train details document
        result = train_collection.update_one(
            {"train_id": train_details.train_id},
            {
                "$set": {
                    "active": train_details.active,
                    "updated_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        
        print(f"🚂 Train status updated: active={train_details.active}")
        
        return {
            "success": True,
            "message": "Train status updated successfully",
            "active": train_details.active
        }
    
    except Exception as e:
        print(f"Error updating train status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update train status: {str(e)}"
        )

# ==== Session Management API Routes ====

@app.post("/api/sessions")
async def create_session(session_data: SessionCreate):
    """
    Create a new GPS recording session
    """
    try:
        session_doc = {
            "start_point": session_data.start_point,
            "end_point": session_data.end_point,
            "status": "created",
            "created_at": datetime.utcnow(),
            "started_at": None,
            "ended_at": None,
            "gps_count": 0,
            "gps_data": []
        }
        
        result = sessions_collection.insert_one(session_doc)
        session_doc["_id"] = str(result.inserted_id)
        
        print(f"📝 Session created: {session_data.start_point} → {session_data.end_point}")
        
        return {
            "success": True,
            "message": "Session created successfully",
            "data": {
                "id": str(result.inserted_id),
                "start_point": session_doc["start_point"],
                "end_point": session_doc["end_point"],
                "status": session_doc["status"],
                "created_at": session_doc["created_at"],
                "gps_count": session_doc["gps_count"]
            }
        }
    
    except Exception as e:
        print(f"Error creating session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session: {str(e)}"
        )

@app.post("/api/sessions/{session_id}/start")
async def start_session(session_id: str):
    """
    Start recording GPS data for a session
    """
    try:
        # Check if session exists
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Stop any other active sessions
        sessions_collection.update_many(
            {"status": "active"},
            {"$set": {"status": "completed", "ended_at": datetime.utcnow()}}
        )
        
        # Start this session
        sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"status": "active", "started_at": datetime.utcnow()}}
        )
        
        print(f"▶️ Session started: {session_id}")
        
        return {
            "success": True,
            "message": "Session started successfully",
            "session_id": session_id
        }
    
    except Exception as e:
        print(f"Error starting session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start session: {str(e)}"
        )

@app.post("/api/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """
    Stop recording GPS data for a session and create track section from recorded data
    """
    try:
        # Check if session exists
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Stop the session
        sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"status": "completed", "ended_at": datetime.utcnow()}}
        )
        
        # Create track section from the completed session's GPS data
        track_section_created = await create_track_section_from_session(session)
        
        print(f"⏹️ Session stopped: {session_id}")
        if track_section_created:
            print(f"🛤️ Track section created from session data")
        
        return {
            "success": True,
            "message": "Session stopped successfully",
            "session_id": session_id,
            "track_section_created": track_section_created
        }
    
    except Exception as e:
        print(f"Error stopping session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop session: {str(e)}"
        )

@app.get("/api/sessions")
async def get_sessions():
    """
    Get all sessions
    """
    try:
        cursor = sessions_collection.find().sort("created_at", -1)
        sessions = []
        
        for doc in cursor:
            sessions.append({
                "id": str(doc["_id"]),
                "start_point": doc["start_point"],
                "end_point": doc["end_point"],
                "status": doc["status"],
                "created_at": doc["created_at"],
                "started_at": doc.get("started_at"),
                "ended_at": doc.get("ended_at"),
                "gps_count": doc.get("gps_count", 0)
            })
        
        return {
            "success": True,
            "count": len(sessions),
            "data": sessions
        }
    
    except Exception as e:
        print(f"Error fetching sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch sessions: {str(e)}"
        )

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session (GPS data is embedded, so it's deleted automatically)
    """
    try:
        # Check if session exists
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get GPS count before deletion
        gps_count = session.get("gps_count", 0)
        
        # Delete the session (embedded GPS data will be deleted automatically)
        sessions_collection.delete_one({"_id": ObjectId(session_id)})
        
        print(f"🗑️ Session deleted: {session_id} ({gps_count} GPS records deleted)")
        
        return {
            "success": True,
            "message": f"Session deleted successfully ({gps_count} GPS records deleted)",
            "session_id": session_id
        }
    
    except Exception as e:
        print(f"Error deleting session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete session: {str(e)}"
        )

@app.get("/api/sessions/{session_id}/gps")
async def get_session_gps_data(session_id: str, limit: int = 1000):
    """
    Get all GPS data for a specific session from embedded array
    """
    try:
        # Find the session
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get GPS data from the embedded array
        gps_data = session.get("gps_data", [])
        
        # Apply limit
        if len(gps_data) > limit:
            gps_data = gps_data[:limit]
        
        return {
            "success": True,
            "count": len(gps_data),
            "data": gps_data
        }
    
    except Exception as e:
        print(f"Error fetching session GPS data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch session GPS data: {str(e)}"
        )

@app.post("/api/sessions/{session_id}/create-track")
async def create_track_from_session(session_id: str):
    """
    Manually create a track section from an existing session's GPS data
    """
    try:
        # Find the session
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Create track section from session data
        track_section_created = await create_track_section_from_session(session)
        
        if track_section_created:
            return {
                "success": True,
                "message": "Track section created successfully from session data",
                "session_id": session_id
            }
        else:
            return {
                "success": False,
                "message": "Failed to create track section - no valid GPS data found",
                "session_id": session_id
            }
    
    except Exception as e:
        print(f"Error creating track from session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create track from session: {str(e)}"
        )

# ==== Track Management API Routes ====

@app.post("/api/tracks/upload")
async def upload_track_data(request: TrackUploadRequest):
    """
    Upload new track data from CSV content
    """
    try:
        # Check if MongoDB is connected
        if track_sections_collection is None:
            raise HTTPException(
                status_code=503,
                detail="MongoDB not connected - service unavailable"
            )
        
        # Parse CSV content
        coordinates = parse_csv_data(request.file_content)
        
        if not coordinates:
            raise HTTPException(status_code=400, detail="No valid coordinates found in CSV")
        
        # Generate track_id
        track_count = track_sections_collection.count_documents({})
        track_id = f"track_{track_count + 1:02d}"
        
        # Deactivate all other tracks if this is the first one
        if track_count == 0:
            is_active = True
        else:
            is_active = False
        
        # Create track document
        track_section = {
            "track_id": track_id,
            "name": request.name,
            "filename": request.filename,
            "start_station": request.start_station,
            "end_station": request.end_station,
            "coordinates": coordinates,
            "is_active": is_active,
            "uploaded_at": datetime.utcnow(),
            "created_at": datetime.utcnow()
        }
        
        result = track_sections_collection.insert_one(track_section)
        track_section["_id"] = str(result.inserted_id)
        
        print(f"✅ Uploaded track: {request.name} ({len(coordinates)} points)")
        
        return {
            "success": True,
            "message": "Track data uploaded successfully",
            "track": {
                "track_id": track_id,
                "name": request.name,
                "filename": request.filename,
                "points_count": len(coordinates),
                "is_active": is_active
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading track: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload track: {str(e)}"
        )

@app.get("/api/tracks")
async def get_tracks():
    """
    Get all track sections
    """
    try:
        # Check if MongoDB is connected
        if track_sections_collection is None:
            raise HTTPException(
                status_code=503,
                detail="MongoDB not connected - service unavailable"
            )
        
        tracks = list(track_sections_collection.find().sort("uploaded_at", -1))
        for track in tracks:
            track["_id"] = str(track["_id"])
            # Add point count
            track["points_count"] = len(track.get("coordinates", []))
            # Remove coordinates from list view for performance
            track.pop("coordinates", None)
        
        return {
            "success": True,
            "count": len(tracks),
            "tracks": tracks
        }
    except Exception as e:
        print(f"Error fetching tracks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch tracks: {str(e)}"
        )

@app.delete("/api/tracks/{track_id}")
async def delete_track(track_id: str):
    """
    Delete a track section
    """
    try:
        # Check if MongoDB is connected
        if track_sections_collection is None:
            raise HTTPException(
                status_code=503,
                detail="MongoDB not connected - service unavailable"
            )
        
        track = track_sections_collection.find_one({"track_id": track_id})
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
        
        was_active = track.get("is_active", False)
        
        # Delete the track
        track_sections_collection.delete_one({"track_id": track_id})
        
        # If deleted track was active, activate the first remaining track
        if was_active:
            first_track = track_sections_collection.find_one()
            if first_track:
                track_sections_collection.update_one(
                    {"_id": first_track["_id"]},
                    {"$set": {"is_active": True}}
                )
                print(f"✅ Activated track: {first_track['track_id']}")
        
        # Clear any locks on this track
        track_locks_collection.delete_many({"track_id": track_id})
        
        print(f"🗑️ Deleted track: {track_id}")
        
        return {
            "success": True,
            "message": "Track deleted successfully",
            "track_id": track_id
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting track: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete track: {str(e)}"
        )

@app.post("/api/tracks/{track_id}/activate")
async def activate_track(track_id: str):
    """
    Set a track as active for collision detection
    """
    try:
        # Check if MongoDB is connected
        if track_sections_collection is None:
            raise HTTPException(
                status_code=503,
                detail="MongoDB not connected - service unavailable"
            )
        
        track = track_sections_collection.find_one({"track_id": track_id})
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
        
        # Deactivate all tracks
        track_sections_collection.update_many(
            {},
            {"$set": {"is_active": False}}
        )
        
        # Activate selected track
        track_sections_collection.update_one(
            {"track_id": track_id},
            {"$set": {"is_active": True}}
        )
        
        # Reset all track locks and collision states
        track_locks_collection.delete_many({})
        train_collection.update_many(
            {},
            {
                "$set": {
                    "active": False,
                    "collision_detected": False,
                    "current_track": None,
                    "collision_with": []
                }
            }
        )
        
        print(f"✅ Activated track: {track_id}")
        print(f"🔄 Reset all collision states")
        
        return {
            "success": True,
            "message": f"Track {track_id} is now active",
            "track_id": track_id,
            "name": track["name"]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error activating track: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to activate track: {str(e)}"
        )

@app.get("/api/tracks/{track_id}/status")
async def get_track_status(track_id: str):
    """
    Get the lock status of a specific track
    """
    try:
        # Check if MongoDB is connected
        if track_locks_collection is None:
            raise HTTPException(
                status_code=503,
                detail="MongoDB not connected - service unavailable"
            )
        
        locks = list(track_locks_collection.find({
            "lock_type": "track_lock",
            "track_id": track_id,
            "locked": True
        }))
        
        for lock in locks:
            lock["_id"] = str(lock["_id"])
        
        return {
            "success": True,
            "track_id": track_id,
            "locked": len(locks) > 0,
            "lock_count": len(locks),
            "locks": locks,
            "collision_risk": len(locks) >= 2
        }
    except Exception as e:
        print(f"Error fetching track status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch track status: {str(e)}"
        )

@app.get("/api/tracks/{track_id}/coordinates")
async def get_track_coordinates(track_id: str):
    """
    Get the coordinates for a specific track for route mapping
    """
    try:
        # Check if MongoDB is connected
        if track_sections_collection is None:
            raise HTTPException(
                status_code=503,
                detail="MongoDB not connected - service unavailable"
            )
        
        track = track_sections_collection.find_one({"track_id": track_id})
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
        
        # Return track details with coordinates
        track_data = {
            "track_id": track["track_id"],
            "name": track["name"],
            "filename": track.get("filename", ""),
            "start_station": track.get("start_station", ""),
            "end_station": track.get("end_station", ""),
            "coordinates": track["coordinates"],
            "points_count": len(track["coordinates"]),
            "is_active": track.get("is_active", False),
            "uploaded_at": track.get("uploaded_at", track.get("created_at"))
        }
        
        return {
            "success": True,
            "track": track_data
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching track coordinates: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch track coordinates: {str(e)}"
        )

@app.post("/api/tracks/reset")
async def reset_all_tracks():
    """
    Reset all track locks and train statuses (for testing/simulation)
    """
    try:
        # Check if MongoDB is connected
        if track_locks_collection is None or train_collection is None:
            raise HTTPException(
                status_code=503,
                detail="MongoDB not connected - service unavailable"
            )
        
        # Clear all track locks
        track_locks_collection.delete_many({})
        
        # Reset all train statuses
        train_collection.update_many(
            {},
            {
                "$set": {
                    "active": False,
                    "collision_detected": False,
                    "current_track": None,
                    "collision_with": [],
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        print("🔄 All tracks and train statuses reset")
        
        return {
            "success": True,
            "message": "All tracks reset successfully"
        }
    except Exception as e:
        print(f"Error resetting tracks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset tracks: {str(e)}"
        )

# ==== Simulation API Routes ====

class SimulateGPSRequest(BaseModel):
    device_id: str
    track_id: str = "track_01"
    start_index: int = 0
    num_points: int = 10

@app.post("/api/simulate/gps")
async def simulate_gps_data(request: SimulateGPSRequest):
    """
    Simulate GPS data from a device following the track
    Useful for testing collision detection without physical devices
    """
    try:
        # Check if MongoDB is connected
        if track_sections_collection is None:
            raise HTTPException(
                status_code=503,
                detail="MongoDB not connected - service unavailable"
            )
        
        # Get track data
        track = track_sections_collection.find_one({"track_id": request.track_id})
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
        
        coordinates = track['coordinates']
        
        # Validate indices
        if request.start_index >= len(coordinates):
            raise HTTPException(status_code=400, detail="Start index out of range")
        
        # Get points to simulate
        end_index = min(request.start_index + request.num_points, len(coordinates))
        points_to_send = coordinates[request.start_index:end_index]
        
        # Find or create session for simulation
        active_session = sessions_collection.find_one({"status": "active"})
        if not active_session:
            # Create a simulation session
            session_doc = {
                "start_point": "Simulation",
                "end_point": "Simulation",
                "status": "active",
                "created_at": datetime.utcnow(),
                "started_at": datetime.utcnow(),
                "ended_at": None,
                "gps_count": 0,
                "gps_data": []
            }
            result = sessions_collection.insert_one(session_doc)
            active_session = sessions_collection.find_one({"_id": result.inserted_id})
        
        results = []
        for idx, point in enumerate(points_to_send):
            # Create GPS data object
            gps_data = GPSData(
                latitude=point['latitude'],
                longitude=point['longitude'],
                satellites=12,
                hdop=1.0,
                accuracy=5.0,
                timestamp=datetime.utcnow().isoformat(),
                device_id=request.device_id
            )
            
            # Send through the normal GPS endpoint
            response = await receive_gps_data(gps_data)
            results.append({
                "point_index": request.start_index + idx,
                "latitude": point['latitude'],
                "longitude": point['longitude'],
                "track_match": response.get("track_match", {}),
                "collision": response.get("collision", {})
            })
        
        return {
            "success": True,
            "device_id": request.device_id,
            "track_id": request.track_id,
            "points_sent": len(results),
            "results": results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error simulating GPS data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to simulate GPS data: {str(e)}"
        )

@app.get("/api/simulate/scenario/collision")
async def simulate_collision_scenario():
    """
    Simulate a collision scenario with two trains
    """
    try:
        # Reset everything first
        await reset_all_tracks()
        
        # Simulate Train 1 entering the track (first 20 points)
        train1_response = await simulate_gps_data(SimulateGPSRequest(
            device_id="ESP32_GPS_01",
            track_id="track_01",
            start_index=0,
            num_points=20
        ))
        
        # Simulate Train 2 entering the track (points 10-30, overlapping)
        train2_response = await simulate_gps_data(SimulateGPSRequest(
            device_id="ESP32_GPS_02",
            track_id="track_01",
            start_index=10,
            num_points=20
        ))
        
        # Get final status
        track_status = await get_track_status("track_01")
        train1_status = await get_train_status(device_id="ESP32_GPS_01")
        train2_status = await get_train_status(device_id="ESP32_GPS_02")
        
        return {
            "success": True,
            "message": "Collision scenario simulated",
            "train1": train1_status,
            "train2": train2_status,
            "track_status": track_status,
            "collision_detected": track_status.get("collision_risk", False)
        }
    
    except Exception as e:
        print(f"Error simulating collision: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to simulate collision: {str(e)}"
        )

@app.on_event("startup")
async def startup_event():
    """Load default track data on startup"""
    load_default_track_data()

if __name__ == "__main__":
    print("🚀 Starting GPS Tracker FastAPI Server...")
    print("📡 Waiting for GPS data from ESP32...")
    print("🛤️  Collision Detection System Active")
    port = int(os.getenv("PORT", 8000))  # Railway provides PORT env variable
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

