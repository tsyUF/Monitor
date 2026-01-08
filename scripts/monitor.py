import platform
import subprocess
import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import json
import logging
import requests
from datetime import datetime, timedelta, UTC

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
    """
    Reads a list of targets from a text file.
    Each line can be a plain URL or in the format 'DisplayName=URL'.
    Returns a list of tuples, where each tuple is (DisplayName, URL).
    """
    targets = []
    try:
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if '=' in line:
                    display_name, url = line.split('=', 1)
                    targets.append((display_name.strip(), url.strip()))
                else:
                    targets.append((line, line)) # Use the URL as the display name
            if not targets:
                logging.warning(f"'{file_path}' is empty. Using default targets.")
                return [("Google", "google.com"), ("GitHub", "github.com")]
            logging.info(f"Loaded {len(targets)} targets from '{file_path}'.")
            return targets
    except FileNotFoundError:
        logging.error(f"'{file_path}' not found. Using default targets.")
        return [("Google", "google.com"), ("GitHub", "github.com")]

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
    cutoff_date = datetime.now(UTC) - timedelta(days=days_to_keep)
    pruned_data = [
        entry for entry in data
        if datetime.fromisoformat(entry['timestamp']).replace(tzinfo=UTC) > cutoff_date
    ]
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
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

																	
    current_results = []

    target_urls = [url for _, url in targets]

    for target_host in target_urls:
        logging.info(f"Checking {target_host}...")
												   
        status = "Down"
        try:
            # Add "https://" if no scheme is present
            if not target_host.startswith(('http://', 'https://')):
                url_to_check = f"https://{target_host}"
            else:
                url_to_check = target_host

            response = requests.get(url_to_check, timeout=10)
            if response.status_code >= 200 and response.status_code < 300:
                status = "Up"
                logging.info(f"Check for {target_host} SUCCEEDED with status code {response.status_code}.")
            else:
                logging.warning(f"Check for {target_host} FAILED with status code {response.status_code}.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Check for {target_host} failed with an exception: {e}")

        current_results.append({
            "resource": target_host,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat()
        })


    combined_data = historical_data + current_results
    pruned_data = save_and_prune_data(combined_data, RESULTS_FILE, HISTORY_DAYS)

    generate_chart(pruned_data, target_urls)
    generate_html_report(pruned_data, targets)

# --- Output Generation ---
def generate_chart(all_data, target_urls):
    """Generates a bar chart for each resource url based on historical data."""
    if not all_data:
        logging.warning("No data available to generate charts.")
        return

    df = pd.DataFrame(all_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp'].dt.date
    df['status_val'] = df['status'].apply(lambda x: 1 if x == 'Up' else 0)

    for resource_url in target_urls:
        try:
            resource_df = df[df['resource'] == resource_url]
            sanitized_name = "".join(c if c.isalnum() else '_' for c in resource_url)
            chart_path = f"docs/chart_{sanitized_name}.png"

            if resource_df.empty:
                logging.warning(f"No data for {resource_url}, skipping chart generation.")
                continue

            # Group by date and calculate daily uptime percentage
            daily_uptime = resource_df.groupby('date')['status_val'].mean().fillna(0) * 100

            # Create a full 30-day date range
            end_date = datetime.now(UTC).date()
            start_date = end_date - timedelta(days=HISTORY_DAYS - 1)
            full_range = pd.to_datetime(pd.date_range(start=start_date, end=end_date, freq='D')).date
            daily_uptime = daily_uptime.reindex(full_range, fill_value=0)

            fig, ax = plt.subplots(figsize=(6, 2))
            colors = ['#dc3545' if x < 100 else '#28a745' for x in daily_uptime.values]
            ax.bar(daily_uptime.index, daily_uptime.values, color=colors, width=0.8)

            ax.set_title(f'Uptime for {resource_url} (Last 30 Days)', fontsize=10)
            ax.set_ylabel('Uptime %', fontsize=8)
            ax.set_ylim(0, 100)
            ax.tick_params(axis='x', rotation=45, labelsize=6)
            ax.tick_params(axis='y', labelsize=8)

            # Format x-axis to show date without year
            ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b %d'))

            plt.tight_layout()
            plt.savefig(chart_path, dpi=150)
            plt.close(fig)
            logging.info(f"Generated chart for {resource_url} at {chart_path}")

        except Exception as e:
            logging.error(f"Failed to generate chart for {resource_url}: {e}", exc_info=True)


def generate_html_report(all_data, current_targets):
    """Generates a static HTML report from the latest monitoring data."""
    latest_status_map = {}
    for entry in sorted(all_data, key=lambda x: x['timestamp'], reverse=True):
        if entry['resource'] not in latest_status_map:
            latest_status_map[entry['resource']] = entry

    def sanitize_resource_name(name):
        return "".join(c if c.isalnum() else '_' for c in name)

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
        .service-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.5em;
        }
        @media (max-width: 992px) { .service-grid { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 768px) { .service-grid { grid-template-columns: 1fr; } }
        .service { background-color: #fff; border: 1px solid #dee2e6; padding: 1.5em; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .service h3 { margin-top: 0; }
        .up { color: #28a745; font-weight: bold; }
        .down { color: #dc3545; font-weight: bold; }
        .unknown { color: #6c757d; font-weight: bold; }
        img { max-width: 100%; height: auto; border-radius: 4px; margin-top: 1em; }
        .footer { margin-top: 2em; padding-top: 1em; border-top: 1px solid #dee2e6; }
    </style>
</head>
<body>
    <h1>System Status</h1>
"""
    last_checked = "N/A"
    if all_data:
        try:
            latest_timestamp = max(datetime.fromisoformat(d['timestamp']) for d in all_data)
            last_checked = latest_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
        except (ValueError, TypeError):
             last_checked = "Error parsing date"
    else:
        last_checked = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')

    html += f"<h2>Last Checked: {last_checked}</h2>"
    html += '<div class="service-grid">'

    for display_name, resource_url in sorted(current_targets):
        latest_data = latest_status_map.get(resource_url)
        status = latest_data.get('status', 'Unknown') if latest_data else "Unknown"
        sanitized_name = sanitize_resource_name(resource_url)
        chart_path = f"chart_{sanitized_name}.png"
        status_class = status.lower()

        html += f"""
    <div class="service">
        <h3>{display_name}</h3>
        <p><strong>Status:</strong> <span class="{status_class}">{status}</span></p>
        <img src="{chart_path}" alt="{display_name} Uptime Chart">
    </div>
"""
    html += '</div>'

    # Add the static footer
    html += """
    <div class="footer">
        <h3>Salesforce</h3>
        <a href="https://status.salesforce.com/alias/UFF/history/" target="_blank">Salesforce up status</a>
    </div>
"""

    html += '</body></html>'

    try:
        with open("docs/index.html", "w") as f:
            f.write(html)
        logging.info("Successfully generated HTML report at docs/index.html")
    except IOError as e:
        logging.error(f"Could not write HTML report: {e}")

if __name__ == "__main__":
    main()
