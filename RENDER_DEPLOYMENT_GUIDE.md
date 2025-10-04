# 🎨 Render.com Deployment Guide for GPS Tracker API

## ✅ Why Render.com?

- 🆓 **FREE FOREVER** (750 hours/month = 24/7 operation)
- ⚡ Easy deployment (5 minutes setup)
- 🔒 Free HTTPS/SSL
- 🔄 Auto-deploy from GitHub
- 📊 Your ESP32 sends data every 15 seconds → app stays awake!

---

## 📋 Prerequisites

- [x] GitHub account
- [x] Render.com account (sign up at https://render.com)
- [x] Git installed

---

## 🚀 Step-by-Step Deployment

### **Step 1: Push Your Code to GitHub**

#### 1.1 Initialize Git (if not done):

```bash
cd "G:\COTTG company\GA\backend"
git init
```

#### 1.2 Add files to Git:

```bash
git add .
git commit -m "Prepare for Render.com deployment"
```

#### 1.3 Create GitHub repository:

- Go to: https://github.com/new
- Repository name: `gps-tracker-backend`
- Keep it **Public** (required for free tier)
- Don't initialize with README
- Click "Create repository"

#### 1.4 Push to GitHub:

```bash
git remote add origin https://github.com/YOUR_USERNAME/gps-tracker-backend.git
git branch -M main
git push -u origin main
```

---

### **Step 2: Deploy on Render.com**

#### 2.1 Sign Up:

- Go to: https://render.com
- Click "Get Started for Free"
- Sign up with **GitHub** (easiest option)

#### 2.2 Create New Web Service:

1. Click "New +" button (top right)
2. Select "Web Service"
3. Click "Connect account" to connect GitHub
4. Find and select your repository: `gps-tracker-backend`
5. Click "Connect"

#### 2.3 Configure Service:

Fill in these details:

| Field              | Value                                            |
| ------------------ | ------------------------------------------------ |
| **Name**           | `gps-tracker-api` (or any name you like)         |
| **Region**         | Choose closest to you (e.g., Singapore, Oregon)  |
| **Branch**         | `main`                                           |
| **Root Directory** | Leave blank                                      |
| **Runtime**        | `Python 3`                                       |
| **Build Command**  | `pip install -r requirements.txt`                |
| **Start Command**  | `uvicorn server:app --host 0.0.0.0 --port $PORT` |

#### 2.4 Select Plan:

- Scroll down to "Instance Type"
- Select **"Free"** plan
- ⚠️ Note: "Service will spin down with inactivity" (Your ESP32 keeps it awake!)

#### 2.5 Advanced Settings (Optional but Recommended):

- Click "Advanced" button
- Add environment variable (if needed):
  - Key: `PYTHON_VERSION`
  - Value: `3.9.0`

#### 2.6 Deploy:

- Click **"Create Web Service"** button
- Wait 3-5 minutes for deployment
- Watch the logs for progress

---

### **Step 3: Get Your Render.com URL**

After deployment completes:

1. You'll see: "✅ Live" with a green indicator
2. Your URL will be at the top: `https://gps-tracker-api.onrender.com`
3. Copy this URL!

---

### **Step 4: Test Your Deployment**

Open these URLs in your browser:

1. **Health Check:**

   ```
   https://gps-tracker-api.onrender.com/health
   ```

   Should show: `{"status": "OK", "message": "GPS Tracker API is running"}`

2. **Dashboard:**

   ```
   https://gps-tracker-api.onrender.com/dashboard
   ```

   Your dashboard should load!

3. **API Endpoint (for ESP32):**
   ```
   https://gps-tracker-api.onrender.com/api/gps
   ```

---

### **Step 5: Update ESP32 Arduino Code**

Now update your ESP32 to send data to Render.com:

#### 5.1 Open `sketch_sep28a.ino`

#### 5.2 Change line 15:

```cpp
// OLD (local network):
const char* mongoAPIEndpoint = "http://172.20.10.5:8000/api/gps";

// NEW (Render.com):
const char* mongoAPIEndpoint = "https://gps-tracker-api.onrender.com/api/gps";
//                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
//                              Use YOUR actual Render.com URL here!
```

#### 5.3 Update WiFi (if needed):

```cpp
// Lines 7-8: You can now use ANY WiFi network!
const char* ssid     = "Your_WiFi_Name";
const char* password = "Your_WiFi_Password";
```

#### 5.4 Upload to ESP32:

- Connect ESP32 to computer
- Upload the updated code
- Open Serial Monitor (115200 baud)
- Verify it connects and sends data

---

## 🎯 Important URLs (Save These!)

After deployment, you have:

| Purpose                  | URL                                           |
| ------------------------ | --------------------------------------------- |
| **Dashboard**            | `https://YOUR-APP.onrender.com/dashboard`     |
| **API Health**           | `https://YOUR-APP.onrender.com/health`        |
| **GPS Endpoint** (ESP32) | `https://YOUR-APP.onrender.com/api/gps`       |
| **Get GPS Data**         | `https://YOUR-APP.onrender.com/api/gps` (GET) |

---

## 📱 Complete System Test

1. ✅ **Backend deployed** on Render.com
2. ✅ **Dashboard accessible** via browser
3. ✅ **ESP32 updated** with Render URL
4. ✅ **ESP32 connects** to WiFi
5. ✅ **ESP32 sends** GPS data to Render
6. ✅ **Dashboard shows** real-time data
7. ✅ **MongoDB stores** all data

---

## 🔄 Updating Your App

When you make changes to your code:

```bash
git add .
git commit -m "Description of changes"
git push origin main
```

Render will **automatically redeploy** (takes 2-3 minutes)!

---

## ⚠️ Important: "Sleeping" Behavior

### What is it?

- Free tier apps "sleep" after **15 minutes** of inactivity
- First request after sleeping takes **~50 seconds** to wake up

### Will YOUR app sleep?

**NO!** Because:

- ✅ Your ESP32 sends data **every 15 seconds**
- ✅ This keeps the app **always awake**
- ✅ Dashboard always loads instantly

### If you want to GUARANTEE it never sleeps:

**Option A:** Keep ESP32 running (recommended)
**Option B:** Use a monitoring service (like UptimeRobot) to ping every 10 minutes
**Option C:** Upgrade to paid plan ($7/month) - no sleeping

---

## 💰 Render.com Pricing

| Plan        | Price     | Features                                                                                         |
| ----------- | --------- | ------------------------------------------------------------------------------------------------ |
| **Free**    | $0/month  | ✅ 750 hours/month (enough for 24/7!)<br>⚠️ Sleeps after 15 min inactivity<br>✅ 100GB bandwidth |
| **Starter** | $7/month  | ✅ Never sleeps<br>✅ 512MB RAM<br>✅ More bandwidth                                             |
| **Pro**     | $25/month | ✅ 2GB RAM<br>✅ Priority support                                                                |

**For your GPS tracker:** Free plan is PERFECT! ✅

---

## 🛠️ Troubleshooting

### Problem 1: Build Failed

**Solution:**

- Check Render logs (in deployment tab)
- Verify `requirements.txt` has all dependencies
- Make sure repository is public (free tier requirement)

### Problem 2: App Crashes on Start

**Solution:**

- Check Render logs for errors
- Verify MongoDB connection string is correct
- Make sure `PORT` environment variable is used in code ✅ (already done)

### Problem 3: ESP32 Can't Connect

**Solution:**

- Verify Render URL is correct (must be HTTPS, not HTTP)
- Check ESP32 WiFi is connected
- View ESP32 Serial Monitor for error messages
- Test URL in browser first

### Problem 4: CORS Errors

**Solution:** Already configured! ✅

```python
allow_origins=["*"]  # In server.py
```

### Problem 5: App is Sleeping

**Solution:**

- Your ESP32 should keep it awake
- If needed, use UptimeRobot (free service) to ping every 10 minutes
- Or upgrade to Starter plan ($7/month)

---

## 🌟 Benefits of Render.com

✅ **FREE forever** (not a trial!)
✅ **Easy setup** (5 minutes)
✅ **HTTPS included** (secure)
✅ **Auto-deploy** from GitHub
✅ **Global CDN** (fast everywhere)
✅ **Zero maintenance** (no server management)
✅ **Perfect for ESP32** GPS tracker
✅ **Great documentation** and support

---

## 📊 Monitoring Your App

### View Logs:

1. Go to Render dashboard
2. Click on your service
3. Click "Logs" tab
4. See real-time logs (GPS data being received!)

### View Metrics:

1. Click "Metrics" tab
2. See CPU, memory, bandwidth usage
3. Monitor uptime

### View Events:

1. Click "Events" tab
2. See deployments, restarts, etc.

---

## 🎉 You're Done!

Your GPS tracking system is now:

- ✅ **Hosted for FREE** on Render.com
- ✅ **Accessible from anywhere** in the world
- ✅ **Works with ANY WiFi** network (ESP32 and dashboard don't need same WiFi!)
- ✅ **Secure HTTPS** connections
- ✅ **Auto-updates** when you push to GitHub

---

## 🆘 Need Help?

- **Render Docs:** https://render.com/docs
- **Render Community:** https://community.render.com
- **Render Status:** https://status.render.com

---

## 📝 Quick Checklist

- [ ] Code pushed to GitHub
- [ ] Render.com account created
- [ ] Web service deployed
- [ ] Deployment successful (green "Live" status)
- [ ] Health check URL works
- [ ] Dashboard loads in browser
- [ ] ESP32 code updated with Render URL
- [ ] ESP32 connects to WiFi
- [ ] ESP32 sends data successfully
- [ ] Data appears in dashboard

---

**🚀 Your GPS tracker is now live on the internet! Enjoy your FREE hosting!**
