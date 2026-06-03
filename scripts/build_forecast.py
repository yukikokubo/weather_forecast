from __future__ import annotations

import json
import pathlib
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "forecast.json"
JST = timezone(timedelta(hours=9))

DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
    "precipitation_sum",
]

FETCH_RETRIES = 3
FETCH_RETRY_DELAY_SECONDS = 2
FETCH_DELAY_SECONDS = 0.5

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
    for attempt in range(1, FETCH_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except (TimeoutError, urllib.error.URLError) as error:
            if attempt == FETCH_RETRIES:
                raise
            print(f"Fetch failed ({attempt}/{FETCH_RETRIES}): {error}. Retrying...")
            time.sleep(FETCH_RETRY_DELAY_SECONDS * attempt)

    raise RuntimeError("unreachable")


def make_forecast_payload() -> dict[str, object]:
    items = []
    for city in all_cities():
        print(f"Fetching forecast: {city['name']}")
        try:
            forecast = fetch_json(build_forecast_url(city))
        except Exception as error:
            raise RuntimeError(f"Failed to fetch forecast for {city['name']}") from error
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
        time.sleep(FETCH_DELAY_SECONDS)

    return {
        "source": "Open-Meteo",
        "license": "CC BY 4.0",
        "generatedAt": datetime.now(JST).isoformat(timespec="seconds"),
        "dailyFields": DAILY_FIELDS,
        "groups": CITY_GROUPS,
        "cities": items,
    }


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = make_forecast_payload()
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['cities'])} cities to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
