# Electron-työpöytäsovelluksen käyttöönotto

Tässä projektissa käyttöliittymä pysyy Flask-pohjaisena (`web_ui.py`), mutta se käynnistetään Electronin sisälle työpöytäsovellukseksi.

## 1) Asenna Python-riippuvuudet

```bash
python3 -m pip install flask pyyaml requests obs-websocket-py
```

## 2) Tarkista API-osoite ja mode

`config.yaml` määrää mistä AutoDarts-tila luetaan. Varmista ainakin:

```yaml
mode:
  test: false

autodarts:
  api_url: "http://192.168.1.50:3180/api/state"
```

Kun `test: false`, engine pollaa API:a ja vähentää pisteet automaattisesti heittojen perusteella.

## 3) Asenna Node-riippuvuudet

```bash
npm install
```

## 4) Käynnistä työpöytäsovellus

```bash
npm run desktop:start
```

Electron tekee seuraavat asiat automaattisesti:
- käynnistää Python-taustapalvelun (`web_ui.py`)
- odottaa `/health`-päätepisteen vastausta
- avaa käyttöliittymän työpöytäikkunaan

## 5) Rakenna paketti

```bash
npm run desktop:dist
```

Tämä luo jaettavan asennuspaketin `dist/`-kansioon.

## Huomiot

- Jos Python-tulkki ei löydy automaattisesti, määritä ympäristömuuttuja:
  - Linux/macOS: `PYTHON_BIN=python3 npm run desktop:start`
  - Windows: `set PYTHON_BIN=python && npm run desktop:start`
- Flaskin portti voidaan vaihtaa ympäristömuuttujalla `DARTS_UI_PORT`.
