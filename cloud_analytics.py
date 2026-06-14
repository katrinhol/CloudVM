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

    # get_all_cloud_data() liefert DESC, für Kurve brauchen wir alt -> neu
    rows = list(reversed(rows))

    # Ein simulierter Tag hat 288 Werte:
    # 24 Stunden * 12 Werte pro Stunde = 288
    points_per_day = 288

    # Nur den letzten simulierten Tag anzeigen
    rows = rows[-points_per_day:]

    labels = []
    values = []

    for i, row in enumerate(rows):
        simulated_minutes = i * 5
        hour = simulated_minutes // 60
        minute = simulated_minutes % 60

        labels.append(f"{hour:02d}:{minute:02d}")

        # AC Power von W in kW
        ac_power_kw = (row[6] or 0) / 1000
        values.append(round(ac_power_kw, 2))

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