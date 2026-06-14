# cloud_dashboard.py

from flask import Flask, render_template_string, jsonify
from cloud_storage import init_db, get_all_cloud_data, get_all_plant_data
from cloud_analytics import get_cloud_summary, get_daily_curve, get_yearly_curve

app = Flask(__name__)
init_db()

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PV Cloud Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f4f7fb;
            color: #1f2937;
        }

        header {
            background: linear-gradient(135deg, #0f766e, #2563eb);
            color: white;
            padding: 28px 40px;
        }

        header h1 {
            margin: 0;
            font-size: 32px;
        }

        .container {
            padding: 30px 40px;
        }

        .cards {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 18px;
            margin-bottom: 30px;
        }

        .card, .chart-card, .table-card {
            background: white;
            border-radius: 16px;
            padding: 22px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
        }

        .card-title {
            font-size: 14px;
            color: #6b7280;
            margin-bottom: 10px;
        }

        .card-value {
            font-size: 30px;
            font-weight: bold;
        }

        .ok {
            color: #16a34a;
        }

        .warn {
            color: #f59e0b;
        }

        .charts {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 30px;
        }

        canvas {
            max-height: 320px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            text-align: left;
            background: #eef2ff;
            padding: 12px;
        }

        td {
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }

        .badge {
            padding: 5px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: bold;
        }

        .badge-ok {
            background: #dcfce7;
            color: #166534;
        }

        .badge-alarm {
            background: #fee2e2;
            color: #991b1b;
        }

        @media (max-width: 1000px) {
            .cards, .charts {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>

<body>
<header>
    <h1>PV Cloud Dashboard</h1>
    <p>Historical PV production and environmental monitoring</p>
</header>

<div class="container">

    <div class="cards">
        <div class="card">
            <div class="card-title">Records</div>
            <div class="card-value" id="records">{{ summary.records }}</div>
        </div>

        <div class="card">
            <div class="card-title">Total DC Power</div>
            <div class="card-value" id="totalDc">{{ summary.total_dc_power }} W</div>
        </div>

        <div class="card">
            <div class="card-title">Total AC Power</div>
            <div class="card-value ok" id="totalAc">{{ summary.total_ac_power }} W</div>
        </div>

        <div class="card">
            <div class="card-title">Alarm Records</div>
            <div class="card-value warn" id="alarmRecords">{{ summary.alarm_records }}</div>
        </div>
    </div>

    <div class="charts">
        <div class="chart-card">
            <h2>Daily electricity curve</h2>
            <canvas id="dailyChart"></canvas>
        </div>

        <div class="chart-card">
            <h2>Yearly electricity curve</h2>
            <canvas id="yearlyChart"></canvas>
        </div>
    </div>

    <div class="table-card">
        <h2>Historical PV Data</h2>

        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Timestamp</th>
                    <th>Plant</th>
                    <th>DC Power</th>
                    <th>AC Power</th>
                    <th>Energy</th>
                    <th>Irradiance</th>
                    <th>Status</th>
                    <th>Alarms</th>
                </tr>
            </thead>
            <tbody id="historyBody">
                {% for row in rows %}
                <tr>
                    <td>{{ row[0] }}</td>
                    <td>{{ row[1] }}</td>
                    <td>{{ row[2] }}</td>
                    <td>{{ row[5] }}</td>
                    <td>{{ row[6] }}</td>
                    <td>{{ "%.2f"|format(row[7] or 0) }}</td>
                    <td>{{ "%.2f"|format(row[8] or 0) }}</td>
                    <td>
                        {% if row[11] == 1 %}
                            <span class="badge badge-ok">VALID</span>
                        {% else %}
                            <span class="badge badge-alarm">INVALID</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if row[12] == "[]" %}
                            <span class="badge badge-ok">NO ALARM</span>
                        {% else %}
                            <span class="badge badge-alarm">ALARM</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

</div>

<script>
    let dailyChart;
    let yearlyChart;

    const initialDailyLabels = {{ daily_labels | safe }};
    const initialDailyValues = {{ daily_values | safe }};
    const initialYearlyLabels = {{ yearly_labels | safe }};
    const initialYearlyValues = {{ yearly_values | safe }};

    function hasValues(values) {
        return Array.isArray(values) && values.some(v => Number(v) > 0);
    }

    function saveLastValidChartData(data) {
        if (hasValues(data.daily_values)) {
            localStorage.setItem("dailyChartData", JSON.stringify({
                labels: data.daily_labels,
                values: data.daily_values
            }));
        }

        if (hasValues(data.yearly_values)) {
            localStorage.setItem("yearlyChartData", JSON.stringify({
                labels: data.yearly_labels,
                values: data.yearly_values
            }));
        }
    }

    function loadLastValidChartData(key, fallbackLabels, fallbackValues) {
        const saved = localStorage.getItem(key);

        if (saved) {
            try {
                return JSON.parse(saved);
            } catch (error) {
                console.error("Could not load saved chart data:", error);
            }
        }

        return {
            labels: fallbackLabels,
            values: fallbackValues
        };
    }

    const dailyData = loadLastValidChartData(
        "dailyChartData",
        initialDailyLabels,
        initialDailyValues
    );

    const yearlyData = loadLastValidChartData(
        "yearlyChartData",
        initialYearlyLabels,
        initialYearlyValues
    );

    dailyChart = new Chart(document.getElementById("dailyChart"), {
        type: "line",
        data: {
            labels: dailyData.labels,
            datasets: [{
                label: "AC Power [kW]",
                data: dailyData.values,
                borderWidth: 3,
                tension: 0.35
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: true
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: "Time [h]"
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: "AC-Power [kW]"
                    }
                }
            }
        }
    });

    yearlyChart = new Chart(document.getElementById("yearlyChart"), {
        type: "bar",
        data: {
            labels: yearlyData.labels,
            datasets: [{
                label: "Energy [kWh]",
                data: yearlyData.values,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    function updateSummary(summary) {
        document.getElementById("records").textContent = summary.records;
        document.getElementById("totalDc").textContent = summary.total_dc_power + " kW";
        document.getElementById("totalAc").textContent = summary.total_ac_power + " kW";
        document.getElementById("alarmRecords").textContent = summary.alarm_records;
    }

    function updateHistoryTable(rows) {
        const tbody = document.getElementById("historyBody");
        tbody.innerHTML = "";

        rows.forEach(row => {
            const validBadge = row[11] === 1
                ? '<span class="badge badge-ok">VALID</span>'
                : '<span class="badge badge-alarm">INVALID</span>';

            const alarmBadge = row[12] === "[]"
                ? '<span class="badge badge-ok">NO ALARM</span>'
                : '<span class="badge badge-alarm">ALARM</span>';

            const tr = document.createElement("tr");

            tr.innerHTML = `
                <td>${row[0] ?? ""}</td>
                <td>${row[1] ?? ""}</td>
                <td>${row[2] ?? ""}</td>
                <td>${row[5] ?? ""}</td>
                <td>${row[6] ?? ""}</td>
                <td>${row[7] ?? ""}</td>
                <td>${row[8] ?? ""}</td>
                <td>${validBadge}</td>
                <td>${alarmBadge}</td>
            `;

            tbody.appendChild(tr);
        });
    }

    async function updateDashboard() {
        try {
            const response = await fetch("/dashboard-data");

            if (!response.ok) {
                throw new Error("Dashboard update failed");
            }

            const data = await response.json();

            updateSummary(data.summary);
            updateHistoryTable(data.rows);

            saveLastValidChartData(data);

            if (hasValues(data.daily_values)) {
                dailyChart.data.labels = data.daily_labels;
                dailyChart.data.datasets[0].data =
                data.daily_values;
                dailyChart.update();
            }

            if (hasValues(data.yearly_values)) {
                yearlyChart.data.labels = data.yearly_labels;
                yearlyChart.data.datasets[0].data = data.yearly_values;
                yearlyChart.update();
            }

        } catch (error) {
            console.error("Dashboard update failed:", error);
        }
    }

    setInterval(updateDashboard, 10000);
</script>

</body>
</html>
"""


@app.route("/")
def dashboard():
    daily_labels, daily_values = get_daily_curve()
    yearly_labels, yearly_values = get_yearly_curve()

    return render_template_string(
        HTML,
        rows=get_all_plant_data(),
        summary=get_cloud_summary(),
        daily_labels=daily_labels,
        daily_values=daily_values,
        yearly_labels=yearly_labels,
        yearly_values=yearly_values
    )


@app.route("/dashboard-data")
def dashboard_data():
    daily_labels, daily_values = get_daily_curve()
    yearly_labels, yearly_values = get_yearly_curve()

    return jsonify({
        "summary": get_cloud_summary(),
        "rows": get_all_plant_data(),
        "daily_labels": daily_labels,
        "daily_values": daily_values,
        "yearly_labels": yearly_labels,
        "yearly_values": yearly_values
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)