import platform, subprocess, datetime, csv, os, shutil

# Set host and ping count parameter depending on OS
host = "us-east-2.console.aws.amazon.com"
param = "-n" if platform.system().lower() == "windows" else "-c"
command = ["ping", param, "1", host]

# Check if ping command exists before attempting to run it.
if shutil.which("ping"):
    # Attempt to ping; success if return code 0
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

# Ensure log file exists with header
logfile = "status_log.csv"
if not os.path.exists(logfile):
    with open(logfile, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp","status"])

# Append current result
with open(logfile, "a", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([now, status])
    
import pandas as pd
import matplotlib.pyplot as plt

# Read log and filter last 7 days
df = pd.read_csv("status_log.csv", parse_dates=["timestamp"])
cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=7)

# Make cutoff timezone-naive to match the DataFrame's timestamp column
cutoff = cutoff.tz_localize(None) # Remove timezone information from cutoff

# Use .floor('D') to remove the time component for accurate comparison.
df = df[df["timestamp"] >= cutoff.floor('D')] 

# Map status to numeric values (1 for Up, 0 for Down)
df["value"] = df["status"].map({"Up": 1, "Down": 0})

# Ensure we have 7 days (fill missing)
df = df.set_index("timestamp").resample("6h").last().fillna(method="ffill").fillna(0) # Changed '6H' to '6h'
data = df["value"].tolist()

# Plot sparkline
plt.figure(figsize=(2,0.5))
plt.plot(data, color='tab:green', linewidth=1)
plt.ylim(-0.1,1.1)
plt.axis('off')  # remove axes for sparkline style
plt.tight_layout()

# Save the figure
plt.savefig("sparkline.png")
plt.close()
