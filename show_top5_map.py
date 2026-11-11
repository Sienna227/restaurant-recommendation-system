# 현재 위치와 상위 5개 추천 식당을 지도에 표시하는 코드입니다.
# C 프로그램에서 top5_map_input.csv를 만든 뒤 이 파일을 호출합니다.

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


def read_restaurants(path):
    restaurants = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Name"):
                restaurants.append(row)
    return restaurants


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
            key = row.get("Location", "")
            if key:
                cache[key] = row
    return cache


def save_cache(cache):
    with CACHE_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["Location", "lat", "lon"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for key, value in cache.items():
            writer.writerow({
                "Location": key,
                "lat": value.get("lat", ""),
                "lon": value.get("lon", ""),
            })


def valid_number(value):
    try:
        number = float(value)
        return number != 0.0
    except Exception:
        return False


def geocode_address(address):
    # geopy는 지도 버튼을 눌렀을 때 좌표가 비어 있는 식당에만 호출됩니다.
    try:
        from geopy.geocoders import Nominatim
    except Exception:
        return None, None

    try:
        geolocator = Nominatim(user_agent="hyehwa_restaurant_project", timeout=10)
        location = geolocator.geocode(address)
        if location is None:
            location = geolocator.geocode("서울 " + address)
        if location is None:
            return None, None
        return location.latitude, location.longitude
    except Exception:
        return None, None


def fill_location(restaurants):
    cache = read_cache()
    changed = False

    for rest in restaurants:
        if valid_number(rest.get("lat")) and valid_number(rest.get("lon")):
            continue

        address = rest.get("Location", "")
        if address in cache and valid_number(cache[address].get("lat")) and valid_number(cache[address].get("lon")):
            rest["lat"] = cache[address]["lat"]
            rest["lon"] = cache[address]["lon"]
            continue

        lat, lon = geocode_address(address)
        if lat is not None and lon is not None:
            rest["lat"] = str(lat)
            rest["lon"] = str(lon)
            cache[address] = {"lat": str(lat), "lon": str(lon)}
            changed = True

    if changed:
        save_cache(cache)


def restaurant_popup(idx, rest):
    return (
        f"{idx + 1}. {rest.get('Name')}<br>"
        f"장르: {rest.get('Genre')}<br>"
        f"평점: {rest.get('Rating')}<br>"
        f"도보거리: {rest.get('Distance')}m"
    )


def make_map(restaurants, user_label, user_lat, user_lon):
    import folium

    points = []
    for rest in restaurants:
        if valid_number(rest.get("lat")) and valid_number(rest.get("lon")):
            points.append(rest)

    center_items = [(user_lat, user_lon)]
    center_items += [(float(r["lat"]), float(r["lon"])) for r in points]
    center_lat = sum(item[0] for item in center_items) / len(center_items)
    center_lon = sum(item[1] for item in center_items) / len(center_items)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=16)

    folium.Marker(
        [user_lat, user_lon],
        popup=f"현재 위치: {user_label}",
        tooltip="현재 위치",
        icon=folium.Icon(color="red", icon="user"),
    ).add_to(m)

    if not points:
        print("지도에 표시할 식당 위치를 찾을 수 없습니다....")
    else:
        try:
            import geopandas as gpd
            from shapely.geometry import Point

            gdf = gpd.GeoDataFrame(
                points,
                geometry=[Point(float(r["lon"]), float(r["lat"])) for r in points],
                crs="EPSG:4326",
            )

            for idx, row in gdf.iterrows():
                folium.Marker(
                    [row.geometry.y, row.geometry.x],
                    popup=restaurant_popup(idx, row),
                    tooltip=row.get("Name"),
                    icon=folium.Icon(color="blue", icon="cutlery", prefix="fa"),
                ).add_to(m)
        except Exception:
            for idx, rest in enumerate(points):
                folium.Marker(
                    [float(rest["lat"]), float(rest["lon"])],
                    popup=restaurant_popup(idx, rest),
                    tooltip=rest.get("Name"),
                    icon=folium.Icon(color="blue", icon="cutlery", prefix="fa"),
                ).add_to(m)

    out_path = BASE_DIR / "top5_restaurants_map.html"
    m.save(out_path)
    open_html(out_path)
    print("지도를 열었습니다....")


def main():
    if len(sys.argv) < 2:
        input_file = BASE_DIR / "top5_map_input.csv"
    else:
        input_file = Path(sys.argv[1])
        if not input_file.is_absolute():
            input_file = BASE_DIR / input_file

    if len(sys.argv) >= 3:
        location_file = Path(sys.argv[2])
    else:
        location_file = USER_LOCATION_FILE

    restaurants = read_restaurants(input_file)
    fill_location(restaurants)
    user_label, user_lat, user_lon = read_user_location(location_file)
    make_map(restaurants, user_label, user_lat, user_lon)


if __name__ == "__main__":
    main()
