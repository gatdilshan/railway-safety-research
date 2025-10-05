# 📡 Device ID Setup Guide

This guide explains how to configure and manage multiple ESP32 GPS devices in your Railway Safety System.

## 🎯 Overview

The device ID system allows you to:

- Track multiple ESP32 boards simultaneously
- Identify which device is at which location
- Filter and view data from specific devices
- See all devices on the map with different colored markers

## 🔧 Setting Up Device IDs

### Step 1: Configure Each ESP32 Board

1. Open the `sketch_sep28a.ino` file in Arduino IDE
2. Find the **DEVICE CONFIGURATION** section at the top (around line 6-9):

```cpp
// ==== DEVICE CONFIGURATION ====
// ⚠️ IMPORTANT: Change this for each ESP32 board to a unique ID
// Examples: "ESP32_STATION_01", "ESP32_STATION_02", "ESP32_COLOMBO", "ESP32_GALLE"
const char* DEVICE_ID = "ESP32_GPS_01";  // 🔧 CHANGE THIS FOR EACH DEVICE!
```

3. **Change the DEVICE_ID** to a unique identifier for each board. Use meaningful names that indicate location or purpose:

   **Examples:**

   - `"ESP32_STATION_01"` - For station 1
   - `"ESP32_STATION_02"` - For station 2
   - `"ESP32_COLOMBO"` - For Colombo location
   - `"ESP32_GALLE"` - For Galle location
   - `"ESP32_CROSSING_A"` - For railway crossing A
   - `"ESP32_NORTH_LINE"` - For north railway line

4. Upload the code to your ESP32 board
5. Repeat for each additional device with a different DEVICE_ID

### Step 2: Verify Device Configuration

When the ESP32 starts up, it will display its Device ID in the Serial Monitor:

```
==================================
🆔 DEVICE ID: ESP32_STATION_01
==================================
```

This confirms which device ID is programmed into that board.

## 📊 Using the Dashboard

### Viewing All Devices

1. Open the dashboard in your web browser
2. By default, the dashboard shows "📡 All Devices" in the device selector
3. The map will display all active devices with different colored markers
4. Each device gets a unique color to distinguish them on the map

### Filtering by Specific Device

1. Use the **"🆔 Select Device"** dropdown in the Statistics card
2. Choose a specific device ID to see only that device's data
3. The map will zoom to that device's location
4. GPS data table will show only data from the selected device

### Device Status Indicator

Below the device selector, you'll see a status display:

```
📊 3 device(s) total | 🟢 2 online | 🔴 1 offline
```

- **Online (🟢)**: Device sent data within the last 60 seconds
- **Offline (🔴)**: No data received for more than 60 seconds

### Statistics Display

When viewing a specific device or the latest data:

- **Latitude**: Current latitude coordinates
- **Longitude**: Current longitude coordinates
- **Satellites**: Number of GPS satellites in view
- **HDOP**: Horizontal Dilution of Precision (accuracy indicator)
- **Accuracy**: Kalman-filtered accuracy in meters
- **Device ID**: The unique identifier of the device

### GPS Data Table

The Recent GPS Data table now includes a "Device ID" column showing which device each GPS reading came from.

### Map Features

- **Multiple Colored Markers**: Each device appears as a different colored circle on the map
- **Click on Markers**: Click any marker to see device details in a popup
- **Auto-Zoom**: When filtering by device, the map automatically zooms to that device's location
- **View All**: When "All Devices" is selected, the map shows all devices at once

## 🗂️ Session Management with Multiple Devices

When creating GPS recording sessions, data from **all active devices** will be recorded if there's an active session. In the session view:

- The GPS data table shows which device each point came from
- You can track routes from multiple devices in a single session
- The route map will show the combined path of all devices

## 🔍 Backend API Endpoints

The system provides several endpoints for device management:

### Get All Devices

```
GET /api/devices
```

Returns a list of all devices that have sent data, including their last known location and last seen time.

### Get GPS Data by Device

```
GET /api/gps/{device_id}
```

Returns GPS data for a specific device.

### Get All GPS Data

```
GET /api/gps
```

Returns GPS data from all devices (default behavior).

## 💡 Best Practices

1. **Use Descriptive Names**: Choose device IDs that clearly indicate the device's location or purpose
2. **Document Your Devices**: Keep a list of which physical device has which ID
3. **Label Physical Devices**: Put a physical label on each ESP32 board with its Device ID
4. **Test Each Device**: Before deploying, verify each device reports its correct ID
5. **Monitor Status**: Regularly check the device status indicator to ensure all devices are online

## 🛠️ Troubleshooting

### Device Not Appearing in List

- Ensure the device has sent at least one GPS reading
- Check that the device is connected to WiFi
- Verify the device can reach the backend server
- Check the Serial Monitor for error messages

### Wrong Device ID Displayed

- Re-upload the sketch to the ESP32 with the correct Device ID
- Power cycle the device after uploading
- Check the Serial Monitor to confirm the Device ID at startup

### Multiple Devices Showing Same ID

- Each device must have a unique ID
- Re-program devices that have duplicate IDs
- Use the Serial Monitor to verify which physical device has which ID

## 📝 Example Deployment Scenario

**Railway with 3 Stations:**

1. **Station A (Main)**

   - Device ID: `ESP32_STATION_A`
   - Location: Main railway station entrance

2. **Station B (Mid)**

   - Device ID: `ESP32_STATION_B`
   - Location: Mid-line station platform

3. **Crossing C (Junction)**
   - Device ID: `ESP32_CROSSING_C`
   - Location: Railway crossing junction

All three devices send data to the same backend, and the dashboard allows you to:

- View all three locations simultaneously on the map
- Filter to see data from specific stations
- Track train movements across all stations in sessions
- Monitor which devices are online/offline

## 🎨 Device Marker Colors

The system uses a color palette to distinguish devices:

1. Purple (`#667eea`)
2. Red (`#f44336`)
3. Green (`#4caf50`)
4. Orange (`#ff9800`)
5. Blue (`#2196f3`)
6. Purple-Pink (`#9c27b0`)
7. Cyan (`#00bcd4`)
8. Yellow (`#ffeb3b`)

Colors are assigned automatically as devices appear in the system.

## 🚀 Summary

With device IDs configured, you can now:

- ✅ Deploy multiple ESP32 boards across your railway system
- ✅ Track each device's location independently
- ✅ Filter and view data from specific devices
- ✅ Monitor the online/offline status of all devices
- ✅ Record sessions with data from multiple devices
- ✅ See all devices on a single map with unique colors

Your railway safety system is now ready for multi-device deployment! 🎉
