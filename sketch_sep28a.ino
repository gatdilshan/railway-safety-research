#include <TinyGPS++.h>
#include <WiFi.h>   // Wi-Fi library
#include <HTTPClient.h>  // HTTP client for API requests
#include <ArduinoJson.h>  // JSON library for MongoDB data

// ==== Wi-Fi Credentials ====
const char* ssid     = "Tyzon7";      
const char* password = "11111111";

// ==== FastAPI Backend Endpoint ====
// For localhost testing (ESP32 and computer on same network):
// const char* mongoAPIEndpoint = "http://127.0.0.1:8000/api/gps";  // ❌ This won't work from ESP32!
// Replace YOUR_SERVER_IP with your computer's IP address (use 'ipconfig' on Windows)
// Example: "http://192.168.1.100:8000/api/gps"
const char* mongoAPIEndpoint = "http://172.20.10.5:8000/api/gps";  // Your computer's IP
// The FastAPI server now runs on port 8000  

// ==== GPS ====
HardwareSerial GPSSerial(2);
TinyGPSPlus gps;

const int GPS_RX_PIN = 25; // GPS TX -> ESP RX
const int GPS_TX_PIN = 26; // GPS RX -> ESP TX

// Print time interval
const unsigned long PRINT_INTERVAL_MS = 15000UL;
unsigned long lastPrint = 0;

const double HDOP_MAX = 1.8;    
const uint8_t MINSATS = 8;       

// ==== 1D Kalman Filter ====
struct KF1D {
  bool initialized = false;
  double x = 0.0;
  double P = 0.0;
  void predict(double Q) { if (initialized) P += Q; }
  void update(double z, double R) {
    if (!initialized) { x = z; P = R; initialized = true; return; }
    double K = P / (P + R);
    x = x + K * (z - x);
    P = (1.0 - K) * P;
  }
  double sigma() const { return initialized ? sqrt(P) : NAN; }
};

KF1D kfLat, kfLon;
unsigned long lastKFMs = 0;

// ==== Conversions ====
static inline double metersToDegLat(double m)    { return m / 111320.0; }
static inline double metersToDegLon(double m, double lat_deg) {
  double c = cos(lat_deg * (PI / 180.0));
  if (c < 1e-6) c = 1e-6;
  return m / (111320.0 * c);
}
static inline double degLatToMeters(double deg)  { return deg * 111320.0; }
static inline double degLonToMeters(double deg, double lat_deg) {
  double c = cos(lat_deg * (PI / 180.0));
  if (c < 1e-6) c = 1e-6;
  return deg * 111320.0 * c;
}

// ==== Send GPS Data to MongoDB ====
bool sendToMongoDB(double latitude, double longitude, int satellites, double hdop, 
                   const char* timestamp) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ WiFi not connected. Cannot send to MongoDB.");
    return false;
  }

  HTTPClient http;
  http.begin(mongoAPIEndpoint);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON document
  StaticJsonDocument<512> doc;
  doc["latitude"] = latitude;
  doc["longitude"] = longitude;
  doc["satellites"] = satellites;
  doc["hdop"] = hdop;
  doc["timestamp"] = timestamp;
  doc["device_id"] = "ESP32_GPS_01";  // You can customize this
  
  // Serialize JSON
  String jsonString;
  serializeJson(doc, jsonString);
  
  Serial.println("📤 Sending to MongoDB:");
  Serial.println(jsonString);
  
  // Send POST request
  int httpResponseCode = http.POST(jsonString);
  
  if (httpResponseCode > 0) {
    Serial.print("✅ MongoDB Response Code: ");
    Serial.println(httpResponseCode);
    String response = http.getString();
    Serial.println("Response: " + response);
    http.end();
    return true;
  } else {
    Serial.print("❌ Error sending to MongoDB. Code: ");
    Serial.println(httpResponseCode);
    http.end();
    return false;
  }
}

