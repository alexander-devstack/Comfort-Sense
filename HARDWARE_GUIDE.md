# Hardware Integration Guide

## ESP8266 + Smart Office IoT Dashboard

This guide will help you connect your ESP8266 sensors to the Flask dashboard.

---

## 🔌 Hardware Requirements

| Component                  | Purpose                | Pin        |
| -------------------------- | ---------------------- | ---------- |
| ESP8266 (NodeMCU/Wemos D1) | WiFi microcontroller   | -          |
| DHT22                      | Temperature & Humidity | D4         |
| PIR Motion Sensor          | Motion detection       | D7         |
| LDR (Light Sensor)         | Light level            | A0         |
| RGB LED (Common Anode)     | Status indicator       | D1, D2, D6 |
| Buzzer                     | Alerts                 | D5         |

---

## 📐 Wiring Diagram

```
ESP8266 NodeMCU
┌─────────────────┐
│                 │
│ D4  ──────────► DHT22 Data
│ D7  ◄────────── PIR OUT
│ A0  ◄────────── LDR (with 10K resistor divider)
│ D1  ──────────► RGB Red
│ D2  ──────────► RGB Green
│ D6  ──────────► RGB Blue
│ D5  ──────────► Buzzer +
│ 3V3 ──────────► DHT22 VCC, PIR VCC
│ GND ──────────► Common Ground
│                 │
└─────────────────┘
```

---

## 🖥️ Step-by-Step Setup

### Step 1: Find Your Computer's IP Address

Open **PowerShell** and run:

```powershell
ipconfig
```

Look for `IPv4 Address` under your WiFi adapter:

```
Wireless LAN adapter Wi-Fi:
   IPv4 Address. . . . . . . . : 192.168.1.100  ← Use this!
```

---

### Step 2: Update Arduino Code

In your Arduino sketch, update these lines:

```cpp
// WiFi credentials
const char* ssid = "YourWiFiName";        // ← Your WiFi name
const char* password = "YourWiFiPassword"; // ← Your WiFi password

// Server URL - use your computer's IP!
const char* serverURL = "http://10.165.141.186:5005/api/update";
//                             ^^^^^^^^^^^^^^^
//                             Your computer's IP
```

> ⚠️ **Important**: Both the ESP8266 and your computer must be on the **same WiFi network**!

---

### Step 3: Start the Flask Server

Open **PowerShell** in the project folder and run:

```powershell
cd "d:\Personal Projects\Smart IoT for offices"
python app.py
```

You should see:

```
==================================================
🏢 SMART OFFICE IoT DASHBOARD
==================================================
📡 Server running on http://0.0.0.0:5000
🌐 Dashboard: http://localhost:5000
📥 ESP8266 endpoint: http://<your-ip>:5000/api/update
==================================================
```

---

### Step 4: Upload Arduino Code

1. Open Arduino IDE
2. Select your ESP8266 board:
   - **Tools → Board → ESP8266 Boards → NodeMCU 1.0**
3. Select the correct COM port:
   - **Tools → Port → COM X**
4. Click **Upload**

---

### Step 5: Monitor Serial Output

Open **Serial Monitor** (115200 baud) to see:

```
=== SMART OFFICE SYSTEM ===
🌐 Connecting to WiFi...
✅ WiFi Connected!
📡 ESP IP: 192.168.1.150
🖥️  Server: http://192.168.1.100:5000/api/update
=== SYSTEM READY ===

🌡️ 26.5°C | 💧 55.2% | 💡 650 (Natural)
✅ Sent: {"temp":26.5,"hum":55.2,"light":650,"motion":1,"occupancy":"occupied"}
📥 Response: {"status":"success"...}
```

---

### Step 6: View Dashboard

Open your browser and go to:

```
http://localhost:5005
```

You should see real-time data updating every second!

---

## 🔧 Troubleshooting

### ESP8266 Can't Connect to WiFi

- Check SSID and password (case-sensitive!)
- Move ESP8266 closer to router
- Check if 2.4GHz WiFi (ESP8266 doesn't support 5GHz)

### ESP8266 Can't Reach Server

- Verify computer IP address is correct
- Check both devices are on same network
- Ensure Windows Firewall allows Python on port 5000
- Run this in PowerShell (as Admin):
  ```powershell
  netsh advfirewall firewall add rule name="Flask IoT" dir=in action=allow protocol=TCP localport=5000
  ```

### Dashboard Shows "--" Values

- Check ESP8266 is sending data (Serial Monitor)
- Verify Flask server is running
- Check browser console (F12) for errors

### DHT22 Reading "nan"

- Check wiring connections
- Add 10K pull-up resistor between Data and VCC
- Wait 2 seconds between readings (sensor limitation)

---

## 📊 Data Export

Click the **"Export CSV"** button on the dashboard to download all sensor readings. The CSV includes:

- Timestamp
- Temperature (°C)
- Humidity (%)
- Light Level
- Motion Status
- Occupancy Status

---

## 🌐 Making it Accessible Externally (Optional)

To access the dashboard from your phone or other devices:

1. Use your computer's local IP instead of localhost:

   ```
   http://192.168.1.100:5005
   ```

2. For internet access, consider:
   - **ngrok**: `ngrok http 5005`
   - Port forwarding on your router
   - Deploying to a cloud service

---

## 📁 Project Files

```
Smart IoT for offices/
├── app.py              # Flask backend
├── requirements.txt    # Python dependencies
├── sensor_data.db      # SQLite database (auto-created)
├── templates/
│   └── index.html      # Dashboard HTML
├── static/
│   ├── css/
│   │   └── style.css   # Dashboard styling
│   └── js/
│       └── app.js      # Real-time updates
└── sketch_feb5b/
    └── sketch_feb5b.ino # Arduino code
```
