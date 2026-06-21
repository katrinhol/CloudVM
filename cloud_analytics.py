import ast
from collections import defaultdict
from datetime import datetime

from cloud_storage import get_all_cloud_data, get_today_plant_data, normalize_plant_id

PLANTS = ["PV1", "PV2"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# SQLite row indexes. New columns are appended after the original schema.
IDX = {
    "id": 0,
    "timestamp": 1,
    "plant_id": 2,
    "source": 3,
    "type": 4,
    "dc_power": 5,
    "ac_power": 6,
    "energy_kwh": 7,
    "irradiance": 8,
    "module_temp": 9,
    "ambient_temp": 10,
    "valid": 11,
    "alarms": 12,
    "dc_voltage": 13,
    "dc_current": 14,
    "ac_voltage": 15,
    "ac_current": 16,
    "status": 17,
    "errors": 18,
    "wind_speed": 19,
    "region": 20,
}


def parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def has_alarm(row):
    value = row[IDX["alarms"]] if len(row) > IDX["alarms"] else None
    if value in (None, "", "[]", []):
        return False
    if isinstance(value, list):
        return bool(value)
    try:
        parsed = ast.literal_eval(str(value))
        return bool(parsed)
    except Exception:
        return str(value).strip() not in {"[]", ""}


def _plant(row):
    return normalize_plant_id(row[IDX["plant_id"]])


def _num(row, key, default=0.0):
    pos = IDX[key]
    if len(row) <= pos or row[pos] is None:
        return default
    try:
        return float(row[pos])
    except (TypeError, ValueError):
        return default


def row_to_dict(row):

    plant = _plant(row) or row[IDX["plant_id"]]
    msg_type = row[IDX["type"]]

    if msg_type == "summary":
        plant = f"Summary {plant}"

    return {
        "id": row[IDX["id"]],
        "timestamp": row[IDX["timestamp"]],
        "plant_id": plant,
        "source": row[IDX["source"]],
        "type": row[IDX["type"]],
        "dc_power": _num(row, "dc_power", None),
        "ac_power": _num(row, "ac_power", None),
        "energy_kwh": _num(row, "energy_kwh", None),
        "irradiance": _num(row, "irradiance", None),
        "module_temp": _num(row, "module_temp", None),
        "ambient_temp": _num(row, "ambient_temp", None),
        "valid": bool(row[IDX["valid"]]),
        "alarms": row[IDX["alarms"]],
        "has_alarm": has_alarm(row),
        "dc_voltage": _num(row, "dc_voltage", None),
        "dc_current": _num(row, "dc_current", None),
        "ac_voltage": _num(row, "ac_voltage", None),
        "ac_current": _num(row, "ac_current", None),
        "status": row[IDX["status"]] if len(row) > IDX["status"] else None,
        "errors": row[IDX["errors"]] if len(row) > IDX["errors"] else "[]",
        "wind_speed": _num(row, "wind_speed", None),
        "region": row[IDX["region"]] if len(row) > IDX["region"] else None,
    }


def get_cloud_summary():
    rows = get_today_plant_data()
    latest_by_plant = {}

    for row in rows:  # rows already DESC, first per plant is latest
        plant = _plant(row)
        if plant and plant not in latest_by_plant:
            latest_by_plant[plant] = row

    plants = {}
    total_dc = 0.0
    total_ac = 0.0
    for plant in PLANTS:
        row = latest_by_plant.get(plant)
        dc = _num(row, "dc_power") if row else 0.0
        ac = _num(row, "ac_power") if row else 0.0
        total_dc += dc
        total_ac += ac
        plants[plant] = {
            "dc_kw": round(dc / 1000, 2),
            "ac_kw": round(ac / 1000, 2),
            "irradiance": round(_num(row, "irradiance", 0), 2) if row else 0,
            "wind_speed": round(_num(row, "wind_speed", 0), 2) if row else 0,
            "region": row[IDX["region"]] if row and len(row) > IDX["region"] else plant,
        }

    return {
        "records": len(rows),
        "total_dc_power": round(total_dc / 1000, 2),
        "total_ac_power": round(total_ac / 1000, 2),
        "alarm_records": sum(1 for row in rows if has_alarm(row)),
        "plants": plants,
    }


def _energy_curve(rows, bucket_func, labels):
    buckets = {plant: defaultdict(lambda: {"first": None, "last": None}) for plant in PLANTS}
    for row in reversed(rows):
        plant = _plant(row)
        if plant not in PLANTS:
            continue
        energy = _num(row, "energy_kwh", None)
        dt = parse_dt(row[IDX["timestamp"]])
        if energy is None or dt is None:
            continue
        bucket = bucket_func(dt)
        current = buckets[plant][bucket]
        if current["first"] is None:
            current["first"] = energy
        current["last"] = energy

    values = {}
    for plant in PLANTS:
        values[plant] = []
        for label in labels:
            item = buckets[plant].get(label)
            if item and item["first"] is not None and item["last"] is not None:
                values[plant].append(round(max(item["last"] - item["first"], 0), 2))
            else:
                values[plant].append(0)
    return labels, values


def get_daily_curve_by_plant():
    rows = get_today_plant_data()
    hours = sorted({parse_dt(r[IDX["timestamp"]]).hour for r in rows if parse_dt(r[IDX["timestamp"]])})
    if not hours:
        labels = [f"{h:02d}:00" for h in range(24)]
    else:
        labels = [f"{h:02d}:00" for h in range(min(hours), max(hours) + 1)]
    return _energy_curve(rows, lambda dt: f"{dt.hour:02d}:00", labels)


def get_yearly_curve_by_plant():
    year = datetime.now().year
    rows = [r for r in get_all_cloud_data() if (parse_dt(r[IDX["timestamp"]]) or datetime.min).year == year]
    return _energy_curve(rows, lambda dt: MONTHS[dt.month - 1], MONTHS)


def get_history_rows():
    return [row_to_dict(row) for row in get_today_plant_data()]
