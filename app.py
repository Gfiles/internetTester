# To build the executable, run the `build.py` script.
import sqlite3
from flask import Flask, jsonify, request, render_template, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler # pip install apscheduler
from datetime import datetime, timedelta
import speedtest #pip install speedtest-cli
import webbrowser, sys, os # pip install webbrowser
from threading import Timer
import os
import sys
import statistics
import json
import logging
from waitress import serve # pip install waitress

from PIL import Image # pip install Pillow
from pystray import Icon as TrayIcon, MenuItem as item, Menu #pip install pystray
import threading

VERSION = "2025.11.28"
APP_NAME = "internetTester"

def get_default_settings():
    """Returns a dictionary with the default settings."""
    return {
        "port": 5010,
        "show_median_lines": True,
        "open_on_startup": True,
        "test_interval_minutes": 15,
        "default_time_frame": "1hour",
        "time_frames": {
            "1hour": {"label": "Last Hour", "delta": {"hours": 1}},
            "4hours": {"label": "Last 4 Hours", "delta": {"hours": 4}},
            "12hours": {"label": "Last 12 Hours", "delta": {"hours": 12}},
            "day": {"label": "Last 24 Hours", "delta": {"days": 1}},
            "week": {"label": "Last Week", "delta": {"weeks": 1}},
            "month": {"label": "Last Month", "delta": {"days": 30}},
            "year": {"label": "Last Year", "delta": {"days": 365}},
            "all": {"label": "All Time", "delta": {}}
        }
    }

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

app = Flask(__name__, template_folder=resource_path('templates'), static_folder=resource_path('static'))

# Determine the base path for the database, which works for development and for a PyInstaller bundle.
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # In a PyInstaller bundle, use the executable's directory
    application_path = os.path.dirname(sys.executable)
else:
    # In a normal Python environment, use the script's directory
    application_path = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(application_path, 'network_tests.db')
log_path = os.path.join(application_path, 'app.log')

# Setup logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler(sys.stdout)
    ]
)

