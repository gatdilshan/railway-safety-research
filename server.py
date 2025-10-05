from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import uvicorn
import os

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

client = None
db = None
collection = None
train_collection = None
sessions_collection = None

try:
    client = MongoClient(MONGODB_URI)
    # Test the connection
    client.admin.command('ping')
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]
    train_collection = db[TRAIN_DETAILS_COLLECTION]
    sessions_collection = db[SESSIONS_COLLECTION]
    
    # Initialize train details if not exists
    if train_collection.count_documents({}) == 0:
        train_collection.insert_one({
            "train_id": "TRAIN_01",
            "active": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
    
    print("✅ Connected to MongoDB")
    print("✅ Train details collection initialized")
    print("✅ Sessions collection initialized")
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
    Receive GPS data from ESP32 and store in session's gps_data array
    """
    try:
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

        print(f"📍 GPS Data saved: {gps_data.latitude}, {gps_data.longitude} from {gps_data.device_id} (Session: {active_session['_id']})")

        return {
            "success": True,
            "message": "GPS data saved successfully",
            "data": gps_document
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

# ==== Train Details API Routes ====

@app.get("/api/train/status")
async def get_train_status():
    """
    Get the current train active status
    """
    try:
        # Get the first (and only) train details document
        train_doc = train_collection.find_one({"train_id": "TRAIN_01"})
        
        if not train_doc:
            # If not found, create default
            train_collection.insert_one({
                "train_id": "TRAIN_01",
                "active": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            train_doc = train_collection.find_one({"train_id": "TRAIN_01"})
        
        return {
            "success": True,
            "train_id": train_doc["train_id"],
            "active": train_doc["active"],
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
    Stop recording GPS data for a session
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
        
        print(f"⏹️ Session stopped: {session_id}")
        
        return {
            "success": True,
            "message": "Session stopped successfully",
            "session_id": session_id
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

if __name__ == "__main__":
    print("🚀 Starting GPS Tracker FastAPI Server...")
    print("📡 Waiting for GPS data from ESP32...")
    port = int(os.getenv("PORT", 8000))  # Railway provides PORT env variable
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

