
import requests
import time
import random

API_URL = "http://localhost:5005/api/update"

# Arduino Constants
INACTIVITY_TIMEOUT_SEC = 60
CYCLE_DELAY = 1  # Standard delay

# State
room_active = False
last_motion_time = 0
last_buzzer_time = 0
buzzer_muted = False
people_in_room = 0  # Internal state for simulation logic, NOT sent in payload

# Thresholds
HUM_HIGH = 70.0


def simulate_sensor_data():
    global room_active, last_motion_time, people_in_room, buzzer_muted, last_buzzer_time
    
    cycle = 0
    print("🚀 Starting Arduino-accurate simulator...")
    print("   Payload: temp, hum, light, motion, occupancy")
    print("   Note: people_count is NOT sent (backend estimates it)")

    while True:
        cycle += 1
        now = time.time()
        
        # 1. Simulate Motion (PIR)
        # Randomly trigger motion if "people" are present
        if people_in_room > 0:
            if random.random() < 0.3:  # 30% chance of motion each cycle
                last_motion_time = now
                if not room_active:
                    room_active = True
                    print("\n>>> ROOM OCCUPIED (Motion Detected)")
        else:
            # 5% chance of "phantom" motion to test Suspicious Activity logic
            if random.random() < 0.05:
                last_motion_time = now
                print("\n>>> 🚨 SUSPICIOUS MOTION (PIR triggered in empty room)")

        # 2. Check Inactivity
        if room_active and (now - last_motion_time > INACTIVITY_TIMEOUT_SEC):
            room_active = False
            print("\n>>> ROOM VACANT (Timeout)")
            
        # 3. Simulate Sensor Readings
        # LDR is always read
        light = random.randint(200, 900)
        
        if room_active:
            # Simulate environment changes
            base_temp = 24.0 + (people_in_room * 0.5)
            base_hum = 45.0 + (people_in_room * 2.0)
            
            temperature = round(random.uniform(base_temp - 1, base_temp + 1), 1)
            humidity = round(random.uniform(base_hum - 5, base_hum + 5), 1)
            occupancy = "occupied"
            
            # Simulate Humidity Alert
            if humidity >= HUM_HIGH:
                user_msg = "🚨 HIGH HUMIDITY!"
                if not buzzer_muted and (now - last_buzzer_time > 10):
                    user_msg += " [BEEP!]"
                    last_buzzer_time = now
            else:
                buzzer_muted = False
                
        else:
            # Vacant state logic from Arduino:
            # Temp/Hum are 0 in payload, but LDR is sent
            temperature = 0
            humidity = 0
            occupancy_state_for_print = "vacant" # For print statement

        # 4. Generate Payload (Exactly matching Arduino)
        # Note: 'motion' field is actually roomActive state (1/0)
        payload = {
            'indoor_temp': temperature,
            'indoor_hum': humidity,
            'outdoor_temp': round(temperature + random.uniform(2, 10), 1), # Usually hotter outside
            'outdoor_hum': round(humidity + random.uniform(-10, 10), 1),
            'light': light,
            'motion': 1 if now - last_motion_time < 30 else 0, # Room active for 30s after motion
            'people': people_in_room,
            'occupancy': 'occupied' if people_in_room > 0 else 'vacant'
        }
        # 5. Send to API
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                print(f"✅ Data sent: T={temperature} H={humidity} L={light} Occ={payload['occupancy']}")
            else:
                print(f"❌ Error: {response.text}")
        except Exception as e:
            print(f"❌ Connection failed: {e}")

        # 6. Simulate People Entry/Exit (External Events)
        if cycle % 10 == 0:
            change = random.choice([0, 0, 0, 1, -1])  # Mostly no change
            if change == 1 and people_in_room < 8:
                people_in_room += 1
                # Trigger motion immediately on entry
                last_motion_time = now 
                room_active = True 
                print(f"👤 Person ENTERED. Total: {people_in_room}")
            elif change == -1 and people_in_room > 0:
                people_in_room -= 1
                if people_in_room > 0:
                    last_motion_time = now # Remaining people still move
                print(f"👤 Person EXITED. Total: {people_in_room}")

        time.sleep(CYCLE_DELAY)

if __name__ == "__main__":
    simulate_sensor_data()
