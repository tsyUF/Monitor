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
host = os.getenv("PING_HOST", "us-east-2.console.aws.amazon.com")  # Host to ping (can be overridden with an environment variable)
if not host:
    logging.error("PING_HOST environment variable is not set.")
    raise ValueError("PING_HOST environment variable is not set.")
logfile = os.path.join(os.getcwd(), "status_log.csv")
logging.info(f"Log file path: {logfile}")
sparkline_file = "docs/sparkline.png"  # Output file for sparkline visualization

# Setup ping command based on platform
param = "-n" if platform.system().lower() == "windows" else "-c"
command = ["ping", param, "1", host]

# Function to log status and generate sparkline
def main():
    success = False

    if shutil.which("ping"):
        # Attempt to ping; success if return code is 0
        try:
            success = (subprocess.call(command) == 0)
        except Exception as e:
            logging.error(f"Ping command failed: {e}")
    else:
        logging.warning("The 'ping' command was not found. Attempting to install...")
        # Install iputils-ping (requires root privileges)
        try:
            subprocess.run(["sudo", "apt-get", "update"], check=True)  # Update package lists
            subprocess.run(["sudo", "apt-get", "install", "-y", "iputils-ping"], check=True)
            logging.info("Ping installed successfully. Retrying ping...")
            success = (subprocess.call(command) == 0)  # Retry ping
        except subprocess.CalledProcessError as e:
            logging.error(f"Installation failed with error: {e}")
        except Exception as e:
            logging.error(f"Unexpected error during ping installation: {e}")

    # Prepare timestamp and status
    now = datetime.utcnow().isoformat()
    status = "Up" if success else "Down"

    try:
        # Ensure log file exists with a header
        if not os.path.exists(logfile):
            logging.info(f"Creating log file at: {logfile}")
            with open(logfile, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "status"])

        # Append current result to the log
        logging.info(f"Appending to log file at: {logfile}")
        with open(logfile, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([now, status])
        logging.info("Log updated successfully.")
    except IOError as e:
        logging.error(f"I/O error writing to log file: {e}")
    except Exception as e:
        logging.error(f"Unexpected error writing to log file: {e}")

    # Generate sparkline visualization
    generate_sparkline()

def generate_sparkline():
    try:
        # Read log and filter last 7 days
        df = pd.read_csv(logfile, parse_dates=["timestamp"])
        cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=7)

        # Make cutoff timezone-naive to match the DataFrame's timestamp column
        cutoff = cutoff.tz_localize(None)

        # Filter data for the last 7 days
        df = df[df["timestamp"] >= cutoff.floor('D')]

        # Map status to numeric values (1 for Up, 0 for Down)
        df["value"] = df["status"].map({"Up": 1, "Down": 0})

        # Resample to ensure consistent intervals (e.g., every 6 hours)
        df = df.set_index("timestamp").resample("6h").last().fillna(method="ffill").fillna(0)
        data = df["value"].tolist()

        # Plot sparkline
        plt.figure(figsize=(4, 1))  # Increased size for better visibility
        plt.plot(data, color='tab:green', linewidth=1.5)
        plt.ylim(-0.1, 1.1)
        plt.axis('off')  # Remove axes for sparkline style
        plt.margins(x=0)  # Remove extra margins around the plot
        plt.tight_layout()

        # Save the sparkline figure
        os.makedirs(os.path.dirname(sparkline_file), exist_ok=True)
        plt.savefig(sparkline_file, dpi=150)  # Export with higher resolution
        plt.close()
        logging.info(f"Sparkline saved to {sparkline_file}")
    except FileNotFoundError as e:
        logging.error(f"Log file not found for sparkline generation: {e}")
    except pd.errors.ParserError as e:
        logging.error(f"Error parsing log file for sparkline generation: {e}")
    except Exception as e:
        logging.error(f"Failed to generate sparkline: {e}")
if __name__ == "__main__":
    main()
