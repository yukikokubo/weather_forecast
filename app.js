const state = {
  dayIndex: 0,
  region: "all",
  data: null,
  markers: [],
  firstRender: true,
};

const DEFAULT_BOUNDS = [
  [35.55, 137.85],
  [36.55, 140.5],
];

const ALL_MAP_BOUNDS = [
  [31.25, 129.8],
  [43.55, 141.7],
];

const TABLE_PRIORITY = ["東京", "松本", "札幌", "静岡", "大阪", "福岡"];
const ALL_MAP_PRIORITY = [
  "札幌",
  "仙台",
  "東京",
  "松本",
  "名古屋",
  "静岡",
  "大阪",
  "広島",
  "福岡",
  "鹿児島",
];
const REGIONAL_FOCUS_CITIES = {
  中部: ["松本", "名古屋", "静岡"],
  "九州・沖縄": ["福岡", "熊本", "鹿児島"],
};

const weatherMap = {
  0: ["快晴", "☀️"],
  1: ["晴れ", "🌤️"],
  2: ["薄曇り", "⛅"],
  3: ["曇り", "☁️"],
  45: ["霧", "🌫️"],
  48: ["霧氷", "🌫️"],
  51: ["弱い霧雨", "🌦️"],
  53: ["霧雨", "🌦️"],
  55: ["強い霧雨", "🌧️"],
  61: ["小雨", "🌦️"],
  63: ["雨", "🌧️"],
  65: ["強い雨", "🌧️"],
  71: ["小雪", "🌨️"],
  73: ["雪", "🌨️"],
  75: ["大雪", "❄️"],
  80: ["にわか雨", "🌦️"],
  81: ["強いにわか雨", "🌧️"],
  82: ["激しい雨", "⛈️"],
  95: ["雷雨", "⛈️"],
  96: ["雷雨・雹", "⛈️"],
  99: ["激しい雷雨", "⛈️"],
};

const map = L.map("map", {
  zoomControl: false,
  minZoom: 4,
});

L.control.zoom({ position: "bottomright" }).addTo(map);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const dayTabs = document.querySelector("#dayTabs");
const regionSelect = document.querySelector("#regionSelect");
const forecastHead = document.querySelector("#forecastHead");
const forecastBody = document.querySelector("#forecastBody");
const mobileMapQuery = window.matchMedia("(max-width: 980px)");

function setMapInteraction(enabled) {
  const action = enabled ? "enable" : "disable";
  map.dragging[action]();
  map.touchZoom[action]();
  map.doubleClickZoom[action]();
  map.scrollWheelZoom[action]();
  map.boxZoom[action]();
  map.keyboard[action]();
  if (map.tap) map.tap[action]();
}

function syncMapInteraction() {
  setMapInteraction(!mobileMapQuery.matches);
}

mobileMapQuery.addEventListener("change", syncMapInteraction);
syncMapInteraction();

function weatherInfo(code) {
  return weatherMap[code] || ["不明", "🌡️"];
}

function formatDate(value) {
  return new Intl.DateTimeFormat("ja-JP", {
    month: "numeric",
    day: "numeric",
    weekday: "short",
  }).format(new Date(`${value}T00:00:00+09:00`));
}

function filteredCities() {
  if (!state.data) return [];
  if (state.region === "all") return state.data.cities;
  return state.data.cities.filter((city) => city.region === state.region || (state.region === "関東" && city.name === "松本"));
}

function tableCities() {
  const priority = new Map(TABLE_PRIORITY.map((name, index) => [name, index]));
  return [...filteredCities()].sort((first, second) => {
    const firstPriority = priority.has(first.name) ? priority.get(first.name) : Number.MAX_SAFE_INTEGER;
    const secondPriority = priority.has(second.name) ? priority.get(second.name) : Number.MAX_SAFE_INTEGER;
    if (firstPriority !== secondPriority) return firstPriority - secondPriority;
    return 0;
  });
}

function mapFocusCities(cities) {
  const focusNames = REGIONAL_FOCUS_CITIES[state.region];
  if (!focusNames) return cities;

  const focusCities = cities.filter((city) => focusNames.includes(city.name));
  return focusCities.length ? focusCities : cities;
}

function mapCities() {
  const cities = filteredCities();
  if (state.region !== "all") return cities;

  const priority = new Set(ALL_MAP_PRIORITY);
  return cities.filter((city) => priority.has(city.name));
}

function clearMarkers() {
  state.markers.forEach((marker) => map.removeLayer(marker));
  state.markers = [];
}

