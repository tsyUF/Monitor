import platform
import subprocess
import datetime
import csv
import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import json
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    filename='monitor.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Example status data
status_data = {
    "serverStatus": "All systems operational",
    "lastUpdated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
}

# Write the data to status.json
try:
    with open("docs/status.json", "w") as f:
        json.dump(status_data, f)
    logging.info("Status data written to docs/status.json successfully.")
except Exception as e:
    logging.error(f"Failed to write status data to docs/status.json: {e}")

# Configuration
ping_targets_env = os.getenv("PING_TARGETS")
if not ping_targets_env:
    logging.error("PING_TARGETS environment variable is not set or empty. Please set it to a comma-separated list of targets.")
    # Defaulting to a predefined list as per potential future enhancement, but exiting for now.
    # targets = ["google.com", "8.8.8.8"]
    # logging.info(f"Using default targets: {targets}")
    exit(1) # Exit if not set, as per current requirements

targets = [target.strip() for target in ping_targets_env.split(',')]
logging.info(f"Targets to ping: {targets}")

# logfile = os.path.join(os.getcwd(), "status_log.csv") # Existing log file for single host status - REMOVED
# logging.info(f"Legacy log file path (single host status): {logfile}") - REMOVED
# sparkline_file = "docs/sparkline.png"  # REMOVED - No longer a single sparkline file
# logging.info(f"Sparkline file (based on legacy log): {sparkline_file}") # REMOVED

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
        # Storing a status for this situation might be useful in a real system
        # For now, just exit.
        exit(1)

    for target_host in targets:
        logging.info(f"Processing target: {target_host}")
        command = ["ping", param, "1", target_host] # Define command for current target
        success = False # Default to False for each target

        try:
            # Attempt to ping; success if return code is 0
            # Using subprocess.run for consistency and better error capture if needed, though call is fine for just exit code
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

    # Create 'data/' directory and write results to 'data/results.json'
    results_file_path = "data/results.json"
    try:
        os.makedirs("data", exist_ok=True)
        logging.info(f"Ensured 'data' directory exists.")
        with open(results_file_path, "w") as f:
            json.dump(ping_results, f, indent=2)
        logging.info(f"Successfully wrote ping results to {results_file_path}")
    except IOError as e:
        logging.error(f"I/O error writing to {results_file_path}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error writing to {results_file_path}: {e}")

    # Generate sparkline visualization for each target
    generate_sparkline(ping_results)

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

            # Resample to ensure consistent intervals (e.g., every 6 hours)
            # Since data/results.json is overwritten each run, it likely contains only one point per resource.
            # Resampling will still work but might produce a single point or a flat line.
            # The .last() after resample might be problematic if there's only one point.
            # Using .mean() or .first() might be more robust for single points, or simply plot the points.
            # For now, sticking to existing logic as much as possible.
            # If a resource has only one entry, resampling might lead to an empty series if not careful.
            # Let's ensure there's data before resampling.
            if resource_df.empty: # Double check after map
                 logging.warning(f"No data after mapping status for resource '{resource_name}'. Skipping its sparkline.")
                 continue

            # Set index for resampling
            # It's crucial that timestamps are unique per resource for resampling, or handle duplicates
            resource_df = resource_df.set_index('timestamp')
            
            # The problem mentions "last 7 days" for original sparkline, but current data is per-run.
            # So, the 7-day window logic is not directly applicable here without data accumulation.
            # We will plot all available points from the current run for this resource.
            # Resample to 6H intervals, forward fill, and then fill remaining NaNs with 0
            # This handles cases with sparse data better than just .last()
            data_series = resource_df['value'].resample("6h").mean().fillna(method="ffill").fillna(0)
            
            if data_series.empty:
                logging.warning(f"Data series is empty for resource '{resource_name}' after resampling. Skipping its sparkline.")
                continue
                
            data = data_series.tolist()

            # Sanitize resource_name for filename
            # Replace common problematic characters with underscore
            sanitized_resource_name = "".join(c if c.isalnum() or c == '-' else '_' for c in resource_name)
            
            sparkline_output_path = f"docs/sparkline_{sanitized_resource_name}.png"
            docs_dir = os.path.dirname(sparkline_output_path)
            os.makedirs(docs_dir, exist_ok=True)

            # Plot sparkline
            plt.figure(figsize=(4, 1))
            plt.plot(data, color='tab:green', linewidth=1.5)
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
