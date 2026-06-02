# 気象予報士 水谷幸資のズバリ天気

地図と週間表で主要都市の天気予報を確認できるサンプルサイトです。

公開URL:
https://yukikokubo.github.io/weather_forecast/

## 概要

- Open-Meteo APIから7日分の天気予報を取得
- 地図上に天気アイコン、最高気温、最低気温を表示
- 地域ごとの表示切り替え
- 週間予報を表形式で表示
- GitHub Pagesで静的サイトとして公開
- GitHub Actionsで `data/forecast.json` を毎日更新

## データ出典

天気データはOpen-Meteoを利用しています。

- Open-Meteo: https://open-meteo.com/
- License: CC BY 4.0 https://creativecommons.org/licenses/by/4.0/

地図はLeafletとOpenStreetMapを利用しています。

- Leaflet: https://leafletjs.com/
- OpenStreetMap: https://www.openstreetmap.org/

## ファイル構成

```text
.
├── index.html
├── styles.css
├── app.js
├── data/
│   └── forecast.json
├── scripts/
│   └── build_forecast.py
└── .github/
    └── workflows/
        └── update-forecast.yml
```

## ローカル確認

```powershell
python -m http.server 8000
```

ブラウザで以下を開きます。

```text
http://127.0.0.1:8000/
```

## 予報データの手動更新

```powershell
python scripts/build_forecast.py
```

実行すると `data/forecast.json` が更新されます。

## GitHub Pages設定

GitHubのリポジトリ設定で以下を指定します。

- Source: Deploy from a branch
- Branch: main
- Folder: / (root)

## 自動更新

`.github/workflows/update-forecast.yml` により、GitHub Actionsが毎日 `data/forecast.json` を更新します。

手動更新したい場合は、GitHub Actionsの `Update forecast data` ワークフローから `Run workflow` を実行できます。
