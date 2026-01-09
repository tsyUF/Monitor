import json
import os
from datetime import datetime, timedelta
import pytz

# --- Configuration ---
RESULTS_FILE = "docs/data/results.json"
ARCHIVE_FILE = "docs/data/archive.json"
HISTORY_DAYS = 30
EASTERN_TZ = pytz.timezone('US/Eastern')

def archive_old_data():
    """
    Archives monitoring data older than a specified number of days from a JSON file.
    """
    # Load the current results
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r") as f:
                all_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading {RESULTS_FILE}: {e}")
            return
    else:
        print(f"{RESULTS_FILE} not found.")
        return

    # Load the existing archive
    if os.path.exists(ARCHIVE_FILE):
        try:
            with open(ARCHIVE_FILE, "r") as f:
                archive_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading {ARCHIVE_FILE}: {e}. Starting with an empty archive.")
            archive_data = []
    else:
        archive_data = []

    # Identify old and new records
    cutoff_date = datetime.now(EASTERN_TZ) - timedelta(days=HISTORY_DAYS)
    new_results = []
    old_results = []

    for entry in all_data:
        entry_timestamp = datetime.fromisoformat(entry['timestamp'])
        # If the timestamp is naive, assume it's in the Eastern timezone
        if entry_timestamp.tzinfo is None:
            entry_timestamp = EASTERN_TZ.localize(entry_timestamp)

        if entry_timestamp < cutoff_date:
            old_results.append(entry)
        else:
            new_results.append(entry)

    # Append old records to the archive
    updated_archive = archive_data + old_results

    # Save the updated archive
    try:
        with open(ARCHIVE_FILE, "w") as f:
            json.dump(updated_archive, f, indent=2)
        print(f"Appended {len(old_results)} records to {ARCHIVE_FILE}.")
    except IOError as e:
        print(f"Error writing to {ARCHIVE_FILE}: {e}")

    # Save the pruned results
    try:
        with open(RESULTS_FILE, "w") as f:
            json.dump(new_results, f, indent=2)
        print(f"Saved {len(new_results)} records to {RESULTS_FILE}.")
    except IOError as e:
        print(f"Error writing to {RESULTS_FILE}: {e}")

if __name__ == "__main__":
    archive_old_data()
