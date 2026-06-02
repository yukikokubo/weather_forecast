from __future__ import annotations

import json
import mimetypes
import os
import pathlib
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


ROOT = pathlib.Path(__file__).parent.resolve()
STATIC_DIR = ROOT / "static"
DB_PATH = ROOT / "weather.db"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
JST = timezone(timedelta(hours=9))

DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
    "precipitation_sum",
]

CITY_GROUPS = [
    {
        "region": "北海道・東北",
        "cities": [
            {"name": "札幌", "prefecture": "北海道", "lat": 43.0618, "lon": 141.3545},
            {"name": "青森", "prefecture": "青森県", "lat": 40.8244, "lon": 140.74},
            {"name": "仙台", "prefecture": "宮城県", "lat": 38.2682, "lon": 140.8694},
            {"name": "秋田", "prefecture": "秋田県", "lat": 39.7186, "lon": 140.1024},
        ],
    },
    {
        "region": "関東",
        "cities": [
            {"name": "東京", "prefecture": "東京都", "lat": 35.6762, "lon": 139.6503},
            {"name": "横浜", "prefecture": "神奈川県", "lat": 35.4437, "lon": 139.638},
            {"name": "さいたま", "prefecture": "埼玉県", "lat": 35.8617, "lon": 139.6455},
            {"name": "千葉", "prefecture": "千葉県", "lat": 35.6074, "lon": 140.1065},
            {"name": "水戸", "prefecture": "茨城県", "lat": 36.3659, "lon": 140.4712},
            {"name": "宇都宮", "prefecture": "栃木県", "lat": 36.5551, "lon": 139.8828},
            {"name": "前橋", "prefecture": "群馬県", "lat": 36.3895, "lon": 139.0634},
        ],
    },
    {
        "region": "中部",
        "cities": [
            {"name": "新潟", "prefecture": "新潟県", "lat": 37.9161, "lon": 139.0364},
            {"name": "金沢", "prefecture": "石川県", "lat": 36.5613, "lon": 136.6562},
            {"name": "松本", "prefecture": "長野県", "lat": 36.238, "lon": 137.972},
            {"name": "名古屋", "prefecture": "愛知県", "lat": 35.1815, "lon": 136.9066},
            {"name": "静岡", "prefecture": "静岡県", "lat": 34.9756, "lon": 138.3828},
        ],
    },
    {
        "region": "関西",
        "cities": [
            {"name": "大阪", "prefecture": "大阪府", "lat": 34.6937, "lon": 135.5023},
            {"name": "京都", "prefecture": "京都府", "lat": 35.0116, "lon": 135.7681},
            {"name": "神戸", "prefecture": "兵庫県", "lat": 34.6901, "lon": 135.1955},
        ],
    },
    {
        "region": "中国・四国",
        "cities": [
            {"name": "広島", "prefecture": "広島県", "lat": 34.3853, "lon": 132.4553},
            {"name": "岡山", "prefecture": "岡山県", "lat": 34.6551, "lon": 133.9195},
            {"name": "高松", "prefecture": "香川県", "lat": 34.3428, "lon": 134.0466},
            {"name": "松山", "prefecture": "愛媛県", "lat": 33.8392, "lon": 132.7657},
        ],
    },
    {
        "region": "九州・沖縄",
        "cities": [
            {"name": "福岡", "prefecture": "福岡県", "lat": 33.5902, "lon": 130.4017},
            {"name": "熊本", "prefecture": "熊本県", "lat": 32.8031, "lon": 130.7079},
            {"name": "鹿児島", "prefecture": "鹿児島県", "lat": 31.5966, "lon": 130.5571},
            {"name": "那覇", "prefecture": "沖縄県", "lat": 26.2124, "lon": 127.6792},
        ],
    },
]


def all_cities() -> list[dict[str, object]]:
    cities: list[dict[str, object]] = []
    for group in CITY_GROUPS:
        for city in group["cities"]:
            cities.append({**city, "region": group["region"]})
    return cities


def build_forecast_url(city: dict[str, object]) -> str:
    query = urllib.parse.urlencode(
        {
            "latitude": city["lat"],
            "longitude": city["lon"],
            "daily": ",".join(DAILY_FIELDS),
            "timezone": "Asia/Tokyo",
            "forecast_days": "7",
        }
    )
    return f"https://api.open-meteo.com/v1/forecast?{query}"


def fetch_json(url: str) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": "weather-forecast-demo/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def cache_date() -> str:
    return datetime.now(JST).date().isoformat()


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS forecast_cache (
                cache_date TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            )
            """
        )


def load_cached_forecast() -> dict[str, object] | None:
    init_db()
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            "SELECT payload FROM forecast_cache WHERE cache_date = ?",
            (cache_date(),),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row[0])


def save_cached_forecast(payload: dict[str, object]) -> None:
    init_db()
    payload = {**payload, "cachedAt": datetime.now(JST).isoformat(timespec="seconds")}
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO forecast_cache (cache_date, payload, fetched_at)
            VALUES (?, ?, ?)
            ON CONFLICT(cache_date) DO UPDATE SET
                payload = excluded.payload,
                fetched_at = excluded.fetched_at
            """,
            (cache_date(), json.dumps(payload, ensure_ascii=False), payload["cachedAt"]),
        )


def get_forecast_payload() -> dict[str, object]:
    cached = load_cached_forecast()
    if cached is not None:
        return cached

    payload = make_forecast_payload()
    save_cached_forecast(payload)
    return payload


def make_forecast_payload() -> dict[str, object]:
    items = []
    for city in all_cities():
        forecast = fetch_json(build_forecast_url(city))
        daily = forecast["daily"]
        days = []
        for index, date in enumerate(daily["time"]):
            days.append(
                {
                    "date": date,
                    "weatherCode": daily["weather_code"][index],
                    "maxTemp": daily["temperature_2m_max"][index],
                    "minTemp": daily["temperature_2m_min"][index],
                    "precipProbability": daily["precipitation_probability_max"][index],
                    "precipitation": daily["precipitation_sum"][index],
                }
            )
        items.append({**city, "days": days})
    return {"source": "Open-Meteo", "dailyFields": DAILY_FIELDS, "groups": CITY_GROUPS, "cities": items}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/forecast":
            self.send_forecast()
            return
        if path == "/":
            path = "/index.html"
        self.send_static(path)

    def send_forecast(self) -> None:
        try:
            payload = get_forecast_payload()
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "public, max-age=900")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            body = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def send_static(self, path: str) -> None:
        normalized = pathlib.PurePosixPath(urllib.parse.unquote(path.lstrip("/")))
        file_path = (STATIC_DIR / normalized).resolve()
        if not str(file_path).startswith(str(STATIC_DIR)) or not file_path.is_file():
            self.send_error(404)
            return

        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type and (content_type.startswith("text/") or content_type == "application/javascript"):
            content_type = f"{content_type}; charset=utf-8"
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Serving weather forecast app at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
