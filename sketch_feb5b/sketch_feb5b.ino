#include <DHT.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

// ================== WIFI CONFIG ==================
const char* ssid = "Myhotspot";
const char* password = "alexander007";
const char* serverURL = "http://10.165.141.186:5005/api/update";

WiFiClient wifiClient;
HTTPClient http;

// ================== PIN DEFINITIONS ==================
#define DHT_INDOOR_PIN D4    // Indoor temp/humidity
#define DHT_OUTDOOR_PIN D2   // Outdoor temp/humidity (BACK TO D2!)
#define PIR_PIN D7           // Motion sensor
#define BUZZER_PIN D5        // Alert buzzer
#define LDR_PIN A0           // Light sensor
#define LED_PIN D0           // Light control (PWM)
#define IR1_PIN D1           // Entry sensor (BACK TO D1!)
#define IR2_PIN D6           // Exit sensor

// ================== DHT SETUP ==================
#define DHTTYPE DHT22
DHT dhtIndoor(DHT_INDOOR_PIN, DHTTYPE);
DHT dhtOutdoor(DHT_OUTDOOR_PIN, DHTTYPE);

// ================== THRESHOLDS ==================
#define TEMP_HIGH 30.0
#define HUM_HIGH 70.0
#define MAX_LDR_VALUE 150

// ================== TIMING ==================
#define INACTIVITY_TIMEOUT 60000UL      // 1 minute
#define BUZZER_INTERVAL 10000UL         // 10 seconds
#define SEND_INTERVAL 1000UL            // 1 second (High-frequency update)
#define DHT_INTERVAL 2000UL             // 2 seconds
#define DIRECTION_WINDOW 1000UL         // 1 second
#define SERIAL_UPDATE_INTERVAL 3000UL   // 3 seconds

// ================== STATE VARIABLES ==================
bool roomActive = false;
bool buzzerMuted = false;
int peopleCount = 0;

unsigned long lastMotionTime = 0;
unsigned long lastBuzzerTime = 0;
unsigned long lastSendTime = 0;
unsigned long lastDHTRead = 0;
unsigned long lastSerialUpdate = 0;
unsigned long sequenceStartTime = 0;

float indoorTemp = 0;
float indoorHum = 0;
float outdoorTemp = 0;
float outdoorHum = 0;
int ldrValue = 0;

int targetBrightness = 0;
int currentBrightness = 0;
int fadeSpeed = 5;

enum IRState {
  IDLE,
  WAIT_FOR_IR2,
  WAIT_FOR_IR1
};
IRState currentIRState = IDLE;

// ================== HELPER FUNCTIONS ==================

void beepBuzzer() {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(120);
  digitalWrite(BUZZER_PIN, LOW);
}

String getComfortStatus() {
  if (indoorTemp < 27 && indoorHum < 60) return "COMFORTABLE";
  if (indoorTemp < TEMP_HIGH && indoorHum < HUM_HIGH) return "WARNING";
  return "CRITICAL";
}

String getACStatus() {
  float delta = outdoorTemp - indoorTemp;
  
  if (delta > 8) return "EXCELLENT";
  if (delta > 5) return "GOOD";
  if (delta > 3) return "FAIR";
  return "POOR";
}

