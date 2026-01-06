import platform
import subprocess
import datetime
import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    filename='monitor.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration
ping_targets_env = os.getenv("PING_TARGETS")
if not ping_targets_env:
    targets = ["google.com", "github.com"]
    logging.warning(f"PING_TARGETS environment variable is not set or empty. Using default targets: {targets}")
else:
    targets = [target.strip() for target in ping_targets_env.split(',')]
    logging.info(f"Targets to ping: {targets}")

# Setup ping command based on platform
param = "-n" if platform.system().lower() == "windows" else "-c"
# 'command' will be defined per target in the loop

# Function to log status and generate sparkline
def main():
    ping_results = [] # To store results for multiple targets
    ping_command_available = False

    # Check for ping utility and install if necessary (once before the loop)
    if shutil.which("ping"):
        ping_command_available = True
        logging.info("Ping utility found.")
    else:
        logging.warning("The 'ping' command was not found. Attempting to install iputils-ping...")
        try:
            # Using subprocess.run for better control and error handling
            subprocess.run(["sudo", "apt-get", "update"], check=True, capture_output=True, text=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "iputils-ping"], check=True, capture_output=True, text=True)
            logging.info("iputils-ping installed successfully.")
            ping_command_available = True
        except subprocess.CalledProcessError as e:
            logging.error(f"Installation of iputils-ping failed. Stdout: {e.stdout}. Stderr: {e.stderr}")
        except FileNotFoundError: # Handle if sudo or apt-get is not found
            logging.error("sudo or apt-get command not found. Cannot install iputils-ping.")
        except Exception as e:
            logging.error(f"An unexpected error occurred during ping installation: {e}")

    if not ping_command_available:
        logging.error("Ping command is not available and could not be installed. Exiting.")
        exit(1)

    for target_host in targets:
        logging.info(f"Processing target: {target_host}")
        command = ["ping", param, "1", target_host] # Define command for current target
        success = False # Default to False for each target

        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10) # Added timeout
            if result.returncode == 0:
                success = True
                logging.info(f"Ping to {target_host} SUCCEEDED.")
            else:
                logging.warning(f"Ping to {target_host} FAILED. Return code: {result.returncode}, Error: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            logging.error(f"Ping command to {target_host} timed out.")
        except Exception as e:
            logging.error(f"Ping command to {target_host} failed with an exception: {e}")

        current_time_iso = datetime.utcnow().isoformat()
        status = "Up" if success else "Down"

        ping_results.append({
            "resource": target_host,
            "status": status,
            "timestamp": current_time_iso
        })
        logging.debug(f"Stored result for {target_host}: {{'resource': '{target_host}', 'status': '{status}', 'timestamp': '{current_time_iso}'}}")

    logging.info("Completed processing all targets.")
    logging.info(f"Aggregated ping results (in-memory): {ping_results}")

    # Ensure data is always created with some content
    if not ping_results:
        logging.info("No ping results were collected. Generating pseudo-data for default targets.")
        current_time_iso = datetime.utcnow().isoformat()
        default_fallback_targets = ["google.com", "github.com"]
        for target_host in default_fallback_targets:
            ping_results.append({
                "resource": target_host,
                "status": "Unknown",
                "timestamp": current_time_iso
            })
        logging.debug(f"Generated pseudo-data: {ping_results}")

    # Generate sparkline visualization for each target
    generate_sparkline(ping_results)

    # Generate HTML report
    generate_html_report(ping_results)

def generate_html_report(ping_results_data):
    # Function to sanitize resource names for filenames, matching generate_sparkline
    def sanitize_resource_name(name):
        return "".join(c if c.isalnum() or c == '-' else '_' for c in name)

    # Start of HTML
    html_content = """
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
        img { max-width: 100%; height: auto; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>System Status</h1>
"""

    if not ping_results_data:
        html_content += "<p>No monitoring results found.</p>"
    else:
        try:
            # Assuming all timestamps in a run are similar, use the first one for "Last Checked"
            last_checked_str = ping_results_data[0].get('timestamp', 'N/A')
            if last_checked_str != 'N/A':
                last_checked = datetime.fromisoformat(last_checked_str).strftime('%Y-%m-%d %H:%M:%S UTC')
            else:
                last_checked = "N/A"
            html_content += f"<h2>Last Checked: {last_checked}</h2>"
        except (ValueError, KeyError):
            last_checked = "N/A"
            html_content += f"<h2>Last Checked: {last_checked}</h2>"

        html_content += '<div class="service-grid">'
        for item in ping_results_data:
            resource = item.get("resource", "N/A")
            status = item.get("status", "Unknown")
            sanitized_name = sanitize_resource_name(resource)
            sparkline_path = f"sparkline_{sanitized_name}.png"
            status_class = "up" if status == "Up" else "down"

            html_content += f"""
    <div class="service">
        <h3>{resource}</h3>
        <p><strong>Status:</strong> <span class="{status_class}">{status}</span></p>
        <img src="{sparkline_path}" alt="{resource} Uptime Sparkline">
    </div>
"""
        html_content += '</div>'

    # End of HTML
    html_content += """
</body>
</html>
"""

    # Write to file
    try:
        os.makedirs("docs", exist_ok=True)
        with open("docs/index.html", "w") as f:
            f.write(html_content)
        logging.info("Generated HTML report at docs/index.html")
    except IOError as e:
        logging.error(f"I/O error writing to docs/index.html: {e}")

def generate_sparkline(ping_results_data):
    if not ping_results_data or not isinstance(ping_results_data, list):
        logging.warning("Sparkline generation skipped: ping_results_data is empty or not a list.")
        return

    # Convert the list of dicts to a DataFrame for easier manipulation
    try:
        overall_df = pd.DataFrame(ping_results_data)
        if 'resource' not in overall_df.columns or 'timestamp' not in overall_df.columns or 'status' not in overall_df.columns:
            logging.error("Sparkline generation skipped: ping_results_data is missing required columns (resource, timestamp, status).")
            return
        overall_df['timestamp'] = pd.to_datetime(overall_df['timestamp'])
    except Exception as e:
        logging.error(f"Sparkline generation skipped: Could not process ping_results_data into DataFrame. Error: {e}")
        return

    unique_resources = overall_df['resource'].unique()
    logging.info(f"Found unique resources for sparkline generation: {unique_resources}")

    for resource_name in unique_resources:
        try:
            logging.info(f"Generating sparkline for resource: {resource_name}")
            
            resource_df = overall_df[overall_df['resource'] == resource_name].copy() # Use .copy() to avoid SettingWithCopyWarning
            
            if resource_df.empty:
                logging.warning(f"No data found for resource '{resource_name}' after filtering. Skipping its sparkline.")
                continue

            # Map status to numeric values (1 for Up, 0 for Down)
            resource_df['value'] = resource_df['status'].map({"Up": 1, "Down": 0})
            
            if resource_df['value'].isnull().all():
                logging.warning(f"No valid status data to plot for resource '{resource_name}'. Skipping its sparkline.")
                continue

            # Set index for time-based operations
            resource_df = resource_df.set_index('timestamp')

            # We'll create a simple list of values for plotting.
            # If there's only one point, we can duplicate it to form a flat line.
            data = resource_df['value'].tolist()
            if len(data) == 1:
                data.append(data[0]) # Duplicate the single point to draw a line

            # Sanitize resource_name for filename
            sanitized_resource_name = "".join(c if c.isalnum() or c == '-' else '_' for c in resource_name)
            
            sparkline_output_path = f"docs/sparkline_{sanitized_resource_name}.png"
            docs_dir = os.path.dirname(sparkline_output_path)
            os.makedirs(docs_dir, exist_ok=True)

            # Plot sparkline
            plt.figure(figsize=(4, 1))
            plt.plot(data, color='tab:green' if data[0] == 1 else 'tab:red', linewidth=2)
            plt.ylim(-0.1, 1.1)
            plt.axis('off')
            plt.margins(x=0)
            plt.tight_layout()
            
            plt.savefig(sparkline_output_path, dpi=150)
            plt.close()
            logging.info(f"Sparkline for '{resource_name}' saved to {sparkline_output_path}")

        except Exception as e:
            logging.error(f"Failed to generate sparkline for resource '{resource_name}': {e}", exc_info=True)


if __name__ == "__main__":
    main()