function createWeatherMarker(city, day) {
  const [label, icon] = weatherInfo(day.weatherCode);
  const html = `
    <div class="weather-marker" title="${city.name} ${label}">
      <span class="marker-icon">${icon}</span>
      <div class="marker-city">${city.name}</div>
      <div class="marker-temp">
        <strong class="max">${Math.round(day.maxTemp)}°</strong>
        <strong class="min">${Math.round(day.minTemp)}°</strong>
      </div>
    </div>
  `;
  return L.divIcon({ html, className: "", iconSize: [72, 74], iconAnchor: [36, 37] });
}

function renderMap() {
  clearMarkers();
  const cities = mapCities();

  cities.forEach((city) => {
    const day = city.days[state.dayIndex];
    const icon = createWeatherMarker(city, day);
    const [label] = weatherInfo(day.weatherCode);
    const marker = L.marker([city.lat, city.lon], { icon })
      .bindPopup(
        `<strong>${city.name}</strong><br>${formatDate(day.date)} ${label}<br>${day.maxTemp}°C / ${day.minTemp}°C<br>降水確率 ${day.precipProbability}% / 降水量 ${day.precipitation}mm`
      )
      .addTo(map);
    state.markers.push(marker);
  });

  if (state.firstRender) {
    map.fitBounds(ALL_MAP_BOUNDS, { animate: false, padding: [18, 18] });
    state.firstRender = false;
  } else if (state.region === "all") {
    map.fitBounds(ALL_MAP_BOUNDS, { animate: false, padding: [18, 18] });
  } else if (state.region === "関東") {
    map.fitBounds(DEFAULT_BOUNDS, { animate: false, padding: [18, 18] });
  } else if (cities.length && state.region !== "all") {
    const focusCities = mapFocusCities(cities);
    const bounds = L.latLngBounds(focusCities.map((city) => [city.lat, city.lon]));
    map.fitBounds(bounds.pad(0.12), { animate: false });
  }

}

function renderDayTabs() {
  const dates = state.data.cities[0].days.slice(0, 3);
  dayTabs.innerHTML = dates
    .map(
      (day, index) =>
        `<button type="button" class="${index === state.dayIndex ? "active" : ""}" data-day="${index}">${formatDate(day.date)}</button>`
    )
    .join("");
}

function renderRegionSelect() {
  const regions = state.data.groups.map((group) => group.region);
  regionSelect.innerHTML = `<option value="all">すべて</option>${regions
    .map((region) => `<option value="${region}">${region}</option>`)
    .join("")}`;
}

function renderTable() {
  const cities = tableCities();
  const dates = state.data.cities[0].days;
  forecastHead.innerHTML = `
    <tr>
      <th>都市</th>
      ${dates.map((day) => `<th>${formatDate(day.date)}</th>`).join("")}
    </tr>
  `;
  forecastBody.innerHTML = cities
    .map(
      (city) => `
        <tr>
          <td class="city-cell">${city.name}<span class="prefecture">${city.prefecture}</span></td>
          ${city.days
            .map((day) => {
              const [label, icon] = weatherInfo(day.weatherCode);
              return `
                <td class="day-cell">
                  <div class="day-weather"><span>${icon}</span><strong>${label}</strong></div>
                  <div class="metrics">
                    <span class="temp-pair"><strong class="max">${day.maxTemp}°C</strong><span>/</span><strong class="min">${day.minTemp}°C</strong></span>
                    <span>降水確率 ${day.precipProbability}%</span>
                    <span>降水量 ${day.precipitation}mm</span>
                  </div>
                </td>
              `;
            })
            .join("")}
        </tr>
      `
    )
    .join("");
}

function setDay(index) {
  state.dayIndex = index;
  dayTabs.querySelectorAll("button").forEach((button) => {
    button.classList.toggle("active", Number(button.dataset.day) === index);
  });
  renderMap();
}

dayTabs.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-day]");
  if (button) setDay(Number(button.dataset.day));
});

regionSelect.addEventListener("change", () => {
  state.region = regionSelect.value;
  renderTable();
  renderMap();
});

async function boot() {
  try {
    const response = await fetch("data/forecast.json");
    if (!response.ok) throw new Error(`Forecast API failed: ${response.status}`);
    state.data = await response.json();
    renderRegionSelect();
    renderDayTabs();
    renderTable();
    renderMap();
  } catch (error) {
    forecastBody.innerHTML = `<tr><td>天気データを取得できませんでした。時間をおいて再読み込みしてください。</td></tr>`;
    console.error(error);
  }
}

boot();
