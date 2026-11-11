import csv
import math
import shutil
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CORE_FILE = BASE_DIR / "Restaurant_core.csv"
RUNTIME_FILE = BASE_DIR / "Restaurant_runtime.csv"
DEFAULT_RESTAURANT_FILE = BASE_DIR / "Restaurant_hyehwa.csv"
DEFAULT_DISTANCE_FILE = BASE_DIR / "distance_hyehwa.csv"
USER_LOCATION_FILE = BASE_DIR / "user_location.txt"
LOCATION_CACHE_FILE = BASE_DIR / "location_cache.csv"
DISTANCE_CACHE_FILE = BASE_DIR / "distance_cache.csv"
FAVORITE_FILE = BASE_DIR / "favorite_locations.csv"

DEFAULT_LABEL = "혜화역"
DEFAULT_LAT = 37.582336
DEFAULT_LON = 127.001844


def safe_float(value, default=None):
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def read_user_location():
    if not USER_LOCATION_FILE.exists():
        return {
            "label": DEFAULT_LABEL,
            "lat": DEFAULT_LAT,
            "lon": DEFAULT_LON,
            "source": "default",
            "favorite_label": "",
            "restaurant_file": "",
            "save_favorite": "no",
        }

    try:
        with USER_LOCATION_FILE.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row["label"] = row.get("label") or DEFAULT_LABEL
                row["lat"] = safe_float(row.get("lat"), DEFAULT_LAT)
                row["lon"] = safe_float(row.get("lon"), DEFAULT_LON)
                row["source"] = row.get("source") or "default"
                row["favorite_label"] = row.get("favorite_label") or ""
                row["restaurant_file"] = row.get("restaurant_file") or ""
                row["save_favorite"] = row.get("save_favorite") or "no"
                return row
    except Exception:
        pass

    return {
        "label": DEFAULT_LABEL,
        "lat": DEFAULT_LAT,
        "lon": DEFAULT_LON,
        "source": "default",
        "favorite_label": "",
        "restaurant_file": "",
        "save_favorite": "no",
    }


def read_csv_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames or []


def write_csv_rows(path, rows, fields):
    fieldnames = list(fields)
    for extra in ["Distance_Source"]:
        if extra not in fieldnames:
            fieldnames.append(extra)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def ensure_default_distance_files():
    if DEFAULT_RESTAURANT_FILE.exists() and DEFAULT_DISTANCE_FILE.exists():
        return

    if not CORE_FILE.exists():
        print("식당 데이터 파일을 찾지 못했습니다....")
        sys.exit(1)

    rows, fields = read_csv_rows(CORE_FILE)
    for row in rows:
        row["Distance_Source"] = "혜화역"

    write_csv_rows(DEFAULT_RESTAURANT_FILE, rows, fields)

    with DEFAULT_DISTANCE_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "Name", "Distance"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "id": row.get("id", ""),
                "Name": row.get("Name", ""),
                "Distance": row.get("Distance", ""),
            })


def read_location_cache():
    cache = {}
    if not LOCATION_CACHE_FILE.exists():
        return cache
    with LOCATION_CACHE_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row.get("Location", "").strip()
            if key:
                cache[key] = row
    return cache


def save_location_cache(cache):
    with LOCATION_CACHE_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Location", "lat", "lon"])
        writer.writeheader()
        for key, value in cache.items():
            writer.writerow({
                "Location": key,
                "lat": value.get("lat", ""),
                "lon": value.get("lon", ""),
            })


def geocode_address(address, cache):
    address = (address or "").strip()
    if address == "":
        return None, None

    if address in cache:
        lat = safe_float(cache[address].get("lat"))
        lon = safe_float(cache[address].get("lon"))
        if lat is not None and lon is not None:
            return lat, lon

    try:
        from geopy.geocoders import Nominatim
    except Exception:
        return None, None

    try:
        geolocator = Nominatim(user_agent="hyehwa_food_project", timeout=10)
        location = geolocator.geocode(address)
        if location is None:
            location = geolocator.geocode("서울 " + address)
        if location is None:
            return None, None
        cache[address] = {"lat": str(location.latitude), "lon": str(location.longitude)}
        return location.latitude, location.longitude
    except Exception:
        return None, None


def ensure_restaurant_locations(rows):
    cache = read_location_cache()
    changed = False

    for row in rows:
        lat = safe_float(row.get("lat"))
        lon = safe_float(row.get("lon"))
        if lat is not None and lon is not None and lat != 0.0 and lon != 0.0:
            continue

        lat, lon = geocode_address(row.get("Location", ""), cache)
        if lat is not None and lon is not None:
            row["lat"] = f"{lat:.7f}"
            row["lon"] = f"{lon:.7f}"
            changed = True

    if changed:
        save_location_cache(cache)


def source_key(lat, lon):
    return f"{lat:.5f},{lon:.5f}"


def rest_key(row):
    rest_id = (row.get("id") or "").strip()
    name = (row.get("Name") or "").strip()
    lat = safe_float(row.get("lat"), 0.0)
    lon = safe_float(row.get("lon"), 0.0)
    return f"{rest_id}|{name}|{lat:.5f},{lon:.5f}"


def read_distance_cache():
    cache = {}
    if not DISTANCE_CACHE_FILE.exists():
        return cache
    with DISTANCE_CACHE_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row.get("source_key", ""), row.get("rest_key", ""))
            distance = safe_float(row.get("distance_m"))
            if key[0] and key[1] and distance is not None:
                cache[key] = row
    return cache


