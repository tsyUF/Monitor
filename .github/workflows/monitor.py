import platform
import subprocess
import datetime
import csv
import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt

# Configuration
host = os.getenv("PING_HOST", "us-east-2.console.aws.amazon.com")  # Host to ping (can be overridden with an environment variable)
logfile = "status_log.csv"  # Log file for status
sparkline_file = "docs/sparkline.png"  # Output file for sparkline visualization

# Setup ping command based on platform
param = "-n" if platform.system().lower() == "windows" else "-c"
command = ["ping", param, "1", host]

# Function to log status and generate sparkline
def main():
    # Check if the ping command exists
    if shutil.which("ping"):
        # Attempt to ping; success if return code is 0
        success = (subprocess.call(command) == 0)
    else:
        print("The 'ping' command was not found. Attempting to install...")
        # Install iputils-ping (requires root privileges)
        try:
            subprocess.run(["sudo", "apt-get", "update"], check=True)  # Update package lists
            subprocess.run(["sudo", "apt-get", "install", "-y", "iputils-ping"], check=True)
            print("Installation successful. Retrying ping...")
            success = (subprocess.call(command) == 0)  # Retry ping
        except subprocess.CalledProcessError as e:
            print(f"Installation failed with error: {e}")
            success = False

    # Prepare timestamp and status
    now = datetime.datetime.utcnow().isoformat()
    status = "Up" if success else "Down"

    # Ensure log file exists with a header
    if not os.path.exists(logfile):
        with open(logfile, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "status"])

    # Append current result to the log
    with open(logfile, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([now, status])

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
        plt.figure(figsize=(2, 0.5))
        plt.plot(data, color='tab:green', linewidth=1)
        plt.ylim(-0.1, 1.1)
        plt.axis('off')  # Remove axes for sparkline style
        plt.tight_layout()

        # Save the sparkline figure
        os.makedirs(os.path.dirname(sparkline_file), exist_ok=True)
        plt.savefig(sparkline_file)
        plt.close()
        print(f"Sparkline saved to {sparkline_file}")
    except Exception as e:
        print(f"Failed to generate sparkline: {e}")

if __name__ == "__main__":
    main()
