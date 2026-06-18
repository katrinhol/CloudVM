import json
import sqlite3
from datetime import datetime
from typing import Any, Iterable, Optional

DB_NAME = "cloud_pv_history.db"

BASE_COLUMNS = {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "timestamp": "TEXT",
    "plant_id": "TEXT",
    "source": "TEXT",
    "type": "TEXT",
    "dc_power": "REAL",
    "ac_power": "REAL",
    "energy_kwh": "REAL",
    "irradiance": "REAL",
    "module_temp": "REAL",
    "ambient_temp": "REAL",
    "valid": "INTEGER",
    "alarms": "TEXT",
}

EXTRA_COLUMNS = {
    "dc_voltage": "REAL",
    "dc_current": "REAL",
    "ac_voltage": "REAL",
    "ac_current": "REAL",
    "status": "INTEGER",
    "errors": "TEXT",
    "wind_speed": "REAL",
    "region": "TEXT",
    "raw_payload": "TEXT",
}

ALL_COLUMNS = {**BASE_COLUMNS, **EXTRA_COLUMNS}


def _connect():
    return sqlite3.connect(DB_NAME)


def _json_text(value: Any, default: Any = None) -> str:
    if value is None:
        value = [] if default is None else default
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return json.dumps(str(value), ensure_ascii=False)


def _first_value(data: dict, *keys: str):
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return None


def normalize_plant_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "none":
        return None
    upper = text.upper().replace(" ", "")
    if upper in {"1", "PV1", "PV01", "PLANT1", "ANLAGE1"}:
        return "PV1"
    if upper in {"2", "PV2", "PV02", "PLANT2", "ANLAGE2"}:
        return "PV2"
    return text


def init_db():
    conn = _connect()
    cursor = conn.cursor()

    column_sql = ",\n            ".join(f"{name} {spec}" for name, spec in BASE_COLUMNS.items())
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS pv_cloud_data (
            {column_sql}
        )
    """)

    cursor.execute("PRAGMA table_info(pv_cloud_data)")
    existing = {row[1] for row in cursor.fetchall()}
    for name, spec in EXTRA_COLUMNS.items():
        if name not in existing:
            cursor.execute(f"ALTER TABLE pv_cloud_data ADD COLUMN {name} {spec}")

    conn.commit()
    conn.close()


def save_cloud_data(data):
    init_db()
    conn = _connect()
    cursor = conn.cursor()

    alarms = data.get("alarms", [])
    errors = data.get("errors", [])
    plant_id = normalize_plant_id(data.get("plant_id"))

    row = {
        "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
        "plant_id": plant_id,
        "source": data.get("source"),
        "type": data.get("type", "plant"),
        "dc_power": _first_value(data, "dc_power", "total_dc_power"),
        "ac_power": _first_value(data, "ac_power", "total_ac_power"),
        "energy_kwh": _first_value(data, "energy_kwh", "total_energy_kwh"),
        "irradiance": _first_value(data, "irradiance", "avg_irradiance", "solar_irradiance"),
        "module_temp": _first_value(data, "module_temp", "avg_module_temp"),
        "ambient_temp": _first_value(data, "ambient_temp", "avg_ambient_temp"),
        "valid": int(bool(data.get("valid", True))),
        "alarms": _json_text(alarms),
        "dc_voltage": data.get("dc_voltage"),
        "dc_current": data.get("dc_current"),
        "ac_voltage": data.get("ac_voltage"),
        "ac_current": data.get("ac_current"),
        "status": data.get("status"),
        "errors": _json_text(errors),
        "wind_speed": _first_value(data, "wind_speed", "wind", "wind_mps", "wind_speed_mps"),
        "region": data.get("region") or data.get("location"),
        "raw_payload": _json_text(data, default={}),
    }

    columns = list(row.keys())
    placeholders = ", ".join("?" for _ in columns)
    cursor.execute(
        f"INSERT INTO pv_cloud_data ({', '.join(columns)}) VALUES ({placeholders})",
        tuple(row[col] for col in columns),
    )

    conn.commit()
    conn.close()


def _fetch(query: str, params: Iterable = ()):
    init_db()
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_cloud_data():
    return _fetch("SELECT * FROM pv_cloud_data ORDER BY timestamp DESC")


def get_all_plant_data():
    return _fetch("""
        SELECT *
        FROM pv_cloud_data
        WHERE plant_id IS NOT NULL
          AND plant_id != 'None'
        ORDER BY timestamp DESC
    """)


def get_today_plant_data():
    today = datetime.now().date().isoformat()
    return _fetch("""
        SELECT *
        FROM pv_cloud_data
        WHERE plant_id IS NOT NULL
          AND plant_id != 'None'
          AND substr(timestamp, 1, 10) = ?
        ORDER BY timestamp DESC
    """, (today,))
