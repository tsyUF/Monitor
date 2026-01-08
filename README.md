# Multi-Target Monitoring System

This project implements a multi-target monitoring system that checks a list of specified hosts (IP addresses or URLs) to check their availability. It uses a Python script to perform the monitoring, store historical uptime data, and generate a static HTML status page. The system is designed to be run via GitHub Actions, which automates the monitoring and deployment.

## Features

*   Monitors multiple IP addresses and/or URLs via HTTPS requests.
*   Stores up to 30 days of historical uptime data in a JSON file.
*   Generates individual status bar chart images for each target, visualizing its uptime over the last 30 days.
*   Generates a clean, self-contained `docs/index.html` report with a static footer.
*   Integrates with GitHub Actions for scheduled and manual monitoring runs.
*   Configuration of monitored targets, including custom display names, is managed through a simple text file.

## How it Works

1.  **Trigger**: Monitoring is triggered by a GitHub Actions workflow defined in `.github/workflows/run-monitor.yml`. This runs automatically on any push to the `main` branch, on an hourly schedule, or can be triggered manually.
2.  **Target Configuration**: The script reads a list of targets from the `monitoring_targets.txt` file in the root of the repository.
3.  **Monitoring Script**: The workflow executes the Python script `scripts/monitor.py`.
4.  **Data Collection**: `scripts/monitor.py` sends an HTTPS request to each target, records its status ("Up" or "Down") and timestamp.
5.  **Data Storage**: The script loads existing historical data from `docs/data/results.json`, appends the new results, and prunes any data older than 30 days.
6.  **Output Generation**:
    *   Individual bar chart images (`docs/chart_*.png`) are generated for each target, visualizing its uptime over the last 30 days.
    *   A static `docs/index.html` file is generated, displaying the latest status and the historical bar chart for each target. A static footer with a link to the Salesforce status page is also included.
7.  **Deployment**: The GitHub Actions workflow uses the `stefanzweifel/git-auto-commit-action` to automatically commit the updated contents of the `docs` directory directly back to the `main` branch.

## Configuration

To add or change a target, simply edit the `monitoring_targets.txt` file and commit the change to the `main` branch. The order of the services on the status page is determined by the order of the lines in this file. The monitoring workflow will automatically run and update the status page.

### Format
You can specify targets in two ways:
1.  **Simple URL**: Just the URL or IP address on a line. The URL itself will be used as the display name on the report.
2.  **Custom Display Name**: Use the format `DisplayName=URL`. This allows you to set a custom, human-readable name for each target on the report.

**Example `monitoring_targets.txt` with Custom Display Names:**
```
Salesforce=uff.lightning.force.com
Snowflake=UFL-ADVANCEMENT.snowflakecomputing.com
Quickbase=ufadvancement.quickbase.com
myUFL=my.ufl.edu
Google=google.com
```

## Output Files

The primary outputs of the monitoring process are:

*   **`docs/index.html`**: The main dashboard and status report.
*   **`docs/data/results.json`**: Contains the raw monitoring data for the last 30 days.
*   **`docs/chart_*.png`**: A set of PNG images, where each image is a bar chart visualizing the recent uptime history for a specific target.

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

The monitoring dashboard can be viewed by opening `docs/index.html` in a web browser. When deployed, it is available at the repository's GitHub Pages URL.
