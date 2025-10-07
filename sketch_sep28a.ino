#include <TinyGPS++.h>
#include <WiFi.h>  
#include <HTTPClient.h>  
#include <ArduinoJson.h> 

// ==== DEVICE CONFIGURATION ====
const char* DEVICE_ID = "ESP32_GPS_01"; 

// ==== Wi-Fi Credentials ====
const char* ssid     = "Tyzon7";      
const char* password = "11111111";

// const char* ssid     = "Home_Fiber";      
// const char* password = "Fonseka@7";

// ==== FastAPI Backend Endpoint ====
//https://railway-safety-research.onrender.com/api/gps
const char* mongoAPIEndpoint = "https://railway-safety-research.onrender.com/api/gps"; 
const char* trainStatusEndpoint = "https://railway-safety-research.onrender.com/api/train/status"; 
// The FastAPI server now runs on port 8000  

// ==== GPS ====
HardwareSerial GPSSerial(2);
TinyGPSPlus gps;

const int GPS_RX_PIN = 25; // GPS TX -> ESP RX
const int GPS_TX_PIN = 26; // GPS RX -> ESP TX

// ==== Buzzer and LED Pins ====
const int BUZZER_PIN = 23;     // GPIO pin for buzzer
const int LED_PIN = 22;        // GPIO pin for LED/lights
const int POWER_LED_PIN = 21;  // GPIO pin for power indicator LED (always ON when powered)

// Train status
bool trainActive = false;
unsigned long lastTrainStatusCheck = 0;
const unsigned long TRAIN_STATUS_CHECK_INTERVAL = 5000UL;  // Check every 5 seconds

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
unsigned long lastGPSUpdateMs = 0;  // Track when we last received GPS data

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

// ==== Check Train Status from API ====
bool checkTrainStatus() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ WiFi not connected. Cannot check train status.");
    Serial.println("💡 Attempting to reconnect to WiFi...");
    WiFi.reconnect();
    delay(2000);
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("❌ WiFi reconnection failed.");
      return false;
    }
    Serial.println("✅ WiFi reconnected!");
  }

  HTTPClient http;
  http.setTimeout(5000);  // Set 5 second timeout
  
  // Build URL with device_id parameter
  String url = String(trainStatusEndpoint) + "?device_id=" + String(DEVICE_ID);
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  Serial.println("🔍 Checking train status...");
  Serial.print("📡 Connecting to: ");
  Serial.println(url);
  
  // Send GET request
  int httpResponseCode = http.GET();
  
  if (httpResponseCode == 200) {
    String response = http.getString();
    
    // Parse JSON response
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error) {
      bool active = doc["active"];
      bool collision = doc["collision_detected"];
      trainActive = active || collision;  // Activate if either active or collision
      
      Serial.print("🚂 Train Status: ");
      Serial.println(active ? "ACTIVE" : "INACTIVE");
      
      if (collision) {
        Serial.println("🚨 COLLISION DETECTED! ⚠️⚠️⚠️");
        Serial.print("   Collision with: ");
        JsonArray collisionWith = doc["collision_with"];
        for (JsonVariant train : collisionWith) {
          Serial.print(train.as<const char*>());
          Serial.print(" ");
        }
        Serial.println();
      }
      
      const char* currentTrack = doc["current_track"];
      if (currentTrack) {
        Serial.print("   Current Track: ");
        Serial.println(currentTrack);
      }
      
      // Control buzzer and LED based on status (active OR collision)
      if (trainActive) {
        digitalWrite(LED_PIN, HIGH);    // Turn on LED
        digitalWrite(BUZZER_PIN, HIGH); // Turn on buzzer
        if (collision) {
          Serial.println("🔊 BUZZER ACTIVATED - COLLISION WARNING!");
        }
      } else {
        digitalWrite(LED_PIN, LOW);     // Turn off LED
        digitalWrite(BUZZER_PIN, LOW);  // Turn off buzzer
      }
      
      http.end();
      return true;
    } else {
      Serial.println("❌ Error parsing train status JSON");
      http.end();
      return false;
    }
  } else {
    Serial.print("❌ Error checking train status. HTTP Code: ");
    Serial.println(httpResponseCode);
    
    // Detailed error messages
    if (httpResponseCode == -1) {
      Serial.println("💡 CONNECTION FAILED - Possible causes:");
      Serial.println("   1. Server not running on the specified IP");
      Serial.println("   2. Wrong IP address in code");
      Serial.println("   3. Firewall blocking the connection");
      Serial.println("   4. ESP32 and computer on different networks");
      Serial.print("   Current endpoint: ");
      Serial.println(url);
      Serial.print("   WiFi Status: ");
      Serial.println(WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected");
      Serial.print("   ESP32 IP: ");
      Serial.println(WiFi.localIP());
    } else if (httpResponseCode == -11) {
      Serial.println("💡 TIMEOUT - Server took too long to respond");
    } else if (httpResponseCode == 404) {
      Serial.println("💡 NOT FOUND - API endpoint doesn't exist");
    } else if (httpResponseCode == 500) {
      Serial.println("💡 SERVER ERROR - Backend server has an error");
    }
    
    http.end();
    return false;
  }
}

