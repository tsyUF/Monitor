import platform
import subprocess
import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import json
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    filename='monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Configuration ---
TARGETS_FILE = "monitoring_targets.txt"
RESULTS_FILE = "docs/data/results.json"
HISTORY_DAYS = 30 # Number of days of history to keep

# --- Helper Functions ---
def read_targets(file_path):
    """Reads a list of targets from a text file, one per line."""
    try:
        with open(file_path, "r") as f:
            targets = [line.strip() for line in f if line.strip()]
            if not targets:
                logging.warning(f"'{file_path}' is empty. Using default targets.")
                return ["google.com", "github.com"]
            logging.info(f"Loaded {len(targets)} targets from '{file_path}'.")
            return targets
    except FileNotFoundError:
        logging.error(f"'{file_path}' not found. Using default targets.")
        return ["google.com", "github.com"]

def load_historical_data(file_path):
    """Loads historical monitoring data from a JSON file."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Could not read or parse '{file_path}': {e}. Starting fresh.")
            return []
    return []

def save_and_prune_data(data, file_path, days_to_keep):
    """Appends new data, prunes old entries, and saves to a JSON file."""
    # Prune entries older than the specified number of days
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    pruned_data = [
        entry for entry in data
        if datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00')) > cutoff_date.replace(tzinfo=None)
    ]

    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Save the pruned data
    try:
        with open(file_path, "w") as f:
            json.dump(pruned_data, f, indent=2)
        logging.info(f"Saved {len(pruned_data)} data points to '{file_path}'.")
    except IOError as e:
        logging.error(f"Could not write to '{file_path}': {e}")
    return pruned_data


# --- Core Logic ---
def main():
    """Main function to run the monitoring process."""
    targets = read_targets(TARGETS_FILE)
    historical_data = load_historical_data(RESULTS_FILE)

    # Setup ping command based on platform
    param = "-n" if platform.system().lower() == "windows" else "-c"

    # Perform pings for all targets
    current_results = []
    for target_host in targets:
        logging.info(f"Pinging {target_host}...")
        command = ["ping", param, "1", target_host]
        status = "Down"
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                status = "Up"
                logging.info(f"Ping to {target_host} SUCCEEDED.")
            else:
                logging.warning(f"Ping to {target_host} FAILED.")
        except Exception as e:
            logging.error(f"Ping to {target_host} failed with an exception: {e}")

        current_results.append({
            "resource": target_host,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        })

    # Combine and save data
    combined_data = historical_data + current_results
    pruned_data = save_and_prune_data(combined_data, RESULTS_FILE, HISTORY_DAYS)

    # Generate outputs
    generate_sparklines(pruned_data)
    generate_html_report(pruned_data)


# --- Output Generation ---
def generate_html_report(all_data):
    """Generates a static HTML report from the latest monitoring data."""
    # Get the latest status for each resource
    latest_status = {item['resource']: item for item in all_data}

    # Function to sanitize resource names for filenames
    def sanitize_resource_name(name):
        return "".join(c if c.isalnum() else '_' for c in name)

    # Build HTML content
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Status</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 2em; background-color: #f8f9fa; color: #212529; }
        h1, h2 { color: #343a40; }
        .service-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1em; }
        .service { background-color: #fff; border: 1px solid #dee2e6; padding: 1.5em; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .service h3 { margin-top: 0; }
        .up { color: #28a745; font-weight: bold; }
        .down { color: #dc3545; font-weight: bold; }
        img { max-width: 100%; height: auto; border-radius: 4px; margin-top: 1em; }
    </style>
</head>
<body>
    <h1>System Status</h1>
"""
    last_checked = "N/A"
    if all_data:
        last_checked_ts = max(datetime.fromisoformat(d['timestamp']) for d in all_data)
        last_checked = last_checked_ts.strftime('%Y-%m-%d %H:%M:%S UTC')

    html += f"<h2>Last Checked: {last_checked}</h2>"
    html += '<div class="service-grid">'

    for resource, data in sorted(latest_status.items()):
        status = data['status']
        sanitized_name = sanitize_resource_name(resource)
        sparkline_path = f"sparkline_{sanitized_name}.png"
        status_class = "up" if status == "Up" else "down"

        html += f"""
    <div class="service">
        <h3>{resource}</h3>
        <p><strong>Status:</strong> <span class="{status_class}">{status}</span></p>
        <img src="{sparkline_path}" alt="{resource} Uptime Sparkline">
    </div>
"""
    html += '</div></body></html>'

    # Write report to file
    try:
        with open("docs/index.html", "w") as f:
            f.write(html)
        logging.info("Successfully generated HTML report at docs/index.html")
    except IOError as e:
        logging.error(f"Could not write HTML report: {e}")


def generate_sparklines(all_data):
    """Generates sparkline images for each resource based on historical data."""
    if not all_data:
        logging.warning("No data available to generate sparklines.")
        return

    df = pd.DataFrame(all_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['value'] = df['status'].map({'Up': 1, 'Down': 0})

    for resource_name, group in df.groupby('resource'):
        try:
            # Sanitize resource name for filename
            sanitized_name = "".join(c if c.isalnum() else '_' for c in resource_name)
            sparkline_path = f"docs/sparkline_{sanitized_name}.png"

            # Resample data to create a consistent time series
            series = group.set_index('timestamp')['value']
            resampled = series.resample('6h').mean().ffill().fillna(0) # Resample every 6 hours and fill gaps
            
            if resampled.empty:
                logging.warning(f"No data to plot for {resource_name}. Creating a flat line.")
                plot_data = [0, 0] # Default to 'Down' if no data
            else:
                plot_data = resampled.tolist()

            # Plotting
            plt.figure(figsize=(4, 0.75))
            color = 'tab:green' if plot_data[-1] > 0.5 else 'tab:red'
            plt.plot(plot_data, color=color, linewidth=2)
            plt.ylim(-0.1, 1.1)
            plt.axis('off')
            plt.tight_layout(pad=0)
            
            plt.savefig(sparkline_path, dpi=100)
            plt.close()
            logging.info(f"Generated sparkline for {resource_name} at {sparkline_path}")

        except Exception as e:
            logging.error(f"Failed to generate sparkline for {resource_name}: {e}", exc_info=True)


if __name__ == "__main__":
    main()