def save_distance_cache(cache):
    fieldnames = [
        "source_key", "rest_key", "source_label", "rest_name",
        "start_lat", "start_lon", "end_lat", "end_lon",
        "distance_m", "updated_at"
    ]
    with DISTANCE_CACHE_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for value in cache.values():
            writer.writerow({name: value.get(name, "") for name in fieldnames})


def estimate_radius(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def calculate_missing_distances(rows, start_label, start_lat, start_lon, cache):
    s_key = source_key(start_lat, start_lon)
    missing = []

    for row in rows:
        lat = safe_float(row.get("lat"))
        lon = safe_float(row.get("lon"))
        if lat is None or lon is None or lat == 0.0 or lon == 0.0:
            row["Distance_Source"] = "기존 거리"
            continue

        key = (s_key, rest_key(row))
        if key in cache:
            row["Distance"] = cache[key]["distance_m"]
            row["Distance_Source"] = "저장된 거리"
        else:
            missing.append(row)

    if not missing:
        return

    try:
        import networkx as nx
        import osmnx as ox
    except Exception:
        print("거리 확인이 어려워 기존 값을 사용합니다....")
        for row in missing:
            row["Distance_Source"] = "기존 거리"
        return

    max_radius = 1500.0
    for row in missing:
        lat = safe_float(row.get("lat"))
        lon = safe_float(row.get("lon"))
        if lat is not None and lon is not None:
            max_radius = max(max_radius, estimate_radius(start_lat, start_lon, lat, lon) + 1200.0)
    max_radius = min(max_radius, 7000.0)

    print("처음 사용하는 위치라 준비 시간이 조금 걸릴 수 있습니다.")
    print("잠시만 기다려주세요....")

    try:
        G = ox.graph_from_point((start_lat, start_lon), dist=max_radius, network_type="walk", simplify=True)
        start_node = ox.nearest_nodes(G, start_lon, start_lat)
    except Exception:
        print("거리 확인에 실패해서 기존 값을 사용합니다....")
        for row in missing:
            row["Distance_Source"] = "기존 거리"
        return

    changed = False
    for row in missing:
        lat = safe_float(row.get("lat"))
        lon = safe_float(row.get("lon"))
        if lat is None or lon is None:
            continue
        try:
            end_node = ox.nearest_nodes(G, lon, lat)
            distance = nx.shortest_path_length(G, start_node, end_node, weight="length")
            row["Distance"] = f"{float(distance):.0f}"
            row["Distance_Source"] = "새로 계산한 거리"

            key = (s_key, rest_key(row))
            cache[key] = {
                "source_key": s_key,
                "rest_key": key[1],
                "source_label": start_label,
                "rest_name": row.get("Name", ""),
                "start_lat": f"{start_lat:.7f}",
                "start_lon": f"{start_lon:.7f}",
                "end_lat": f"{lat:.7f}",
                "end_lon": f"{lon:.7f}",
                "distance_m": f"{float(distance):.0f}",
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            changed = True
        except Exception:
            row["Distance_Source"] = "기존 거리"

    if changed:
        save_distance_cache(cache)


def register_favorite(label, lat, lon, restaurant_file):
    existing = []
    if FAVORITE_FILE.exists():
        with FAVORITE_FILE.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            existing = list(reader)

    found = False
    for row in existing:
        if row.get("label") == label:
            row["lat"] = f"{lat:.7f}"
            row["lon"] = f"{lon:.7f}"
            row["restaurant_file"] = restaurant_file
            row["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            found = True
            break

    if not found:
        existing.append({
            "label": label,
            "lat": f"{lat:.7f}",
            "lon": f"{lon:.7f}",
            "restaurant_file": restaurant_file,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    with FAVORITE_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["label", "lat", "lon", "restaurant_file", "updated_at"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in existing:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def copy_if_exists(src, dst):
    if src.exists():
        shutil.copyfile(src, dst)
        return True
    return False


def main():
    ensure_default_distance_files()
    location = read_user_location()
    label = location["label"]
    lat = float(location["lat"])
    lon = float(location["lon"])
    source = location["source"]
    restaurant_file = location.get("restaurant_file", "")
    save_favorite = location.get("save_favorite", "no")
    favorite_label = location.get("favorite_label", "") or label

    if source == "default":
        copy_if_exists(DEFAULT_RESTAURANT_FILE, RUNTIME_FILE)
        print("혜화역 기준으로 불러왔습니다.")
        return

    if source == "favorite" and restaurant_file:
        favorite_path = BASE_DIR / restaurant_file
        if copy_if_exists(favorite_path, RUNTIME_FILE):
            print("즐겨찾기 위치 기준으로 불러왔습니다.")
            return
        print("처음 사용하는 즐겨찾기라 준비 시간이 조금 걸릴 수 있습니다.")

    print(f"현재 위치: {label}")

    rows, fields = read_csv_rows(CORE_FILE)
    ensure_restaurant_locations(rows)
    cache = read_distance_cache()
    calculate_missing_distances(rows, label, lat, lon, cache)
    write_csv_rows(RUNTIME_FILE, rows, fields)
    print("식당 정보를 준비했습니다.")

    if (source == "favorite" and restaurant_file) or save_favorite.lower() in ["yes", "y"]:
        if not restaurant_file:
            restaurant_file = f"Restaurant_favorite_{favorite_label}.csv"
        safe_name = "".join(ch if ch.isalnum() or ch in "_-." else "_" for ch in restaurant_file)
        restaurant_file = safe_name
        shutil.copyfile(RUNTIME_FILE, BASE_DIR / restaurant_file)
        register_favorite(favorite_label, lat, lon, restaurant_file)
        print("즐겨찾기에 저장했습니다.")


if __name__ == "__main__":
    main()
