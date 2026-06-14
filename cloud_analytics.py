from cloud_storage import get_all_cloud_data
from datetime import datetime


def get_cloud_summary():
    rows = get_all_cloud_data()

    total_ac = 0
    total_dc = 0
    alarm_count = 0

    for row in rows:
        total_dc += row[5] or 0
        total_ac += row[6] or 0

        if row[12] != "[]":
            alarm_count += 1

    return {
        "records": len(rows),
        "total_dc_power": round(total_dc / 1000, 2),
        "total_ac_power": round(total_ac / 1000, 2),
        "alarm_records": alarm_count
    }


def get_daily_curve():
    rows = get_all_cloud_data()

    hourly = {h: 0 for h in range(24)}
    counts = {h: 0 for h in range(24)}

    for row in rows:
        try:
            timestamp = row[1]
            plant_id = row[2]
            ac_power = row[6] or 0

            # Gesamtwerte ohne Plant ignorieren
            if plant_id is None or str(plant_id) == "None":
                continue

            dt = datetime.fromisoformat(timestamp)
            hour = dt.hour

            hourly[hour] += ac_power
            counts[hour] += 1

        except:
            pass

    labels = [f"{h:02d}:00" for h in range(24)]

    values = []
    for h in range(24):
        if counts[h] > 0:
            # Durchschnitt pro Stunde in kW
            values.append(round((hourly[h] / counts[h]) / 1000, 2))
        else:
            values.append(0)

    return labels, values


def get_yearly_curve():
    rows = get_all_cloud_data()

    months = {
        "Jan": 0, "Feb": 0, "Mar": 0, "Apr": 0,
        "May": 0, "Jun": 0, "Jul": 0, "Aug": 0,
        "Sep": 0, "Oct": 0, "Nov": 0, "Dec": 0
    }

    for row in rows:
        timestamp = row[1]
        energy = row[7] or 0

        try:
            dt = datetime.fromisoformat(timestamp)
            month = dt.strftime("%b")
            months[month] += energy
        except:
            pass

    return list(months.keys()), list(months.values())