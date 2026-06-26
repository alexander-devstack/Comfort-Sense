# 🚨 Sensor Alert Thresholds

This document lists the threshold values for all sensors in the **ComfortSense Smart Office IoT** system. When a reading crosses these thresholds, the system triggers visual and/or audible alerts.

---

## 🌡️ Temperature (DHT22)

| Condition       | Range              | Status Indicator | Alert Action         |
|-----------------|--------------------|------------------|----------------------|
| Cool            | Below 20 °C        | 🟡 Moderate      | Dashboard warning    |
| **Comfortable** | **20 °C – 27 °C**  | 🟢 Good          | None (normal)        |
| Warm            | 27 °C – 30 °C      | 🟡 Moderate      | Dashboard warning    |
| **Too Hot!**    | **≥ 30 °C**        | 🔴 Bad           | Dashboard alert, RGB LED turns **RED** |

> **Hardware threshold** (`TEMP_HIGH`): **30.0 °C** — defined in the ESP8266 firmware.

---

## 💧 Humidity (DHT22)

| Condition       | Range              | Status Indicator | Alert Action         |
|-----------------|--------------------|------------------|----------------------|
| Dry             | Below 40 %         | 🟡 Moderate      | Dashboard warning    |
| **Optimal**     | **40 % – 60 %**    | 🟢 Good          | None (normal)        |
| High            | 60 % – 70 %        | 🟡 Moderate      | Dashboard warning    |
| **Too Humid!**  | **≥ 70 %**         | 🔴 Bad           | Dashboard alert, RGB LED turns **RED**, **Buzzer beeps** every 10 s |

> **Hardware threshold** (`HUM_HIGH`): **70.0 %** — defined in the ESP8266 firmware.  
> The buzzer sounds once every **10 seconds** (`BUZZER_INTERVAL`) while humidity stays above 70 %.

---

## 💡 Light Level (LDR – Analog 0–1024)

| Condition            | Range        | Status Indicator | Alert Action      |
|----------------------|--------------|------------------|-------------------|
| Low Light            | Below 500    | 🟡 Moderate      | Dashboard notice  |
| **Adequate Light**   | **≥ 500**    | 🟢 Good          | None (normal)     |

> **Dashboard threshold** (`LIGHT_ARTIFICIAL`): **500** — defined in the frontend JS config.

---

## 🚶 Motion / Occupancy (PIR Sensor)

| State              | Trigger                          | Alert Action                          |
|--------------------|----------------------------------|---------------------------------------|
| **Motion Detected**| PIR pin reads HIGH               | Room marked **Occupied**, sensors activate |
| **No Motion**      | No motion for **60 seconds**     | Room marked **Vacant**, RGB LED off, buzzer off |

> **Inactivity timeout** (`INACTIVITY_TIMEOUT`): **60 000 ms (1 minute)** — defined in the ESP8266 firmware.

---

## 🚦 RGB LED Summary (Common Anode)

The RGB LED on the hardware provides an at-a-glance comfort indicator:

| LED Colour | Condition                                      |
|------------|-------------------------------------------------|
| 🟢 Green   | Temperature < 27 °C **and** Humidity < 60 %    |
| 🟡 Yellow  | Temperature < 30 °C **and** Humidity < 70 %    |
| 🔴 Red     | Temperature ≥ 30 °C **or** Humidity ≥ 70 %     |
| ⚫ Off     | Room is vacant (no motion for 1 minute)         |

---

## 📂 Where Thresholds Are Defined

| Source File | Constants |
|-------------|-----------|
| `sketch_feb5b/sketch_feb5b.ino` | `TEMP_HIGH` (30 °C), `HUM_HIGH` (70 %), `INACTIVITY_TIMEOUT` (60 s), `BUZZER_INTERVAL` (10 s) |
| `static/js/app.js` | `TEMP_COMFORT_MIN` (20), `TEMP_COMFORT_MAX` (27), `TEMP_WARNING` (30), `HUM_COMFORT_MIN` (40), `HUM_COMFORT_MAX` (60), `HUM_WARNING` (70), `LIGHT_ARTIFICIAL` (500) |
