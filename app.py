from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os
import csv
import io
import time

app = Flask(__name__)
CORS(app)

DATABASE = 'sensor_data.db'

# ==========================================
# Server-side state for computed features
# ==========================================
server_state = {
    'led_on_seconds': 0,
    'total_energy_cost': (0.0, 0.0),
    'last_update_time': None,
    'suspicious_activity': False,
    'comfort_score': 100,
    'people_count': 0,
    'session_start': None,
    'comfort_breakdown': {
        'temp_score': 100,
        'hum_score': 100,
        'indoor_temp': 0,
        'indoor_hum': 0
    },
    # Match Arduino RGB LED logic
    'rgb_status': 'off',       # off, green, yellow, red
    'buzzer_active': False,     # mirrors Arduino buzzer alert state
    # People estimation state
    'occupied_streak': 0,       # consecutive occupied readings
    'vacant_streak': 0,         # consecutive vacant readings
    'last_reading': None,       # For stale data detection
    'stale_count': 0
}

# Indian electricity tariff constants
ELECTRICITY_RATE = 6.50        # ₹ per kWh
LED_WATTAGE = 10               # Watts (typical office LED)
IDEAL_TEMP = 25.0              # Ideal reference temperature °C
IDEAL_HUM = 50.0               # Ideal reference humidity %

# Arduino thresholds (mirrored from sketch)
ARDUINO_TEMP_HIGH = 30.0
ARDUINO_HUM_HIGH = 70.0
ARDUINO_TEMP_COMFORT = 27.0
ARDUINO_HUM_COMFORT = 60.0
ARDUINO_LDR_THRESHOLD = 500


