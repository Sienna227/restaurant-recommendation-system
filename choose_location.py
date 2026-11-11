import csv
import json
import re
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
LOCATION_FILE = BASE_DIR / "user_location.txt"
FAVORITE_FILE = BASE_DIR / "favorite_locations.csv"

DEFAULT_LABEL = "혜화역"
DEFAULT_LAT = 37.582336
DEFAULT_LON = 127.001844


def slugify(text):
    text = (text or "favorite").strip()
    text = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", text)
    text = text.strip("_")
    return text or "favorite"


def favorite_restaurant_file(label):
    return f"Restaurant_favorite_{slugify(label)}.csv"


def save_user_location(label, lat, lon, source, favorite_label="", restaurant_file="", save_favorite="no"):
    with LOCATION_FILE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "lat", "lon", "source", "favorite_label", "restaurant_file", "save_favorite"])
        writer.writerow([
            label,
            f"{lat:.7f}",
            f"{lon:.7f}",
            source,
            favorite_label,
            restaurant_file,
            save_favorite,
        ])


def read_favorites():
    favorites = []
    if not FAVORITE_FILE.exists():
        return favorites

    with FAVORITE_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = (row.get("label") or "").strip()
            if label:
                favorites.append(row)
    return favorites


class LocationHandler(BaseHTTPRequestHandler):
    received = None

    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/":
            self.send_response(404)
            self.end_headers()
            return

        html = """
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>현재 위치 확인</title>
<style>
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 32px; line-height: 1.7; }
button { font-size: 18px; padding: 11px 18px; border-radius: 8px; }
#status { margin-top: 22px; font-weight: bold; }
</style>
</head>
<body>
<h2>혜화 식당 추천</h2>
<p>아래 버튼을 누르고 위치 권한을 허용해주세요.</p>
<button onclick="shareLocation()">현재 위치 사용하기</button>
<div id="status">대기 중입니다.</div>
<script>
function shareLocation(){
    const status = document.getElementById('status');
    if(!navigator.geolocation){
        status.innerText = '이 브라우저에서는 위치 확인을 지원하지 않습니다.';
        return;
    }
    status.innerText = '현재 위치를 확인하고 있습니다.';
    navigator.geolocation.getCurrentPosition(function(pos){
        fetch('/location', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                lat: pos.coords.latitude,
                lon: pos.coords.longitude
            })
        }).then(function(){
            status.innerText = '완료되었습니다. 이 창을 닫고 터미널로 돌아가세요.';
        });
    }, function(err){
        status.innerText = '위치 확인에 실패했습니다. 다시 시도해주세요.';
    }, {enableHighAccuracy: true, timeout: 15000, maximumAge: 0});
}
</script>
</body>
</html>
"""
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/location":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            body = json.loads(raw)
            lat = float(body["lat"])
            lon = float(body["lon"])
            LocationHandler.received = (lat, lon)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception:
            self.send_response(400)
            self.end_headers()


def share_location_by_browser():
    LocationHandler.received = None
    try:
        server = HTTPServer(("127.0.0.1", 0), LocationHandler)
    except Exception:
        print("현재 위치 확인을 시작하지 못했습니다....")
        return None, None

    url = f"http://127.0.0.1:{server.server_port}/"
    print("브라우저에서 위치 권한을 허용해주세요.")
    opened = webbrowser.open(url)
    if not opened:
        print("브라우저가 열리지 않으면 아래 주소를 직접 열어주세요.")
        print(url)

    server.timeout = 1
    start = time.time()
    while time.time() - start < 60:
        server.handle_request()
        if LocationHandler.received is not None:
            server.server_close()
            return LocationHandler.received

    server.server_close()
    print("시간이 초과되었습니다....")
    return None, None


def choose_default():
    save_user_location(DEFAULT_LABEL, DEFAULT_LAT, DEFAULT_LON, "default")
    print(f"현재 위치를 {DEFAULT_LABEL} 기준으로 설정했습니다.")


def choose_favorite():
    favorites = read_favorites()
    if not favorites:
        print("저장된 즐겨찾기 위치가 없습니다....")
        choose_default()
        return

    print("\n[즐겨찾기 위치]")
    for i, row in enumerate(favorites, start=1):
        print(f"{i}. {row.get('label', '')}")
    print("0. 돌아가기")

    try:
        idx = int(input("선택 >> ").strip())
    except Exception:
        idx = 0

    if idx <= 0 or idx > len(favorites):
        choose_default()
        return

    row = favorites[idx - 1]
    label = row.get("label", "즐겨찾기 위치")
    try:
        lat = float(row.get("lat", DEFAULT_LAT))
        lon = float(row.get("lon", DEFAULT_LON))
    except Exception:
        choose_default()
        return

    restaurant_file = row.get("restaurant_file", "") or favorite_restaurant_file(label)
    save_user_location(label, lat, lon, "favorite", label, restaurant_file, "no")
    print(f"현재 위치를 {label} 기준으로 설정했습니다.")


def ask_save_favorite(lat, lon):
    try:
        answer = input("이 위치를 즐겨찾기에 저장할까요? (y/n) >> ").strip().lower()
    except EOFError:
        answer = "n"

    if answer not in ["y", "yes"]:
        save_user_location("현재 위치", lat, lon, "browser", "", "", "no")
        print("현재 위치로 진행합니다.")
        return

    try:
        label = input("즐겨찾기 이름 >> ").strip()
    except EOFError:
        label = "내 위치"

    if label == "":
        label = "내 위치"

    restaurant_file = favorite_restaurant_file(label)
    save_user_location(label, lat, lon, "browser", label, restaurant_file, "yes")
    print(f"'{label}' 이름으로 저장합니다.")


def main():
    print("\n========== 현재 위치 ==========")
    print("1. 혜화역")
    print("2. 즐겨찾기 위치")
    print("3. 위치 권한 허용")

    try:
        choice = input("선택 >> ").strip()
    except EOFError:
        choice = "1"

    if choice == "2":
        choose_favorite()
    elif choice == "3":
        lat, lon = share_location_by_browser()
        if lat is None or lon is None:
            print("현재 위치를 가져오지 못했습니다....")
            choose_default()
        else:
            print("현재 위치를 확인했습니다.")
            ask_save_favorite(lat, lon)
    else:
        choose_default()

    print("==============================\n")


if __name__ == "__main__":
    main()
