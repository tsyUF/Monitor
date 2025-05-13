# Monitor

This repository monitors external spaces by pinging a specified host and visualizing the results. It is based on https://autonomousecon.substack.com/p/build-a-self-updating-landing-page

## Features and Technologies
The repository includes features such as status logging to status_log.csv and visualization through a generated image file (docs/sparkline.png). Given that it is implemented entirely in Python, it likely leverages libraries for file handling, network requests, and visualization. The project also hints at hosting visual results through GitHub Pages at https://tsyuf.github.io/Monitor/. This makes it a lightweight tool for real-time monitoring and reporting of host statuses.

- Pings the host `us-east-2.console.aws.amazon.com` (default).
- Logs the status (`Up` or `Down`) in `status_log.csv`.
- Generates a sparkline visualization in `docs/sparkline.png`.

## How to Run Locally
1. Clone the repository:
   ```bash
   git clone https://github.com/tsyUF/Monitor.git

## EVENTUALLY you can go here:
https://tsyuf.github.io/Monitor/


## Purpose of the Repository
This repository is designed to monitor external spaces by pinging a specified host and visualizing the results. It provides a mechanism to track the availability of a host (defaulting to us-east-2.console.aws.amazon.com) and logs its status in a CSV file. Additionally, it generates a sparkline visualization to represent the monitoring data. The project is inspired by an article on creating self-updating landing pages.