void printSerialDashboard() {
  Serial.println("\n");
  Serial.println("╔════════════════════════════════════════════════════════════╗");
  Serial.println("║           COMFORTSENSE - LIVE SYSTEM STATUS               ║");
  Serial.println("╚════════════════════════════════════════════════════════════╝");
  Serial.println();
  
  // Room Status
  Serial.println("┌─────────────────────────────────────────────────────────┐");
  Serial.println("│  ROOM STATUS                                            │");
  Serial.println("├─────────────────────────────────────────────────────────┤");
  Serial.print("│  Occupancy:      ");
  Serial.print(roomActive ? "🟢 OCCUPIED" : "⚪ VACANT");
  Serial.print("        People Count: ");
  Serial.print(peopleCount);
  for(int i = String(peopleCount).length(); i < 6; i++) Serial.print(" ");
  Serial.println("│");
  
  Serial.print("│  Lighting:       ");
  if (currentBrightness > 0) {
    int percent = map(currentBrightness, 0, 255, 0, 100);
    Serial.print("💡 ON (");
    Serial.print(percent);
    Serial.print("%)");
    if (percent < 10) Serial.print("  ");
    else if (percent < 100) Serial.print(" ");
  } else {
    Serial.print("🌙 OFF     ");
  }
  Serial.print("    LDR: ");
  Serial.print(ldrValue);
  for(int i = String(ldrValue).length(); i < 4; i++) Serial.print(" ");
  Serial.println("│");
  Serial.println("└─────────────────────────────────────────────────────────┘");
  Serial.println();
  
  // Environmental Data
  Serial.println("┌─────────────────────────────────────────────────────────┐");
  Serial.println("│  ENVIRONMENTAL CONDITIONS                               │");
  Serial.println("├─────────────────────────────────────────────────────────┤");
  Serial.print("│  🏠 INDOOR:      ");
  Serial.print(indoorTemp, 1);
  Serial.print("°C  |  ");
  Serial.print(indoorHum, 1);
  Serial.print("%  |  ");
  
  String status = getComfortStatus();
  Serial.print(status);
  for(int i = status.length(); i < 12; i++) Serial.print(" ");
  Serial.println("│");
  
  Serial.print("│  🌍 OUTDOOR:     ");
  Serial.print(outdoorTemp, 1);
  Serial.print("°C  |  ");
  Serial.print(outdoorHum, 1);
  Serial.print("%");
  for(int i = 0; i < 25; i++) Serial.print(" ");
  Serial.println("│");
  Serial.println("└─────────────────────────────────────────────────────────┘");
  Serial.println();
  
  // Analytics
  Serial.println("┌─────────────────────────────────────────────────────────┐");
  Serial.println("│  SYSTEM ANALYTICS                                       │");
  Serial.println("├─────────────────────────────────────────────────────────┤");
  
  float thermalDelta = outdoorTemp - indoorTemp;
  Serial.print("│  Thermal Delta:  ");
  Serial.print(thermalDelta, 1);
  Serial.print("°C  (");
  Serial.print(thermalDelta > 0 ? "Cooling" : "Heating");
  Serial.print(")");
  for(int i = 0; i < 20; i++) Serial.print(" ");
  Serial.println("│");
  
  Serial.print("│  AC Efficiency:  ");
  Serial.print(getACStatus());
  for(int i = getACStatus().length(); i < 42; i++) Serial.print(" ");
  Serial.println("│");
  
  Serial.print("│  Buzzer Status:  ");
  Serial.print(buzzerMuted ? "🔕 MUTED" : "🔔 ACTIVE");
  for(int i = 0; i < 38; i++) Serial.print(" ");
  Serial.println("│");
  Serial.println("└─────────────────────────────────────────────────────────┘");
  Serial.println();
  
  // Alerts
  if (status == "CRITICAL") {
    Serial.println("╔═════════════════════════════════════════════════════════╗");
    Serial.println("║  ⚠️  CRITICAL ALERT - ACTION REQUIRED                   ║");
    Serial.println("╚═════════════════════════════════════════════════════════╝");
    Serial.println();
  }
  
  // Smart Recommendations
  if (thermalDelta < 3 && outdoorTemp > 30 && roomActive) {
    Serial.println("💡 RECOMMENDATION: AC may be underperforming - check maintenance");
  }
  if (indoorTemp > outdoorTemp && outdoorTemp < 25 && roomActive) {
    Serial.println("💡 RECOMMENDATION: Outdoor is cooler - consider natural ventilation");
  }
  if (peopleCount == 0 && roomActive) {
    Serial.println("⚠️  WARNING: PIR detects motion but people count is 0");
  }
  
  Serial.println("───────────────────────────────────────────────────────────");
  Serial.print("⏰ Uptime: ");
  Serial.print(millis() / 1000);
  Serial.print("s  |  WiFi: ");
  Serial.println(WiFi.status() == WL_CONNECTED ? "✅ Connected" : "❌ Offline");
  Serial.println("═══════════════════════════════════════════════════════════\n");
}