// ==== Send GPS Data to MongoDB ====
bool sendToMongoDB(double latitude, double longitude, int satellites, double hdop, 
                   const char* timestamp, double accuracy) {
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
  doc["accuracy"] = accuracy;  // Add accuracy field
  doc["device_id"] = DEVICE_ID;  // Use configured device ID
  
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

  // ==== Display Device ID ====
  Serial.println("==================================");
  Serial.print("🆔 DEVICE ID: ");
  Serial.println(DEVICE_ID);
  Serial.println("==================================");

  // ==== Initialize Power Indicator LED (Turn ON immediately) ====
  pinMode(POWER_LED_PIN, OUTPUT);
  digitalWrite(POWER_LED_PIN, HIGH);  // Power indicator ON - ESP32 is powered!
  Serial.println("💡 Power indicator LED turned ON");

  // ==== Initialize Buzzer and LED Pins ====
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);  // Start with buzzer off
  digitalWrite(LED_PIN, LOW);     // Start with LED off
  Serial.println("🔊 Buzzer and LED initialized");

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
  
  // ==== Check initial train status ====
  checkTrainStatus();
}

void loop() {
  // Feed TinyGPS++
  while (GPSSerial.available()) gps.encode(GPSSerial.read());

  const unsigned long now = millis();

  // ==== Check Train Status Periodically ====
  if (now - lastTrainStatusCheck >= TRAIN_STATUS_CHECK_INTERVAL) {
    lastTrainStatusCheck = now;
    checkTrainStatus();
  }

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
    
    // Mark that we received fresh GPS data
    lastGPSUpdateMs = now;
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
      
      // ==== Calculate and Print Accuracy Metrics ====
      // Get Kalman filter uncertainties (standard deviation)
      double sigma_lat_deg = kfLat.sigma();  // in degrees
      double sigma_lon_deg = kfLon.sigma();  // in degrees
      
      // Convert to meters for practical interpretation
      double sigma_lat_m = degLatToMeters(sigma_lat_deg);
      double sigma_lon_m = degLonToMeters(sigma_lon_deg, kLat);
      
      // Combined position accuracy (CEP - Circular Error Probable)
      // This gives the radius within which 50% of positions fall
      double cep_meters = 0.59 * (sigma_lat_m + sigma_lon_m);
      
      // 95% confidence radius (approximately 2-sigma)
      double accuracy_95_meters = sqrt(sq(2.0 * sigma_lat_m) + sq(2.0 * sigma_lon_m));
      
      // Raw GPS accuracy estimate (based on HDOP)
      double hdopVal = gps.hdop.isValid() ? gps.hdop.hdop() : 0.0;
      double raw_accuracy_m = max(1.5, 3.0 * hdopVal);
      
      Serial.println("\n📊 Accuracy After Kalman Filtering:");
      Serial.print("  Lat Uncertainty: "); Serial.print(sigma_lat_m, 2); Serial.println(" m");
      Serial.print("  Lon Uncertainty: "); Serial.print(sigma_lon_m, 2); Serial.println(" m");
      Serial.print("  CEP (50% confidence): "); Serial.print(cep_meters, 2); Serial.println(" m");
      Serial.print("  Accuracy (95% confidence): "); Serial.print(accuracy_95_meters, 2); Serial.println(" m");
      Serial.print("  Raw GPS Accuracy: "); Serial.print(raw_accuracy_m, 2); Serial.println(" m");
      
      // Show improvement
      double improvement_percent = ((raw_accuracy_m - accuracy_95_meters) / raw_accuracy_m) * 100.0;
      if (improvement_percent > 0) {
        Serial.print("  🎯 Improvement: "); Serial.print(improvement_percent, 1); Serial.println("% better");
      }
      Serial.println();

      // ==== Check if GPS data is fresh (received within last 30 seconds) ====
      const unsigned long GPS_TIMEOUT_MS = 30000UL;  // 30 seconds
      unsigned long timeSinceLastGPS = now - lastGPSUpdateMs;
      
      if (lastGPSUpdateMs > 0 && timeSinceLastGPS < GPS_TIMEOUT_MS) {
        // GPS data is fresh - send to MongoDB
        char timestampStr[40] = "Unknown";
        if (gps.date.isValid() && gps.time.isValid()) {
          sprintf(timestampStr, "%04d-%02d-%02d %02d:%02d:%02d UTC",
                  gps.date.year(), gps.date.month(), gps.date.day(),
                  gps.time.hour(), gps.time.minute(), gps.time.second());
        }
        
        int sats = gps.satellites.isValid() ? gps.satellites.value() : 0;
        double hdopVal = gps.hdop.isValid() ? gps.hdop.hdop() : 0.0;
        
        // Send with accuracy (95% confidence radius)
        sendToMongoDB(kLat, kLon, sats, hdopVal, timestampStr, accuracy_95_meters);
      } else {
        // GPS data is stale or GPS is disconnected
        Serial.println("⚠️ GPS data is stale or GPS disconnected. Not sending to MongoDB.");
        Serial.print("Time since last GPS update: ");
        Serial.print(timeSinceLastGPS / 1000.0);
        Serial.println(" seconds");
      }
      
    } else {
      Serial.println("Waiting for stable, high-quality fixes.");
    }

    Serial.println("-------------------------");
  }
}
