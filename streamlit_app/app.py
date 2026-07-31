from pathlib import Path
import json
from datetime import datetime
import pandas as pd
import streamlit as st

# Paths (app lives in streamlit_app/)
ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "docs" / "data" / "results.json"
TARGETS_PATH = ROOT / "monitoring_targets.txt"
CHARTS_DIR = ROOT / "docs"

st.set_page_config(page_title="Uptime Monitor", layout="wide")

def load_targets(path: Path):
    targets = []
    if not path.exists():
        return targets
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if "=" in line:
            name, url = line.split("=", 1)
            targets.append((name.strip(), url.strip()))
        else:
            targets.append((line, line))
    return targets

def load_results(path: Path):
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []

def latest_status_map(all_data):
    latest = {}
    for entry in sorted(all_data, key=lambda x: x["timestamp"], reverse=True):
        if entry["resource"] not in latest:
            latest[entry["resource"]] = entry
    return latest

def sanitize(name: str):
    return "".join(c if c.isalnum() else "_" for c in name)

def compute_uptime_pct(df: pd.DataFrame):
    if df.empty:
        return None
    n = len(df)
    up = (df["status"] == "Up").sum()
    return round(up / n * 100, 2)

# Load data
targets = load_targets(TARGETS_PATH)
results = load_results(RESULTS_PATH)
latest_map = latest_status_map(results)

st.title("Uptime Monitor — Interactive Dashboard")

# Top-level summary
col1, col2, col3 = st.columns(3)
last_checked = "N/A"
if results:
    try:
        last_checked = max(datetime.fromisoformat(d["timestamp"]) for d in results).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        last_checked = "parse error"
col1.metric("Last checked (approx)", last_checked)

df = pd.DataFrame(results) if results else pd.DataFrame(columns=["resource","status","timestamp"])
if not df.empty:
    overall_uptime = round((df["status"] == "Up").sum() / len(df) * 100, 2)
    col2.metric("Overall sample uptime %", f"{overall_uptime}%")
else:
    col2.metric("Overall sample uptime %", "N/A")

col3.metric("Targets monitored", len(targets))

st.sidebar.header("Target selector")
target_options = ["All targets"] + [f"{name} — {url}" for name, url in targets]
selected = st.sidebar.selectbox("Choose target", target_options)

def show_target_view(display_name, resource_url):
    st.header(display_name)
    last = latest_map.get(resource_url)
    status = last["status"] if last else "Unknown"
    st.subheader(f"Current status: {status}")
    # show chart image if present
    chart_file = CHARTS_DIR / f"chart_{sanitize(resource_url)}.png"
    if chart_file.exists():
        st.image(str(chart_file), use_column_width=True)
    else:
        st.info("No pre-generated chart image found. Showing computed stats below.")
    # computed stats
    df_r = df[df["resource"] == resource_url].copy()
    if not df_r.empty:
        df_r["timestamp"] = pd.to_datetime(df_r["timestamp"])
        uptime_pct = compute_uptime_pct(df_r)
        st.metric("Uptime (sample)", f"{uptime_pct}%")
        # show recent history table
        st.dataframe(df_r.sort_values("timestamp", ascending=False).head(100), use_container_width=True)
    else:
        st.write("No historical data for this target.")

if selected == "All targets":
    st.header("All targets")
    cols = st.columns(3)
    for i, (display_name, resource_url) in enumerate(targets):
        c = cols[i % 3]
        last = latest_map.get(resource_url)
        status = last["status"] if last else "Unknown"
        pct = None
        df_r = df[df["resource"] == resource_url]
        if not df_r.empty:
            pct = compute_uptime_pct(df_r)
        with c:
            st.subheader(display_name)
            st.write(resource_url)
            st.write(f"Status: **{status}**")
            st.write(f"Uptime (sample): **{pct if pct is not None else 'N/A'}%**")
            chart_file = CHARTS_DIR / f"chart_{sanitize(resource_url)}.png"
            if chart_file.exists():
                st.image(str(chart_file))
            st.markdown("---")
else:
    # parse selection
    sel_name, sel_url = selected.split(" — ", 1)
    show_target_view(sel_name, sel_url)