// ================== SETUP ==================
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n");
  Serial.println("╔════════════════════════════════════════════════════════════╗");
  Serial.println("║                 COMFORTSENSE IoT SYSTEM                   ║");
  Serial.println("║                    Initializing...                        ║");
  Serial.println("╚════════════════════════════════════════════════════════════╝");
  Serial.println();

  // Pin setup
  pinMode(PIR_PIN, INPUT);
  pinMode(IR1_PIN, INPUT);
  pinMode(IR2_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);

  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  // Initialize sensors
  Serial.println("🔧 Initializing sensors...");
  dhtIndoor.begin();
  dhtOutdoor.begin();
  Serial.println("   ✅ DHT22 sensors ready");
  
  // WiFi connection
  Serial.println("🌐 Connecting to WiFi...");
  Serial.print("   SSID: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("   ✅ WiFi Connected!");
    Serial.print("   📡 IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("   ⚠️  WiFi connection failed - continuing in offline mode");
  }
  
  Serial.println();
  Serial.println("═══════════════════════════════════════════════════════════");
  Serial.println("              ✅ SYSTEM READY - Monitoring Started");
  Serial.println("═══════════════════════════════════════════════════════════");
  Serial.println();
  
  delay(2000);
}

// ================== MAIN LOOP ==================
void loop() {
  unsigned long currentTime = millis();

  // ===================================================
  // 1️⃣ LDR - ADAPTIVE BRIGHTNESS (Only if people present)
  // ===================================================
  int ldrTotal = 0;
  for(int i = 0; i < 10; i++) {
    ldrTotal += analogRead(LDR_PIN);
    delay(3);
  }
  ldrValue = ldrTotal / 10;

  // Calculate target brightness
  targetBrightness = 0;

  // ✅ LED only ON if BOTH dark AND people present
  if (peopleCount > 0 && ldrValue < MAX_LDR_VALUE) {
    // Room occupied AND dark → adaptive brightness
    targetBrightness = map(ldrValue, 0, MAX_LDR_VALUE, 255, 0);
    targetBrightness = constrain(targetBrightness, 0, 255);
  }
  // Otherwise: targetBrightness = 0 (lights OFF)

  // Smooth fade to target
  if (currentBrightness < targetBrightness) {
    currentBrightness += fadeSpeed;
    if (currentBrightness > targetBrightness) {
      currentBrightness = targetBrightness;
    }
  } else if (currentBrightness > targetBrightness) {
    currentBrightness -= fadeSpeed;
    if (currentBrightness < targetBrightness) {
      currentBrightness = targetBrightness;
    }
  }

  // Apply PWM to LED
  analogWrite(LED_PIN, currentBrightness);
  

  // Log brightness changes
  static int lastLoggedBrightness = -1;
  if (abs(currentBrightness - lastLoggedBrightness) > 15) {
    int percent = map(currentBrightness, 0, 255, 0, 100);
    Serial.print("💡 LED: ");
    Serial.print(percent);
    Serial.print("% (LDR: ");
    Serial.print(ldrValue);
    Serial.print(", People: ");
    Serial.print(peopleCount);
    Serial.println(")");
    lastLoggedBrightness = currentBrightness;
  }

  // ===================================================
  // 2️⃣ IR SENSORS - PEOPLE COUNTING
  // ===================================================
  int ir1 = digitalRead(IR1_PIN);
  int ir2 = digitalRead(IR2_PIN);

  switch (currentIRState) {
    case IDLE:
      if (ir1 == LOW) {
        currentIRState = WAIT_FOR_IR2;
        sequenceStartTime = currentTime;
      } else if (ir2 == LOW) {
        currentIRState = WAIT_FOR_IR1;
        sequenceStartTime = currentTime;
      }
      break;

    case WAIT_FOR_IR2:
      if (ir2 == LOW) {
        peopleCount++;
        Serial.print("🚶 ENTRY  →  Count: ");
        Serial.println(peopleCount);
        currentIRState = IDLE;
        delay(250);
      } else if (currentTime - sequenceStartTime > DIRECTION_WINDOW) {
        currentIRState = IDLE;
      }
      break;

    case WAIT_FOR_IR1:
      if (ir1 == LOW) {
        if (peopleCount > 0) {
          peopleCount--;
        }
        Serial.print("🚶 EXIT   →  Count: ");
        Serial.println(peopleCount);
        currentIRState = IDLE;
        delay(250);
      } else if (currentTime - sequenceStartTime > DIRECTION_WINDOW) {
        currentIRState = IDLE;
      }
      break;
  }

  // ===================================================
  // 3️⃣ PIR - MOTION DETECTION
  // ===================================================
  if (digitalRead(PIR_PIN) == HIGH) {
    lastMotionTime = currentTime;
    if (!roomActive) {
      roomActive = true;
      Serial.println("🟢 PIR → Room OCCUPIED");
    }
  }

  // Inactivity timeout
  if (peopleCount == 0 && (currentTime - lastMotionTime > INACTIVITY_TIMEOUT)) {
    if (roomActive) {
      roomActive = false;
      Serial.println("⚪ Room VACANT - Systems OFF");
    }
  }

  // ===================================================
  // 4️⃣ DHT22 - TEMPERATURE & HUMIDITY
  // ===================================================
  if (currentTime - lastDHTRead >= DHT_INTERVAL) {
    float tempIn = dhtIndoor.readTemperature();
    float humIn = dhtIndoor.readHumidity();
    float tempOut = dhtOutdoor.readTemperature();
    float humOut = dhtOutdoor.readHumidity();

    if (!isnan(tempIn) && !isnan(humIn) && !isnan(tempOut) && !isnan(humOut)) {
      indoorTemp = tempIn;
      indoorHum = humIn;
      outdoorTemp = tempOut;
      outdoorHum = humOut;

      // Buzzer alert for high humidity
      if (indoorHum >= HUM_HIGH && !buzzerMuted && roomActive) {
        if (currentTime - lastBuzzerTime >= BUZZER_INTERVAL) {
          Serial.println("🚨 HIGH HUMIDITY ALERT");
          beepBuzzer();
          lastBuzzerTime = currentTime;
        }
      }

      // Reset mute if conditions normalize
      if (indoorHum < HUM_HIGH) {
        buzzerMuted = false;
      }
    }

    lastDHTRead = currentTime;
  }

  // ===================================================
  // 5️⃣ SERIAL DASHBOARD
  // ===================================================
  if (currentTime - lastSerialUpdate >= SERIAL_UPDATE_INTERVAL) {
    printSerialDashboard();
    lastSerialUpdate = currentTime;
  }

  // ===================================================
  // 6️⃣ SEND TO FLASK (Uncomment when ready)
  // ===================================================

  if (currentTime - lastSendTime >= SEND_INTERVAL) {
    if (WiFi.status() == WL_CONNECTED) {
      String payload = "{";
      payload += "\"indoor_temp\":" + String(indoorTemp, 1) + ",";
      payload += "\"indoor_hum\":" + String(indoorHum, 1) + ",";
      payload += "\"outdoor_temp\":" + String(outdoorTemp, 1) + ",";
      payload += "\"outdoor_hum\":" + String(outdoorHum, 1) + ",";
      payload += "\"light\":" + String(ldrValue) + ",";
      payload += "\"brightness\":" + String(map(currentBrightness, 0, 255, 0, 100)) + ",";
      payload += "\"motion\":" + String(roomActive ? 1 : 0) + ",";
      payload += "\"people\":" + String(peopleCount) + ",";
      payload += "\"occupancy\":\"" + String(roomActive ? "occupied" : "vacant") + "\"";
      payload += "}";

      http.begin(wifiClient, serverURL);
      http.addHeader("Content-Type", "application/json");
      int httpCode = http.POST(payload);
      
      if (httpCode > 0) {
        Serial.printf("📡 Flask: %d\n", httpCode);
      }
      
      http.end();
    }
    lastSendTime = currentTime;
  }


  delay(10);
}