def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with required tables"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            temperature REAL,
            humidity REAL,
            light INTEGER,
            motion INTEGER,
            occupancy TEXT,
            people_count INTEGER DEFAULT 0,
            outdoor_temp REAL DEFAULT 0,
            outdoor_hum REAL DEFAULT 0
        )
    ''')
    # Lazy migration: Add outdoor columns if they don't exist
    try:
        cursor.execute("ALTER TABLE sensor_readings ADD COLUMN outdoor_temp REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE sensor_readings ADD COLUMN outdoor_hum REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
    print("✅ Database initialized!")


# Initialize database on startup
with app.app_context():
    init_db()
    server_state['session_start'] = time.time()
    server_state['last_update_time'] = time.time()


def compute_comfort_score(temp, hum):
    """Compute comfort score (0-100) based on deviation from ideal conditions"""
    if temp == 0 and hum == 0:
        return 100, 100, 100  # No data, assume comfortable

    # Temperature score: ideal is 25°C, penalty for deviation
    temp_deviation = abs(temp - IDEAL_TEMP)
    temp_score = max(0, 100 - (temp_deviation * 5))

    # Humidity score: ideal is 50%, penalty for deviation
    hum_deviation = abs(hum - IDEAL_HUM)
    hum_score = max(0, 100 - (hum_deviation * 3))

    # Combined weighted score
    overall = round(temp_score * 0.5 + hum_score * 0.5, 1)
    return overall, round(temp_score, 1), round(hum_score, 1)


def compute_energy_cost(seconds):
    """Compute energy cost for given LED-on seconds"""
    energy_kwh = (LED_WATTAGE * seconds) / (3600 * 1000)
    cost = energy_kwh * ELECTRICITY_RATE
    return round(energy_kwh, 6), round(cost, 4)


def compute_rgb_status(temp, hum, occupied):
    """
    Mirror Arduino RGB LED logic exactly:
    - OFF when vacant (rgbOff)
    - GREEN when temp < 27 AND hum < 60
    - YELLOW when temp < 30 AND hum < 70
    - RED otherwise
    """
    if not occupied:
        return 'off'
    if temp < ARDUINO_TEMP_COMFORT and hum < ARDUINO_HUM_COMFORT:
        return 'green'
    elif temp < ARDUINO_TEMP_HIGH and hum < ARDUINO_HUM_HIGH:
        return 'yellow'
    else:
        return 'red'


def estimate_people_count(occupancy, motion, current_count):
    """
    Estimate people count from sustained occupancy patterns.
    Arduino uses PIR + 60s inactivity timeout -> roomActive.
    The 'motion' field from Arduino is actually roomActive (1=occupied, 0=vacant).
    
    Logic:
    - When occupied, gradually increase count based on sustained presence
    - When vacant, immediately set to 0
    - Cap at reasonable maximum
    """
    if occupancy == 'vacant':
        server_state['occupied_streak'] = 0
        server_state['vacant_streak'] += 1
        return 0

    # Room is occupied
    server_state['vacant_streak'] = 0
    server_state['occupied_streak'] += 1

    # Start with 1 person when first occupied
    if current_count == 0:
        return 1

    # After sustained occupancy (every ~30 readings ≈ 30 seconds at 1s interval),
    # there's a chance more people are present
    if server_state['occupied_streak'] % 30 == 0 and current_count < 8:
        return current_count + 1

    return current_count


@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('index.html')


@app.before_request
def log_request_info():
    print(f"\n📥 [RECEPTION] {request.method} {request.path}")
    print(f"📡 Remote Addr: {request.remote_addr}")
    if request.path.startswith('/api'):
        print(f"📦 Content-type: {request.content_type}")
        if request.data:
            try:
                print(f"📝 Body: {request.data.decode('utf-8')[:200]}")
            except:
                print(f"📝 Body (raw): {request.data[:200]}")

@app.route('/api/ping', methods=['GET'])
def ping():
    """Simple connectivity test"""
    print(f"🔔 PING received from {request.remote_addr}")
    return jsonify({
        'status': 'online', 
        'timestamp': datetime.now().isoformat(),
        'server_ip': '10.165.141.186',
        'port': 5005
    }), 200

@app.route('/api/update', methods=['POST'])
def update_sensor_data():
    """Receive sensor data from ESP8266/Simulator"""
    client_ip = request.remote_addr
    is_local = (client_ip == '127.0.0.1' or client_ip == 'localhost')
    source_label = "💻 [LOCAL SIMULATOR]" if is_local else f"📡 [HARDWARE REMOTE: {client_ip}]"
    
    print(f"{source_label} triggered route /api/update")
    try:
        data = request.get_json()
        print(f"📦 Payload Keys: {list(data.keys()) if data else 'EMPTY'}")

        if not data:
            print("⚠️ ERROR: No JSON received. Possible issues:")
            print("   1. Missing Content-Type: application/json header")
            print("   2. Malformed JSON body")
            print(f"   Raw body was: {request.data}")
            return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400

        # Extract values
        temperature = data.get('indoor_temp', data.get('temp', 0))
        humidity = data.get('indoor_hum', data.get('hum', 0))
        outdoor_temp = data.get('outdoor_temp', 0)
        outdoor_hum = data.get('outdoor_hum', 0)
        light = data.get('light', 0)
        motion = data.get('motion', 0)
        occupancy = data.get('occupancy', 'unknown')
        people_count_raw = data.get('people', data.get('people_count', None))

        # Stale Data Detection
        current_reading = (temperature, humidity, light)
        if server_state['last_reading'] == current_reading:
            server_state['stale_count'] += 1
        else:
            server_state['last_reading'] = current_reading
            server_state['stale_count'] = 0
        
        stale_alert = f" [⚠️ STALE DATA x{server_state['stale_count']}]" if server_state['stale_count'] >= 5 else ""

        # Time tracking
        now = time.time()
        
        # Calculate elapsed time for energy cost calculation
        elapsed = now - server_state['last_update_time'] if server_state['last_update_time'] else 1

        # People count & occupancy logic
        if people_count_raw is not None:
            server_state['people_count'] = int(people_count_raw)
        else:
            server_state['people_count'] = estimate_people_count(
                occupancy, motion, server_state['people_count']
            )

        # Software override: occupied ONLY if people count > 0
        if server_state['people_count'] > 0:
            occupancy = 'occupied'
        else:
            occupancy = 'vacant'
        
        is_occupied = (occupancy == 'occupied')

        # Store in database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sensor_readings (temperature, humidity, light, motion, occupancy, people_count, outdoor_temp, outdoor_hum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (temperature, humidity, light, motion, occupancy, server_state['people_count'], outdoor_temp, outdoor_hum))
        conn.commit()
        conn.close()

        # Energy cost: accumulate only when room is occupied (Arduino RGB LED is ON)
        if is_occupied:
            server_state['led_on_seconds'] += elapsed

        server_state['total_energy_cost'] = compute_energy_cost(server_state['led_on_seconds'])

        # Comfort score (uses DHT readings)
        overall, temp_score, hum_score = compute_comfort_score(temperature, humidity)
        server_state['comfort_score'] = overall
        server_state['comfort_breakdown'] = {
            'temp_score': temp_score,
            'hum_score': hum_score,
            'indoor_temp': temperature,
            'indoor_hum': humidity,
            'ref_temp': IDEAL_TEMP,
            'ref_hum': IDEAL_HUM
        }

        # RGB LED status (mirror Arduino logic exactly)
        server_state['rgb_status'] = compute_rgb_status(temperature, humidity, is_occupied)

        # Buzzer alert status (mirrors Arduino: hum >= 70% while occupied)
        server_state['buzzer_active'] = (is_occupied and humidity >= ARDUINO_HUM_HIGH)

        # Suspicious activity: 
        # Requirement: Alert if PIR senses motion without any people in the room
        server_state['suspicious_activity'] = (
            motion == 1 and server_state['people_count'] == 0
        )

        server_state['last_update_time'] = now

        rgb = server_state['rgb_status']
        buzzer = "🔊" if server_state['buzzer_active'] else "🔇"
        suspicious = "🚨" if server_state['suspicious_activity'] else ""
        print(f"📥 T={temperature}°C H={humidity}% L={light} "
              f"Occ={occupancy} People={server_state['people_count']} "
              f"RGB={rgb} {buzzer} Comfort={overall}% {suspicious}{stale_alert}")

        return jsonify({
            'status': 'success',
            'message': 'Data stored successfully',
            'data': {
                'temperature': temperature,
                'humidity': humidity,
                'light': light,
                'motion': motion,
                'occupancy': occupancy,
                'people_count': server_state['people_count'],
                'outdoor_temp': outdoor_temp,
                'outdoor_hum': outdoor_hum
            }
        }), 200

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/data', methods=['GET'])
@app.route('/api/api/data', methods=['GET']) # Fallback for cached frontend issues
def get_latest_data():
    """Get the latest sensor reading with computed features"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM sensor_readings 
            ORDER BY id DESC LIMIT 1
        ''')
        row = cursor.fetchone()
        conn.close()

        if row:
            energy_kwh, energy_cost = server_state['total_energy_cost']
            uptime_seconds = time.time() - server_state['session_start']

            return jsonify({
                'status': 'success',
                'data': {
                    'id': row['id'],
                    'timestamp': row['timestamp'],
                    'temperature': row['temperature'],
                    'humidity': row['humidity'],
                    'light': row['light'],
                    'motion': row['motion'],
                    'occupancy': row['occupancy'],
                    'people_count': server_state['people_count'],
                    'outdoor_temp': row['outdoor_temp'],
                    'outdoor_hum': row['outdoor_hum'],
                    'comfort_score': server_state['comfort_score'],
                    'comfort_breakdown': server_state['comfort_breakdown'],
                    'suspicious_activity': server_state['suspicious_activity'],
                    # Arduino hardware status (mirrored)
                    'rgb_status': server_state['rgb_status'],
                    'buzzer_active': server_state['buzzer_active'],
                    'ldr_threshold': ARDUINO_LDR_THRESHOLD,
                    'energy': {
                        'led_on_seconds': round(server_state['led_on_seconds'], 1),
                        'energy_kwh': energy_kwh,
                        'cost_inr': energy_cost,
                        'wattage': LED_WATTAGE,
                        'rate_per_kwh': ELECTRICITY_RATE
                    },
                    'uptime_seconds': round(uptime_seconds, 0)
                }
            }), 200
        else:
            return jsonify({
                'status': 'success',
                'data': None,
                'message': 'No data available yet'
            }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/history', methods=['GET'])
@app.route('/api/api/history', methods=['GET']) # Fallback
def get_history():
    """Get historical sensor data for charts"""
    try:
        limit = request.args.get('limit', 50, type=int)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM sensor_readings 
            ORDER BY id DESC LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()

        data = []
        for row in rows:
            row_dict = {
                'id': row['id'],
                'timestamp': row['timestamp'],
                'temperature': row['temperature'],
                'humidity': row['humidity'],
                'light': row['light'],
                'motion': row['motion'],
                'occupancy': row['occupancy'],
                'outdoor_temp': row['outdoor_temp'],
                'outdoor_hum': row['outdoor_hum']
            }
            try:
                row_dict['people_count'] = row['people_count']
            except (IndexError, KeyError):
                row_dict['people_count'] = 0
            data.append(row_dict)

        # Reverse to get chronological order
        data.reverse()

        return jsonify({
            'status': 'success',
            'data': data
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
@app.route('/api/api/stats', methods=['GET']) # Fallback
def get_stats():
    """Get statistics for the dashboard"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Get average, min, max values
        cursor.execute('''
            SELECT 
                AVG(temperature) as avg_temp,
                MIN(temperature) as min_temp,
                MAX(temperature) as max_temp,
                AVG(humidity) as avg_hum,
                MIN(humidity) as min_hum,
                MAX(humidity) as max_hum,
                AVG(light) as avg_light,
                COUNT(*) as total_readings
            FROM sensor_readings
            WHERE timestamp >= datetime('now', '-24 hours')
        ''')
        stats = cursor.fetchone()
        conn.close()

        return jsonify({
            'status': 'success',
            'stats': {
                'temperature': {
                    'avg': round(stats['avg_temp'] or 0, 1),
                    'min': round(stats['min_temp'] or 0, 1),
                    'max': round(stats['max_temp'] or 0, 1)
                },
                'humidity': {
                    'avg': round(stats['avg_hum'] or 0, 1),
                    'min': round(stats['min_hum'] or 0, 1),
                    'max': round(stats['max_hum'] or 0, 1)
                },
                'light': {
                    'avg': round(stats['avg_light'] or 0, 0)
                },
                'total_readings': stats['total_readings']
            }
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/energy/reset', methods=['POST'])
def reset_energy():
    """Reset energy tracking counters"""
    try:
        server_state['led_on_seconds'] = 0
        server_state['total_energy_cost'] = (0, 0)
        server_state['session_start'] = time.time()
        return jsonify({
            'status': 'success',
            'message': 'Energy counters reset'
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/export', methods=['GET'])
def export_csv():
    """Export sensor data as CSV file"""
    try:
        start_date = request.args.get('start', None)
        end_date = request.args.get('end', None)

        conn = get_db()
        cursor = conn.cursor()

        query = 'SELECT * FROM sensor_readings'
        params = []

        if start_date and end_date:
            query += ' WHERE timestamp BETWEEN ? AND ?'
            params = [start_date, end_date]
        elif start_date:
            query += ' WHERE timestamp >= ?'
            params = [start_date]
        elif end_date:
            query += ' WHERE timestamp <= ?'
            params = [end_date]

        query += ' ORDER BY timestamp DESC'

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(['ID', 'Timestamp', 'Temperature (°C)', 'Humidity (%)',
                         'Light Level', 'Motion', 'Occupancy', 'People Count',
                         'Outdoor Temp (°C)', 'Outdoor Hum (%)'])

        for row in rows:
            people = 0
            try:
                people = row['people_count']
            except (IndexError, KeyError):
                pass
            writer.writerow([
                row['id'],
                row['timestamp'],
                row['temperature'],
                row['humidity'],
                row['light'],
                row['motion'],
                row['occupancy'],
                people,
                row['outdoor_temp'],
                row['outdoor_hum']
            ])

        output.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'sensor_data_{timestamp}.csv'

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*50)
    print("🏢 COMFORTSENSE IoT DASHBOARD")
    print("="*50)
    print(f"📡 Server running on http://0.0.0.0:5005 (PID: {os.getpid()})")
    print(f"🌐 Dashboard: http://localhost:5005")
    print(f"📥 ESP8266 endpoint: http://<your-ip>:5005/api/update")
    print(f"⚡ Energy rate: ₹{ELECTRICITY_RATE}/kWh | LED: {LED_WATTAGE}W")
    print(f"🌡 Arduino thresholds: T>{ARDUINO_TEMP_HIGH}°C H>{ARDUINO_HUM_HIGH}%")
    
    print("\n⚠️ TROUBLESHOOTING HARDWARE CONNECTION:")
    print("   1. Verify IP matches Arduino sketch: 10.165.141.186")
    print("   2. Check Firewall: Ensure port 5005 is allowed (Private/Public)")
    print("      Try running in PowerShell as Admin: New-NetFirewallRule -DisplayName 'Allow Python Flask' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5005")
    print("   3. Check Network: Ensure Arduino and PC are on the SAME WiFi network")
    print("="*50 + "\n")

    try:
        # Disable reloader to prevent subprocess issues in background execution
        app.run(host='0.0.0.0', port=5005, debug=True, use_reloader=False)
    except Exception as e:
        with open("crash_log.txt", "w") as f:
            f.write(f"CRASH: {str(e)}")
