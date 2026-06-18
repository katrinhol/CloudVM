from flask import Flask, render_template_string, jsonify

from cloud_storage import init_db
from cloud_analytics import (
    get_cloud_summary,
    get_daily_curve_by_plant,
    get_yearly_curve_by_plant,
    get_history_rows,
)

app = Flask(__name__)
init_db()

HTML = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <title>PV Cloud Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { margin: 0; font-family: Arial, sans-serif; background: #f4f7fb; color: #1f2937; }
        header { background: linear-gradient(135deg, #0f766e, #2563eb); color: white; padding: 28px 40px; }
        header h1 { margin: 0; font-size: 32px; }
        .container { padding: 30px 40px; }
        .cards { display: grid; grid-template-columns: repeat(4, minmax(180px, 1fr)); gap: 18px; margin-bottom: 24px; }
        .plant-cards { display: grid; grid-template-columns: repeat(2, minmax(280px, 1fr)); gap: 18px; margin-bottom: 24px; }
        .card, .chart-card, .table-card { background: white; border-radius: 16px; padding: 22px; box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
        .card-title { font-size: 14px; color: #6b7280; margin-bottom: 10px; }
        .card-value { font-size: 28px; font-weight: bold; }
        .plant-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 12px; }
        .metric { background: #f8fafc; border-radius: 12px; padding: 10px; }
        .metric small { display: block; color: #64748b; margin-bottom: 4px; }
        .charts { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 30px; }
        canvas { max-height: 330px; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th { text-align: left; background: #eef2ff; padding: 10px; position: sticky; top: 0; }
        td { padding: 10px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
        .badge { padding: 5px 10px; border-radius: 999px; font-size: 12px; font-weight: bold; display: inline-block; }
        .badge-ok { background: #dcfce7; color: #166534; }
        .badge-alarm { background: #fee2e2; color: #991b1b; }
        .filters { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-bottom: 16px; }
        select, input { padding: 9px 11px; border: 1px solid #cbd5e1; border-radius: 10px; background: white; }
        .table-wrap { max-height: 560px; overflow: auto; }
        @media (max-width: 1000px) { .cards, .plant-cards, .charts { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
<header>
    <h1>PV Cloud Dashboard</h1>
</header>
<div class="container">
    <div class="cards">
        <div class="card"><div class="card-title">Records heute</div><div class="card-value" id="records">0</div></div>
        <div class="card"><div class="card-title">Total DC Power</div><div class="card-value" id="totalDc">0 kW</div></div>
        <div class="card"><div class="card-title">Total AC Power</div><div class="card-value" id="totalAc">0 kW</div></div>
        <div class="card"><div class="card-title">Alarm Records heute</div><div class="card-value" id="alarmRecords">0</div></div>
    </div>

    <div class="plant-cards" id="plantCards"></div>

    <div class="charts">
        <div class="chart-card"><h2>Daily Energy Curve PV1/PV2</h2><canvas id="dailyChart"></canvas></div>
        <div class="chart-card"><h2>Yearly Energy Curve PV1/PV2</h2><canvas id="yearlyChart"></canvas></div>
    </div>

    <div class="table-card">
        <h2>PV History</h2>
        <div class="filters">
            <label>Plant
                <select id="plantFilter">
                    <option value="all">Alle</option>
                    <option value="PV1">PV1</option>
                    <option value="PV2">PV2</option>
                </select>
            </label>
            <label>Alarm
                <select id="alarmFilter">
                    <option value="all">Alle</option>
                    <option value="alarm">Alarm</option>
                    <option value="no_alarm">No Alarm</option>
                </select>
            </label>
            <label>Suche
                <input id="textFilter" placeholder="z.B. low_performance">
            </label>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Zeit</th><th>Plant</th><th>DC W</th><th>AC W</th><th>Energy kWh</th>
                        <th>DC V/A</th><th>AC V/A</th><th>Irradiance</th><th>Wind</th><th>Temp</th><th>Status</th><th>Alarme</th>
                    </tr>
                </thead>
                <tbody id="historyBody"></tbody>
            </table>
        </div>
    </div>
</div>
<script>
let dailyChart;
let yearlyChart;
let latestRows = [];

function fmt(v, digits = 2, suffix = "") {
    if (v === null || v === undefined || v === "") return "-";
    const n = Number(v);
    if (!Number.isFinite(n)) return String(v);
    return n.toFixed(digits) + suffix;
}
function formatTimestamp(timestamp) { return timestamp ? timestamp.substring(0, 19).replace("T", " ") : ""; }
function alarmText(row) { return row.alarms && row.alarms !== "[]" ? row.alarms : "NO ALARM"; }

function makeChart(canvasId, type, labels, valuesByPlant, yTitle) {
    return new Chart(document.getElementById(canvasId), {
        type,
        data: {
            labels,
            datasets: [
                { label: "PV1 [kWh]", data: valuesByPlant.PV1 || [], borderWidth: 3, tension: 0.35 },
                { label: "PV2 [kWh]", data: valuesByPlant.PV2 || [], borderWidth: 3, tension: 0.35 }
            ]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true, title: { display: true, text: yTitle } } } }
    });
}

function updateSummary(summary) {
    document.getElementById("records").textContent = summary.records;
    document.getElementById("totalDc").textContent = summary.total_dc_power + " kW";
    document.getElementById("totalAc").textContent = summary.total_ac_power + " kW";
    document.getElementById("alarmRecords").textContent = summary.alarm_records;

    const box = document.getElementById("plantCards");
    box.innerHTML = "";
    ["PV1", "PV2"].forEach(plant => {
        const p = summary.plants[plant] || {};
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
            <div class="card-title">${plant} / ${p.region || plant}</div>
            <div class="plant-grid">
                <div class="metric"><small>DC</small><strong>${fmt(p.dc_kw, 2, " kW")}</strong></div>
                <div class="metric"><small>AC</small><strong>${fmt(p.ac_kw, 2, " kW")}</strong></div>
                <div class="metric"><small>Sonneneinstrahlung</small><strong>${fmt(p.irradiance, 2, " W/m²")}</strong></div>
                <div class="metric"><small>Windstärke</small><strong>${fmt(p.wind_speed, 2, " m/s")}</strong></div>
            </div>`;
        box.appendChild(card);
    });
}

function updateCharts(data) {
    if (!dailyChart) {
        dailyChart = makeChart("dailyChart", "line", data.daily_labels, data.daily_values, "Energy [kWh]");
        yearlyChart = makeChart("yearlyChart", "bar", data.yearly_labels, data.yearly_values, "Energy [kWh]");
        return;
    }
    dailyChart.data.labels = data.daily_labels;
    dailyChart.data.datasets[0].data = data.daily_values.PV1 || [];
    dailyChart.data.datasets[1].data = data.daily_values.PV2 || [];
    dailyChart.update();
    yearlyChart.data.labels = data.yearly_labels;
    yearlyChart.data.datasets[0].data = data.yearly_values.PV1 || [];
    yearlyChart.data.datasets[1].data = data.yearly_values.PV2 || [];
    yearlyChart.update();
}

function passesFilters(row) {
    const plant = document.getElementById("plantFilter").value;
    const alarm = document.getElementById("alarmFilter").value;
    const text = document.getElementById("textFilter").value.toLowerCase().trim();
    if (plant !== "all" && row.plant_id !== plant) return false;
    if (alarm === "alarm" && !row.has_alarm) return false;
    if (alarm === "no_alarm" && row.has_alarm) return false;
    if (text && !JSON.stringify(row).toLowerCase().includes(text)) return false;
    return true;
}

function renderHistory() {
    const tbody = document.getElementById("historyBody");
    tbody.innerHTML = "";
    latestRows.filter(passesFilters).forEach(row => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${formatTimestamp(row.timestamp)}</td>
            <td><strong>${row.plant_id || "-"}</strong></td>
            <td>${fmt(row.dc_power, 1)}</td>
            <td>${fmt(row.ac_power, 1)}</td>
            <td>${fmt(row.energy_kwh, 2)}</td>
            <td>${fmt(row.dc_voltage, 1)} / ${fmt(row.dc_current, 1)}</td>
            <td>${fmt(row.ac_voltage, 1)} / ${fmt(row.ac_current, 1)}</td>
            <td>${fmt(row.irradiance, 2, " W/m²")}</td>
            <td>${fmt(row.wind_speed, 2, " m/s")}</td>
            <td>${fmt(row.module_temp, 1, " °C")} / ${fmt(row.ambient_temp, 1, " °C")}</td>
            <td>${row.valid ? '<span class="badge badge-ok">VALID</span>' : '<span class="badge badge-alarm">INVALID</span>'}</td>
            <td>${row.has_alarm ? '<span class="badge badge-alarm">ALARM</span> ' + alarmText(row) : '<span class="badge badge-ok">NO ALARM</span>'}</td>`;
        tbody.appendChild(tr);
    });
}

async function updateDashboard() {
    try {
        const response = await fetch("/dashboard-data");
        if (!response.ok) throw new Error("Dashboard update failed");
        const data = await response.json();
        updateSummary(data.summary);
        updateCharts(data);
        latestRows = data.rows;
        renderHistory();
    } catch (error) { console.error(error); }
}

["plantFilter", "alarmFilter", "textFilter"].forEach(id => {
    document.addEventListener("DOMContentLoaded", () => document.getElementById(id).addEventListener("input", renderHistory));
});
updateDashboard();
setInterval(updateDashboard, 5000);
</script>
</body>
</html>
"""


@app.route("/")
def dashboard():
    return render_template_string(HTML)


@app.route("/dashboard-data")
def dashboard_data():
    daily_labels, daily_values = get_daily_curve_by_plant()
    yearly_labels, yearly_values = get_yearly_curve_by_plant()
    return jsonify({
        "summary": get_cloud_summary(),
        "rows": get_history_rows(),
        "daily_labels": daily_labels,
        "daily_values": daily_values,
        "yearly_labels": yearly_labels,
        "yearly_values": yearly_values,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
