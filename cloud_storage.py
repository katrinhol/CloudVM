import sqlite3
from datetime import datetime

DB_NAME = "cloud_pv_history.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pv_cloud_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            plant_id TEXT,
            source TEXT,
            type TEXT,
            dc_power REAL,
            ac_power REAL,
            energy_kwh REAL,
            irradiance REAL,
            module_temp REAL,
            ambient_temp REAL,
            valid INTEGER,
            alarms TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_cloud_data(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO pv_cloud_data (
            timestamp, plant_id, source, type,
            dc_power, ac_power, energy_kwh,
            irradiance, module_temp, ambient_temp,
            valid, alarms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("timestamp", datetime.utcnow().isoformat()),
        data.get("plant_id"),
        data.get("source"),
        data.get("type", "plant"),
        data.get("dc_power") or data.get("total_dc_power"),
        data.get("ac_power") or data.get("total_ac_power"),
        data.get("energy_kwh") or data.get("total_energy_kwh"),
        data.get("irradiance") or data.get("avg_irradiance"),
        data.get("module_temp") or data.get("avg_module_temp"),
        data.get("ambient_temp") or data.get("avg_ambient_temp"),
        int(data.get("valid", True)),
        str(data.get("alarms", []))
    ))

    conn.commit()
    conn.close()


def get_all_cloud_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM pv_cloud_data ORDER BY timestamp DESC")
    rows = cursor.fetchall()

    conn.close()
    return rows