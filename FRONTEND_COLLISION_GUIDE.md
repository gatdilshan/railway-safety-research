# Frontend Collision Detection - User Guide

## 🎨 What Was Added to the Dashboard

Your dashboard now has **automatic collision detection visualization** with visual and audio alerts!

## ✨ New Features

### 1. **Animated Red Warning Light** 🚨

- Appears at the top of the dashboard when collision is detected
- Animated red light that blinks continuously
- Pulsing effect to draw attention
- Shows collision details in real-time

### 2. **Audio Alarm** 🔊

- Plays automatically when collision is detected
- Continuous beeping sound (800 Hz tone)
- Repeats every 600ms
- Stops automatically when collision is cleared

### 3. **Real-Time Monitoring** 📡

- Checks collision status every 3 seconds
- Automatically updates display
- No manual refresh needed
- Shows which trains are involved

### 4. **Collision Information Panel** 📊

- Displays train IDs involved
- Shows track information
- Indicates buzzer activation status
- Auto-scrolls to top when alert appears

## 🎬 How It Works

### When Collision is Detected:

```
1. Dashboard checks /api/train/status every 3 seconds
   ↓
2. Detects trains with collision_detected: true
   ↓
3. RED WARNING PANEL appears at top
   ↓
4. ALARM SOUND starts playing
   ↓
5. Shows train details & track info
   ↓
6. Panel stays until collision is cleared
```

### When Collision is Cleared:

```
1. System detects collision_detected: false
   ↓
2. GREEN "All Clear" message shows
   ↓
3. ALARM SOUND stops
   ↓
4. Panel hides after 3 seconds
   ↓
5. Returns to normal dashboard
```

## 🖥️ Visual Elements

### Collision Warning Panel (Red):

```
┌─────────────────────────────────────┐
│         [Red Blinking Light]        │
│     ⚠️ COLLISION ALERT ⚠️           │
│                                     │
│  Multiple trains detected on the    │
│  same track!                        │
│                                     │
│  🚂 Trains Involved:                │
│  TRAIN_01 (ESP32_GPS_01) &          │
│  TRAIN_02 (ESP32_GPS_02)            │
│                                     │
│  🛤️ Track: track_01                 │
│                                     │
│  ⚠️ BUZZER ACTIVATED ON ALL TRAINS  │
└─────────────────────────────────────┘
```

### All Clear Panel (Green):

```
┌─────────────────────────────────────┐
│         [Green Light] ✅            │
│          All Clear                  │
│  No collision detected.             │
│  Tracks are safe.                   │
└─────────────────────────────────────┘
```

## 🧪 Testing the Frontend

### Option 1: Using Simulation API

1. **Start your server:**

```bash
python server.py
```

2. **Open dashboard:**

```
http://localhost:8000/dashboard
```

3. **Trigger collision in another terminal:**

```bash
curl http://localhost:8000/api/simulate/scenario/collision
```

4. **Watch the dashboard:**
   - Red warning panel appears immediately
   - Alarm sound starts playing
   - Train information displayed

### Option 2: Using Real ESP32 Devices

1. **Start server and open dashboard**

2. **Create and start a session** via dashboard

3. **Take both ESP32 devices** to the actual track (Panadura-Kalutara)

4. **When both trains enter the same track:**
   - Dashboard shows red alert automatically
   - Alarm plays
   - Shows train details
   - ESP32 buzzers also activate

## 🎛️ Configuration

### Alarm Sound Settings

Located in `dashboard.html` line ~2231:

```javascript
oscillator.frequency.value = 800; // Frequency in Hz (adjust pitch)
```

**Suggested values:**

- `400` - Lower pitch (less urgent)
- `800` - Medium pitch (default)
- `1200` - Higher pitch (more urgent)

### Check Interval

Located in `dashboard.html` line ~2352:

```javascript
collisionCheckInterval = setInterval(checkCollisionStatus, 3000); // 3 seconds
```

**Adjust if needed:**

- `1000` - Check every 1 second (more responsive, more server load)
- `3000` - Check every 3 seconds (default, balanced)
- `5000` - Check every 5 seconds (less server load)

### Alarm Repeat Rate

Located in `dashboard.html` line ~2241:

```javascript
setTimeout(() => playAlarmSound(), 600); // 600ms between beeps
```

**Adjust timing:**

- `300` - Faster beeps (more urgent)
- `600` - Default (balanced)
- `1000` - Slower beeps (less annoying)

