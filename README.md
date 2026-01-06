# Multi-Target Monitoring System

This project implements a multi-target monitoring system that pings a list of specified hosts (IP addresses or URLs) to check their availability. It uses a Python script to perform the monitoring, store historical uptime data, and generate a static HTML status page. The system is designed to be run via GitHub Actions, which automates the monitoring and deployment to GitHub Pages.

## Features

*   Monitors multiple IP addresses and/or URLs via ICMP ping.
*   Stores up to 30 days of historical uptime data in a JSON file.
*   Generates individual status sparkline images for each target, visualizing its uptime over the last 30 days.
*   Generates a clean, self-contained `docs/index.html` report.
*   Integrates with GitHub Actions for scheduled and manual monitoring runs.
*   Configuration of monitored targets is managed through a simple text file.

## How it Works

1.  **Trigger**: Monitoring is triggered by a GitHub Actions workflow defined in `.github/workflows/run-monitor.yml`. This can be run manually or on a schedule.
2.  **Target Configuration**: The script reads a list of targets from the `monitoring_targets.txt` file in the root of the repository.
3.  **Monitoring Script**: The workflow executes the Python script `scripts/monitor.py`.
4.  **Data Collection**: `scripts/monitor.py` pings each target, records its status ("Up" or "Down") and timestamp.
5.  **Data Storage**: The script loads existing historical data from `docs/data/results.json`, appends the new results, and prunes any data older than 30 days.
6.  **Output Generation**:
    *   Individual sparkline images (`docs/sparkline_<target_name>.png`) are generated for each target, visualizing its uptime over the last 30 days.
    *   A static `docs/index.html` file is generated, displaying the latest status and the historical sparkline for each target.
7.  **Deployment**: The GitHub Actions workflow uses the `peaceiris/actions-gh-pages` action to automatically deploy the entire contents of the `docs` directory to the `gh-pages` branch, publishing the updated report.

## Configuration

Targets for monitoring are defined in the `monitoring_targets.txt` file.

*   **File to Edit**: `monitoring_targets.txt`
*   **Format**: A list of IP addresses or hostnames, one per line.

**Example `monitoring_targets.txt`:**
```
google.com
8.8.8.8
github.com
```

## Output Files

The primary outputs of the monitoring process are:

*   **`docs/index.html`**: The main dashboard and status report.
*   **`docs/data/results.json`**: Contains the raw monitoring data for the last 30 days.
*   **`docs/sparkline_*.png`**: A set of PNG images, where each image is a sparkline visualizing the recent uptime history for a specific target.

## Running Locally (for Development/Testing)

To run the monitoring script locally:

1.  **Clone the repository**.
2.  **Set up a Python environment**.
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the script**:
    ```bash
    python scripts/monitor.py
    ```
    This will generate the `index.html` report, sparkline images, and update the historical data file in the `docs` directory.

## Viewing the Dashboard

The monitoring dashboard can be viewed by opening `docs/index.html` in a web browser. When deployed via GitHub Pages, it will be available at your GitHub Pages URL.
