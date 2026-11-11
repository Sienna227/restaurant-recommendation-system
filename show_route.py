# 특정 식당까지의 경로를 사용자가 요청했을 때만 표시합니다.

import csv
import sys
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CACHE_FILE = BASE_DIR / "location_cache.csv"
USER_LOCATION_FILE = BASE_DIR / "user_location.txt"

DEFAULT_LABEL = "혜화역"
DEFAULT_LAT = 37.582336
DEFAULT_LON = 127.001844


def open_html(path):
    path = Path(path).resolve()
    try:
        webbrowser.open(path.as_uri())
    except Exception:
        webbrowser.open(str(path))


def valid_number(value):
    try:
        number = float(value)
        return number != 0.0
    except Exception:
        return False


def read_one(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            return row
    return None


def read_user_location(path=None):
    if path is None:
        path = USER_LOCATION_FILE
    path = Path(path)
    if not path.is_absolute():
        path = BASE_DIR / path
    if not path.exists():
        return DEFAULT_LABEL, DEFAULT_LAT, DEFAULT_LON

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                label = row.get("label", DEFAULT_LABEL)
                lat = float(row.get("lat", DEFAULT_LAT))
                lon = float(row.get("lon", DEFAULT_LON))
                return label, lat, lon
    except Exception:
        pass

    return DEFAULT_LABEL, DEFAULT_LAT, DEFAULT_LON


def read_cache():
    cache = {}
    if not CACHE_FILE.exists():
        return cache
    with CACHE_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Location"):
                cache[row["Location"]] = row
    return cache


def save_cache(cache):
    with CACHE_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Location", "lat", "lon"])
        writer.writeheader()
        for key, value in cache.items():
            writer.writerow({"Location": key, "lat": value.get("lat", ""), "lon": value.get("lon", "")})


def geocode_address(address):
    try:
        from geopy.geocoders import Nominatim
    except Exception:
        return None, None

    try:
        geolocator = Nominatim(user_agent="hyehwa_route_project", timeout=10)
        location = geolocator.geocode(address)
        if location is None:
            location = geolocator.geocode("서울 " + address)
        if location is None:
            return None, None
        return location.latitude, location.longitude
    except Exception:
        return None, None


def ensure_location(rest):
    if valid_number(rest.get("lat")) and valid_number(rest.get("lon")):
        return float(rest["lat"]), float(rest["lon"])

    address = rest.get("Location", "")
    cache = read_cache()
    if address in cache and valid_number(cache[address].get("lat")) and valid_number(cache[address].get("lon")):
        return float(cache[address]["lat"]), float(cache[address]["lon"])

    lat, lon = geocode_address(address)
    if lat is not None and lon is not None:
        cache[address] = {"lat": str(lat), "lon": str(lon)}
        save_cache(cache)
        return lat, lon

    return None, None


def marker_only_map(rest, start_label, start_lat, start_lon, end_lat, end_lon, reason):
    import folium

    m = folium.Map(location=[(start_lat + end_lat) / 2, (start_lon + end_lon) / 2], zoom_start=16)
    folium.Marker(
        [start_lat, start_lon],
        popup=f"현재 위치: {start_label}",
        tooltip="현재 위치",
        icon=folium.Icon(color="red", icon="user"),
    ).add_to(m)
    folium.Marker(
        [end_lat, end_lon],
        popup=rest.get("Name"),
        tooltip=rest.get("Name"),
        icon=folium.Icon(color="blue", icon="cutlery", prefix="fa"),
    ).add_to(m)

    out_path = BASE_DIR / "route_map.html"
    m.save(out_path)
    open_html(out_path)
    print("경로를 그리지 못해서 위치만 표시했습니다.")
    print("지도를 열었습니다....")


def route_map(rest, start_label, start_lat, start_lon, end_lat, end_lon):
    try:
        import folium
        import osmnx as ox

        center_lat = (start_lat + end_lat) / 2
        center_lon = (start_lon + end_lon) / 2

        G = ox.graph_from_point((center_lat, center_lon), dist=2500, network_type="walk", simplify=True)
        start_node = ox.nearest_nodes(G, start_lon, start_lat)
        end_node = ox.nearest_nodes(G, end_lon, end_lat)
        route = ox.shortest_path(G, start_node, end_node, weight="length")

        if route is None:
            marker_only_map(rest, start_label, start_lat, start_lon, end_lat, end_lon, "route is None")
            return

        m = folium.Map(location=[center_lat, center_lon], zoom_start=16)
        folium.Marker(
            [start_lat, start_lon],
            popup=f"현재 위치: {start_label}",
            tooltip="현재 위치",
            icon=folium.Icon(color="red", icon="user"),
        ).add_to(m)
        folium.Marker(
            [end_lat, end_lon],
            popup=rest.get("Name"),
            tooltip=rest.get("Name"),
            icon=folium.Icon(color="blue", icon="cutlery", prefix="fa"),
        ).add_to(m)
        folium.PolyLine([(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route]).add_to(m)

        out_path = BASE_DIR / "route_map.html"
        m.save(out_path)
        open_html(out_path)
        print("지도를 열었습니다....")
    except Exception as exc:
        marker_only_map(rest, start_label, start_lat, start_lon, end_lat, end_lon, str(exc))


def main():
    if len(sys.argv) < 2:
        input_file = BASE_DIR / "route_input.csv"
    else:
        input_file = Path(sys.argv[1])
        if not input_file.is_absolute():
            input_file = BASE_DIR / input_file

    if len(sys.argv) >= 3:
        location_file = Path(sys.argv[2])
    else:
        location_file = USER_LOCATION_FILE

    rest = read_one(input_file)
    if rest is None:
        print("선택한 식당 정보를 찾을 수 없습니다....")
        return

    start_label, start_lat, start_lon = read_user_location(location_file)
    end_lat, end_lon = ensure_location(rest)
    if end_lat is None or end_lon is None:
        print("식당 위치를 찾을 수 없습니다....")
        return

    route_map(rest, start_label, start_lat, start_lon, end_lat, end_lon)


if __name__ == "__main__":
    main()
