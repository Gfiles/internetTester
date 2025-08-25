# Build command:
# pyinstaller --clean --name InternetTester --onefile --windowed --add-data "templates;templates" --add-data "static;static" --hidden-import "apscheduler.schedulers.background" --hidden-import "apscheduler.executors.default" --hidden-import "apscheduler.jobstores.default" app.py
import sqlite3
from flask import Flask, jsonify, request, render_template, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import speedtest
import webbrowser
from threading import Timer
import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

app = Flask(__name__, template_folder=resource_path('templates'), static_folder=resource_path('static'))
db_path = 'network_tests.db'

def measure_network_quality():
    """ Measures network quality (download, upload, and latency).

    Returns:
        dict: A dictionary containing 'download' (Mbps), 'upload' (Mbps), and
              'ping' (ms).
    """
    try:
        st = speedtest.Speedtest(secure=True) # Use HTTPS
        st.get_best_server()
        download_speed = st.download()
        upload_speed = st.upload()
        ping = st.results.ping

        # Convert speeds from bits/s to Mbit/s
        download_speed_mbps = download_speed / 1_000_000
        upload_speed_mbps = upload_speed / 1_000_000

        return {
            "download": download_speed_mbps,
            "upload": upload_speed_mbps,
            "ping": ping,
        }
    except speedtest.SpeedtestException as e:
        print(f"A speedtest error occurred: {e}")
        return {"download": None, "upload": None, "ping": None}
    except Exception as e:
        print(f"An unexpected error during speed test: {e}")
        return {"download": None, "upload": None, "ping": None}


def run_test_and_store():
    """Runs the network test and stores the results in the database."""
    print(f"Attempting to run test at {datetime.now()}")
    results = measure_network_quality()
    if results["download"] is not None: # Only store if test was successful
        try:
            timestamp = datetime.now().isoformat()
            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    INSERT INTO network_tests (timestamp, download_mbps, upload_mbps, latency_ms)
                    VALUES (?, ?, ?, ?)
                ''', (timestamp, results['download'], results['upload'], results['ping']))
            print(f"Test run at {timestamp}: Download={results['download']:.2f} Mbps, Upload={results['upload']:.2f} Mbps, Latency={results['ping']:.2f} ms")
        except sqlite3.Error as e:
            print(f"Database error when storing results: {e}")
    else:
        print("Speed test failed, not storing results.")


# Check if the database file exists, if not, create the table
if not os.path.exists(db_path):
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute('''
                CREATE TABLE network_tests (
                    timestamp DATETIME PRIMARY KEY,
                    download_mbps REAL,
                    upload_mbps REAL,
                    latency_ms REAL
                )
            ''')
        print(f"Database '{db_path}' and table 'network_tests' created.")
    except sqlite3.Error as e:
        print(f"Error creating database or table: {e}")
else:
    print(f"Database '{db_path}' already exists.")


# Initialize and start the scheduler
scheduler = BackgroundScheduler()
# Schedule the job to run every 5 minutes
scheduler.add_job(run_test_and_store, 'interval', minutes=5)
#scheduler.add_job(run_test_and_store, 'interval', seconds=5)

scheduler.start()
print("Scheduler started.")


@app.route('/api/network_data', methods=['GET'])
def get_network_data():
    """API endpoint to retrieve network data with optional time filtering."""
    time_frame = request.args.get('time_frame', 'all') # default to 'all'
    start_time = None

    if time_frame != 'all':
        end_time = datetime.now()
        time_deltas = {
            'day': timedelta(days=1),
            'week': timedelta(weeks=1),
            'month': timedelta(days=30), # Approximation for month
            'year': timedelta(days=365), # Approximation for year
        }
        delta = time_deltas.get(time_frame)
        if delta:
            start_time = end_time - delta

    query = '''
        SELECT timestamp, download_mbps, upload_mbps, latency_ms
        FROM network_tests
    '''
    params = []

    if start_time:
        query += ' WHERE timestamp >= ?'
        params.append(start_time)

    query += ' ORDER BY timestamp ASC'

    data = []
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row # Access columns by name
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                data.append(dict(row))
    except sqlite3.Error as e:
        print(f"Error fetching data from database: {e}")

    return jsonify(data)

@app.route('/')
def index():
    """Basic route to serve the frontend HTML file."""
    # In a real application, you would serve an HTML file here
    # For now, just return a simple message
    """Redirects to the main dashboard page."""
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Serves the main dashboard HTML page."""
    return render_template('index.html')

if __name__ == '__main__':
    # Use Waitress as the production WSGI server
    from waitress import serve
    host = "0.0.0.0"
    port = 5000
    dashboard_url = f"http://127.0.0.1:{port}/dashboard"

    def open_browser():
        """
        Opens the dashboard URL in a new browser tab.
        """
        webbrowser.open_new_tab(dashboard_url)

    print(f"Starting server on {host}:{port}")
    print(f"Dashboard will open automatically at: {dashboard_url}")

    # Open the browser one second after the server starts
    Timer(1, open_browser).start()

    serve(app, host=host, port=port)