def init_db():
    """Creates database tables if they don't exist."""
    logging.info(f"Initializing database at: {db_path}")
    with sqlite3.connect(db_path) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS network_tests (
                timestamp DATETIME PRIMARY KEY,
                download_mbps REAL,
                upload_mbps REAL,
                latency_ms REAL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
    logging.info(f"Database '{db_path}' initialized.")

def load_settings():
    """Loads settings from the database, populating with defaults if necessary."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        db_settings = dict(cursor.fetchall())

    settings = {}
    default_settings = get_default_settings()
    is_updated = False

    # Check for missing settings and apply defaults
    for key, default_value in default_settings.items():
        if key not in db_settings:
            settings[key] = default_value
            is_updated = True
        else:
            # Deserialize values from DB text
            db_value = db_settings[key]
            if isinstance(default_value, bool):
                settings[key] = str(db_value).lower() in ('true', '1')
            elif isinstance(default_value, int):
                settings[key] = int(db_value)
            elif isinstance(default_value, (dict, list)):
                try:
                    settings[key] = json.loads(db_value)
                except json.JSONDecodeError:
                    logging.warning(f"Could not decode setting '{key}'. Using default.")
                    settings[key] = default_value
            else:
                settings[key] = db_value

    if is_updated:
        logging.info("Some settings were missing, populating database with defaults.")
        save_settings(settings)

    return settings

def save_settings(settings_dict):
    """Saves the settings dictionary to the database."""
    with sqlite3.connect(db_path) as conn:
        for key, value in settings_dict.items():
            db_value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, db_value))
    logging.info("Settings saved to database.")

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
        if '429' in str(e):
            logging.warning(f"Speedtest rate limit hit: {e}. Consider increasing the test interval in the settings.")
        else:
            logging.error(f"A speedtest error occurred: {e}")
        return {"download": None, "upload": None, "ping": None}
    except Exception as e:
        logging.error("An unexpected error during speed test.", exc_info=True)
        return {"download": None, "upload": None, "ping": None}


def run_test_and_store():
    """Runs the network test and stores the results in the database."""
    logging.info(f"Attempting to run test at {datetime.now()}")
    results = measure_network_quality()
    if results["download"] is not None: # Only store if test was successful
        try:
            timestamp = datetime.now().isoformat()
            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    INSERT INTO network_tests (timestamp, download_mbps, upload_mbps, latency_ms)
                    VALUES (?, ?, ?, ?)
                ''', (timestamp, results['download'], results['upload'], results['ping']))
            logging.info(f"Test run at {timestamp}: Download={results['download']:.2f} Mbps, Upload={results['upload']:.2f} Mbps, Latency={results['ping']:.2f} ms")
        except sqlite3.Error as e:
            logging.error("Database error when storing results.", exc_info=True)
    else:
        logging.warning("Speed test failed, not storing results.")

# Initialize database tables and load settings
init_db()
settings = load_settings()

# Initialize and start the scheduler
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(
    run_test_and_store,
    'interval',
    minutes=settings.get('test_interval_minutes', 5),
    id='speedtest_job',
    next_run_time=datetime.now()
)
scheduler.start()
logging.info(f"Scheduler started. Interval: {settings.get('test_interval_minutes', 15)} minutes.")


@app.route('/api/network_data', methods=['GET'])
def get_network_data():
    """API endpoint to retrieve network data with optional time filtering."""
    time_frame_key = request.args.get('time_frame', settings.get('default_time_frame', '1hour'))
    start_time = None

    time_frames = settings.get('time_frames', get_default_settings()['time_frames'])
    if time_frame_key != 'all' and time_frame_key in time_frames:
        delta_args = time_frames[time_frame_key].get('delta')
        if delta_args:
            start_time = datetime.now() - timedelta(**delta_args)

    query = '''
        SELECT timestamp, download_mbps, upload_mbps, latency_ms
        FROM network_tests
    '''
    params = []

    if start_time:
        query += ' WHERE timestamp >= ?'
        params.append(start_time.isoformat())

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
        logging.error("Error fetching data from database.", exc_info=True)

    # Calculate medians
    medians = {
        "download": None,
        "upload": None,
        "ping": None
    }
    if data:
        downloads = [d['download_mbps'] for d in data if d['download_mbps'] is not None]
        uploads = [d['upload_mbps'] for d in data if d['upload_mbps'] is not None]
        pings = [d['latency_ms'] for d in data if d['latency_ms'] is not None]

        if downloads:
            medians["download"] = statistics.median(downloads)
        if uploads:
            medians["upload"] = statistics.median(uploads)
        if pings:
            medians["ping"] = statistics.median(pings)

    # Return a structured response
    return jsonify({"time_series": data, "medians": medians})

@app.route('/')
def index():
    """Redirects to the main dashboard page."""
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Serves the main dashboard HTML page."""
    return render_template('index.html', settings=settings, version=VERSION)

@app.route('/settings')
def settings_page():
    """Serves the settings page."""
    return render_template('settings.html', settings=settings, version=VERSION)

@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    """API endpoint to get and set application settings."""
    global settings
    if request.method == 'POST':
        try:
            new_settings_data = request.json

            # Handle port
            new_port = new_settings_data.get('port')
            if new_port and new_port != settings.get('port'):
                settings['port'] = int(new_port)

            # Handle the new checkbox setting
            open_on_startup = new_settings_data.get('open_on_startup')
            if isinstance(open_on_startup, bool):
                settings['open_on_startup'] = open_on_startup

            new_interval = int(new_settings_data.get('test_interval_minutes'))

            # Handle show_median_lines
            show_median = new_settings_data.get('show_median_lines')
            if isinstance(show_median, bool):
                settings['show_median_lines'] = show_median

            # Handle test interval
            if new_interval > 0 and new_interval != settings.get('test_interval_minutes'):
                settings['test_interval_minutes'] = new_interval
                scheduler.reschedule_job('speedtest_job', trigger='interval', minutes=new_interval)
                logging.info(f"Rescheduled speed test interval to {new_interval} minutes.")

            # Handle time frames update
            if 'time_frames' in new_settings_data:
                new_time_frames = new_settings_data['time_frames']
                if not isinstance(new_time_frames, dict):
                    raise ValueError("time_frames must be an object.")
                
                # Ensure 'all' is always present
                if 'all' not in new_time_frames:
                    new_time_frames['all'] = get_default_settings()['time_frames']['all']
                
                settings['time_frames'] = new_time_frames

            # Handle default time frame, ensuring it's valid
            new_default_frame = new_settings_data.get('default_time_frame')
            if new_default_frame in settings.get('time_frames', {}):
                settings['default_time_frame'] = new_default_frame
            else:
                # If the old default was deleted or is invalid, pick a new one.
                available_keys = [k for k in settings.get('time_frames', {}).keys() if k != 'all']
                settings['default_time_frame'] = available_keys[0] if available_keys else 'all'

            save_settings(settings)
            return jsonify({"status": "success", "message": "Settings saved successfully."})
        except (ValueError, KeyError, TypeError) as e:
            logging.error(f"Invalid settings data received: {e}", exc_info=True)
            return jsonify({"status": "error", "message": f"Invalid settings data: {e}"}), 400
    return jsonify(settings)

def open_browser():
    """
    Opens the dashboard URL in a new browser tab.
    """
    port = settings.get("port", 5010)
    dashboard_url = f"http://127.0.0.1:{port}/dashboard"
    webbrowser.open_new_tab(dashboard_url)

def exit_action(icon, item):
    """Function to be called when 'Exit' is clicked."""
    logging.info("Exit command received. Shutting down.")
    icon.stop()
    # A hard exit is the most reliable way to ensure all threads (like waitress) are terminated.
    os._exit(0)

def run_tray_icon():
    """Creates and runs the system tray icon."""
    try:
        image = Image.open(resource_path("icon.png"))
        menu = (
            item(f"Internet Tester: v_{VERSION}", None, enabled=False),
            Menu.SEPARATOR,
            item('Open Dashboard', open_browser, default=True),
            item('Exit', exit_action)
        )
        tray_icon = TrayIcon(APP_NAME, image, f"{APP_NAME} v{VERSION}", menu)
        logging.info("Starting system tray icon.")
        tray_icon.run()
    except Exception as e:
        logging.error(f"Failed to create system tray icon: {e}", exc_info=True)

def run_web_server():
    """Starts the Flask web server using Waitress."""
    host = "0.0.0.0"
    port = settings.get("port", 5010)
    logging.info(f"Starting server on http://{host}:{port}")
    if settings.get("open_on_startup", True):
        logging.info(f"Dashboard will open automatically at: http://127.0.0.1:{port}/dashboard")
        Timer(1, open_browser).start()
    else:
        logging.info(f"Dashboard is available at: http://127.0.0.1:{port}/dashboard")
    serve(app, host=host, port=port)

if __name__ == '__main__':
    # Run the web server in a separate thread
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()
    # Run the tray icon in the main thread (pystray must be in the main thread on macOS)
    run_tray_icon()
