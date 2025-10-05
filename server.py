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

client = None
db = None
collection = None
train_collection = None

try:
    client = MongoClient(MONGODB_URI)
    # Test the connection
    client.admin.command('ping')
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]
    train_collection = db[TRAIN_DETAILS_COLLECTION]
    
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
    Receive GPS data from ESP32 and store in MongoDB
    """
    try:
        # Validate required fields
        if not gps_data.latitude or not gps_data.longitude:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: latitude and longitude"
            )

        # Prepare document for MongoDB
        document = {
            "latitude": gps_data.latitude,
            "longitude": gps_data.longitude,
            "satellites": gps_data.satellites,
            "hdop": gps_data.hdop,
            "accuracy": gps_data.accuracy,  # Store accuracy
            "timestamp": gps_data.timestamp,
            "device_id": gps_data.device_id,
            "received_at": datetime.utcnow()
        }

        # Insert into MongoDB
        result = collection.insert_one(document)
        document["_id"] = str(result.inserted_id)

        print(f"📍 GPS Data saved: {gps_data.latitude}, {gps_data.longitude} from {gps_data.device_id}")

        return {
            "success": True,
            "message": "GPS data saved successfully",
            "data": document
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

if __name__ == "__main__":
    print("🚀 Starting GPS Tracker FastAPI Server...")
    print("📡 Waiting for GPS data from ESP32...")
    port = int(os.getenv("PORT", 8000))  # Railway provides PORT env variable
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