## 📱 Mobile Responsive

The collision warning is fully responsive:

- **Desktop:** Large red panel, full details
- **Tablet:** Medium panel, readable text
- **Mobile:** Optimized size, clear warning

## 🔊 Browser Audio Permissions

Some browsers block auto-playing audio. If alarm doesn't play:

1. **Chrome/Edge:**

   - Click anywhere on the page first
   - Or enable "Sound" in site permissions

2. **Firefox:**

   - Should work automatically
   - Check site permissions if not

3. **Safari:**
   - May require user interaction first
   - Tap screen to enable audio

## 🎨 Customizing Colors

### Change Warning Color (in CSS):

```css
.collision-warning {
  background: linear-gradient(135deg, #ff0000 0%, #cc0000 100%);
  /* Change #ff0000 to your preferred color */
}
```

### Change Light Animation:

```css
@keyframes blinkRed {
  0%,
  49% {
    background: radial-gradient(circle, #ff0000, #8b0000);
    /* First state */
  }
  50%,
  100% {
    background: radial-gradient(circle, #8b0000, #4b0000);
    /* Second state (dimmer) */
  }
}
```

## 🐛 Troubleshooting

### Issue: No Warning Shows

**Solution:**

- Check browser console for errors
- Verify server is running
- Test API: `curl http://localhost:8000/api/train/status`
- Make sure collision actually detected

### Issue: No Sound Plays

**Solution:**

- Click anywhere on page first (browser auto-play policy)
- Check browser audio permissions
- Check volume is not muted
- Look for console errors

### Issue: Warning Doesn't Clear

**Solution:**

- Check if collision actually cleared in backend
- Test reset: `curl -X POST http://localhost:8000/api/tracks/reset`
- Refresh dashboard

### Issue: Multiple Alarms Playing

**Solution:**

- Only one tab should have dashboard open
- Refresh page to reset
- Check browser console for errors

## 📊 What You'll See in Console

Normal operation:

```
✅ Collision monitoring started
🛤️ Collision Detection System Active
```

When collision detected:

```
Collision detected!
Trains involved: TRAIN_01, TRAIN_02
Playing alarm sound...
```

When collision cleared:

```
Collision cleared
Alarm stopped
```

## 🎯 Key Features Summary

| Feature           | Description             | Status    |
| ----------------- | ----------------------- | --------- |
| Red Warning Light | Animated blinking light | ✅ Active |
| Alarm Sound       | Continuous beeping      | ✅ Active |
| Auto-Monitoring   | Checks every 3 seconds  | ✅ Active |
| Train Information | Shows involved trains   | ✅ Active |
| Track Information | Shows affected track    | ✅ Active |
| Auto-Clear        | Hides when safe         | ✅ Active |
| Mobile Responsive | Works on all devices    | ✅ Active |

## 🚀 Complete Test Workflow

1. **Open Terminal 1:**

```bash
python server.py
```

2. **Open Browser:**

```
http://localhost:8000/dashboard
```

3. **Open Terminal 2:**

```bash
# Trigger collision
curl http://localhost:8000/api/simulate/scenario/collision

# Watch dashboard - should see:
# - Red warning appears
# - Alarm plays
# - Train info shown
```

4. **Clear Collision (Terminal 2):**

```bash
curl -X POST http://localhost:8000/api/tracks/reset

# Watch dashboard - should see:
# - Green "All Clear" message
# - Alarm stops
# - Panel disappears after 3 seconds
```

## 📝 Notes

- **Automatic Operation:** No manual interaction needed
- **Real-Time:** Updates within 3 seconds
- **Persistent:** Warning stays until collision cleared
- **Visual & Audio:** Dual alert system for maximum attention
- **Information-Rich:** Shows exactly which trains and tracks

## 🎨 Screenshots Reference

### Normal State:

- Dashboard shows normal GPS data
- No warning panel visible
- Green train control panel

### Collision State:

- Red warning panel at top
- Blinking red light
- Train details displayed
- "BUZZER ACTIVATED" message
- Alarm sound playing

### Cleared State:

- Green "All Clear" message
- Checkmark icon
- Fades out after 3 seconds
- Returns to normal

---

**System Status:** ✅ Fully Functional  
**Last Updated:** October 2025  
**Version:** 2.0 - Collision Detection Frontend

**Ready to test!** Open the dashboard and trigger a collision simulation to see it in action! 🚀
