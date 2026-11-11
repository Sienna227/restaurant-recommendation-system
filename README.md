# Restaurant Recommendation & Map Visualization System

A university course project that combines C and Python to provide restaurant recommendations, location selection, distance processing, and map visualization.

## Project Overview

The system is designed to help users explore restaurant options around a selected location. It combines a C-based recommendation program with Python utilities for location handling, distance processing, and route/map visualization.

## Key Features

- **Restaurant Recommendation:** A C program for restaurant recommendation based on the project's implemented logic.
- **Location Selection:** Python utility for selecting a user location.
- **Distance Processing:** Processes restaurant and distance data stored in CSV files.
- **Route Visualization:** Generates a map to visualize routes between locations.
- **Top-5 Restaurant Map:** Displays selected restaurants on an interactive map.

## Tech Stack

- C
- Python
- CSV data processing
- Tkinter GUI
- Folium map visualization
- Geopy and OpenStreetMap-related tools

## Project Structure

| File | Description |
|---|---|
| `restaurant_recommender.c` | C-based restaurant recommendation program |
| `main_ui.py` | Python graphical interface |
| `choose_location.py` | Location selection utility |
| `update_route_distances.py` | Restaurant and distance data processing |
| `show_route.py` | Route visualization |
| `show_top5_map.py` | Top-5 restaurant map visualization |
| `Restaurant_core.csv` | Core restaurant data |
| `Restaurant_runtime.csv` | Runtime restaurant data |

## Notes

This project was developed as part of a university course. Running the complete system may require additional Python packages, compatible input data, and local configuration. Map and geolocation features may also depend on external services.

## Learning Outcomes

- Combining C and Python components in one project
- Working with structured CSV data
- Implementing location-related data processing
- Integrating recommendation logic with map visualization
## Setup

### Requirements

- Python 3.10 or a compatible version supported by the listed packages
- A working Tkinter installation
- Required CSV data files for the selected feature
- Internet access for geocoding and map-related features

### Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### Run the GUI

```bash
python main_ui.py
```

The GUI provides options for random recommendations, favorites, customized recommendations, and settings. Some options may require additional local data files and the C recommendation program.

### Run Notes

- `Restaurant_core.csv` and `Restaurant_runtime.csv` contain restaurant data used by the project.
- Map and route features may require additional input CSV files, location data, and access to external map services.
- `user_settings.txt` and other local configuration or cache files may be generated during execution.
- The project has not been verified as a clean installation on every operating system. Additional configuration may be required.
