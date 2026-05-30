import subprocess
import sys
import time
import webbrowser


def start_process(script_name):
    return subprocess.Popen([sys.executable, script_name])


if __name__ == "__main__":
    print("Starting Cloud API...")
    api_process = start_process("cloud_api.py")

    time.sleep(2)

    print("Starting Cloud Dashboard...")
    dashboard_process = start_process("cloud_dashboard.py")

    time.sleep(2)
    webbrowser.open("http://localhost:5002")

    print("Cloud application started.")
    print("API: http://localhost:5000")
    print("Dashboard: http://localhost:5002")
    print("Press CTRL+C to stop everything.")

    try:
        api_process.wait()
        dashboard_process.wait()
    except KeyboardInterrupt:
        print("Stopping cloud application...")
        api_process.terminate()
        dashboard_process.terminate()