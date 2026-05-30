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
        "total_dc_power": round(total_dc, 2),
        "total_ac_power": round(total_ac, 2),
        "alarm_records": alarm_count
    }


def get_daily_curve():
    rows = get_all_cloud_data()

    labels = []
    values = []

    for row in reversed(rows):
        timestamp = row[1]
        ac_power = row[6] or 0

        try:
            dt = datetime.fromisoformat(timestamp)
            labels.append(dt.strftime("%H:%M:%S"))
            values.append(ac_power)
        except:
            pass

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