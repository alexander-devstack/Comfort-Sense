import sqlite3
import json

def check_db():
    conn = sqlite3.connect('sensor_data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT id, timestamp, temperature, humidity, light, outdoor_temp, outdoor_hum, occupancy FROM sensor_readings ORDER BY id DESC LIMIT 50')
    rows = cursor.fetchall()
    
    for row in rows:
        print(f"ID: {row['id']} | Time: {row['timestamp']} | In: {row['temperature']}C/{row['humidity']}% | Out: {row['outdoor_temp']}C/{row['outdoor_hum']}% | Occ: {row['occupancy']}")
    
    conn.close()

if __name__ == '__main__':
    check_db()