void setup() {
  Serial.begin(115200);
  delay(100);

  // ==== Connect to WiFi ====
  WiFi.begin(ssid, password);
  Serial.print("🔗 Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  // ==== Start GPS ====
  GPSSerial.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  Serial.println("📡 ESP32 + NEO-M8N: Kalman filtering enabled (lat/lon)");
}

void loop() {
  // Feed TinyGPS++
  while (GPSSerial.available()) gps.encode(GPSSerial.read());

  const unsigned long now = millis();

  // GPS Kalman update
  if (gps.location.isUpdated() &&
      gps.location.isValid() &&
      gps.hdop.isValid() &&
      gps.satellites.isValid() &&
      gps.hdop.hdop() <= HDOP_MAX &&
      gps.satellites.value() >= MINSATS) {

    double rawLat = gps.location.lat();
    double rawLon = gps.location.lng();
    double hdop   = gps.hdop.hdop();

    double meas_sigma_m = max(1.5, 3.0 * hdop); 
    double R_lat = sq(metersToDegLat(meas_sigma_m));
    double R_lon = sq(metersToDegLon(meas_sigma_m, rawLat));

    const double base_q_mps = 1.0;
    double dt = 1.0;
    if (lastKFMs != 0) dt = max(0.2, (now - lastKFMs) / 1000.0); 
    lastKFMs = now;

    double q_m2 = sq(base_q_mps) * dt; 
    double latForLon = kfLat.initialized ? kfLat.x : rawLat;
    double Q_lat = sq(metersToDegLat(sqrt(q_m2)));                
    double Q_lon = sq(metersToDegLon(sqrt(q_m2), latForLon));      

    kfLat.predict(Q_lat);
    kfLon.predict(Q_lon);
    kfLat.update(rawLat, R_lat);
    kfLon.update(rawLon, R_lon);
  }

  // Print block
  if (now - lastPrint >= PRINT_INTERVAL_MS) {
    lastPrint = now;

    // Show Wi-Fi status
    Serial.print("WiFi Status: ");
    Serial.println(WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected");

    // Timestamp
    if (gps.date.isValid() && gps.time.isValid()) {
      char buf[40];
      sprintf(buf, "%04d-%02d-%02d %02d:%02d:%02d UTC",
              gps.date.year(), gps.date.month(), gps.date.day(),
              gps.time.hour(), gps.time.minute(), gps.time.second());
      Serial.print("Timestamp: "); Serial.println(buf);
    } else {
      Serial.println("Timestamp: Unknown (no GPS time)");
    }

    // Satellites & HDOP
    Serial.print("Satellites: ");
    if (gps.satellites.isValid()) Serial.println(gps.satellites.value()); else Serial.println("?");
    Serial.print("HDOP: ");
    if (gps.hdop.isValid()) Serial.println(gps.hdop.hdop(), 2); else Serial.println("?");

    // Location data
    if (gps.location.isValid() && kfLat.initialized && kfLon.initialized) {
      double rawLat = gps.location.lat();
      double rawLon = gps.location.lng();
      double kLat = kfLat.x;
      double kLon = kfLon.x;

      Serial.println("✅ Good fix (Kalman-smoothed):");
      Serial.print("Longitude (KF): "); Serial.println(kLon, 7);
      Serial.print("Latitude  (KF): "); Serial.println(kLat, 7);

      // ==== Send to MongoDB ====
      char timestampStr[40] = "Unknown";
      if (gps.date.isValid() && gps.time.isValid()) {
        sprintf(timestampStr, "%04d-%02d-%02d %02d:%02d:%02d UTC",
                gps.date.year(), gps.date.month(), gps.date.day(),
                gps.time.hour(), gps.time.minute(), gps.time.second());
      }
      
      int sats = gps.satellites.isValid() ? gps.satellites.value() : 0;
      double hdopVal = gps.hdop.isValid() ? gps.hdop.hdop() : 0.0;
      
      sendToMongoDB(kLat, kLon, sats, hdopVal, timestampStr);
      
    } else {
      Serial.println("Waiting for stable, high-quality fixes.");
    }

    Serial.println("-------------------------");
  }
}
