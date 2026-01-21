# Invoice App (Streamlit Lite UI)

> Huom: UI tukee suomea ja englantia (fi/en).

## Evaluation / Arviointi (tärkein osa)

Tämän projektin arviointia varten ensisijainen käyttöliittymä on **Streamlit Lite UI**.  
Lite UI mahdollistaa laskun/kuitin luomisen ja **PDF- sekä Finvoice XML** -tiedostojen tuottamisen paikallisesti.

Muut komponentit (API, Pro UI) ovat mukana arkkitehtuurissa jatkokehitystä varten, mutta ne eivät ole välttämättömiä projektin arviointiin.

### Quickstart (Evaluation)

**Prerequisites**
- Pixi (Python-ympäristön deterministinen hallinta)

**Run**
```bash
pixi install
pixi run smoke
pixi run lite
```

Streamlit käynnistyy ja UI avautuu selaimeen. UI:lla voit luoda laskun/kuitin ja ladata PDF- sekä Finvoice XML -tiedostot.

## Overview

Local-first laskutus/kuittisovellus pienyrittäjälle. Sovellus tuottaa:

- PDF-dokumentin (ReportLab)
- Finvoice XML -rungon (manuaalinen OP-upload -polku UI:ssa)
- kirjanpidollisen tapahtumalokin (append-only ledger) ja arkistoinnin (kuukausirakenne)
- Ei pilviriippuvuuksia oletuksena.

## Features

- Streamlit UI (fi/en)
- PDF generation (ReportLab)
- Append-only JSONL integrity ledger (SHA-256)
- Monthly storage structure: storage/YYYY/MM
- Optional ZIP backups + retention
- CI (GitHub Actions) + smoke/import test
- Pixi-locked runtime (Python 3.12 conda-forge)

## Project structure (high-level)

```
invoice-app/
  app.py
  config.py
  core/
  server/
  frontend/
  outputs/
  storage/
  utils/
  locales/
  scripts/
```

## Known limitations (current)

- PDF: “Invoice #” voi näkyä vielä N/A vaikka Finvoice XML sisältää invoice numberin.
  (Numeroiden läpivienti PDF-headeriin viimeistellään jatkokehityksessä.)
- Finvoice XML on tässä vaiheessa “rungon” tasolla; pankki-/operaattoritason validointi ja automaattinen lähetys ovat jatkokehitystä.

## Extensions (optional)

### API (FastAPI)

API toimii “thin wrapperina” core-palvelun ympärillä ja mahdollistaa Pro UI:n.

Tämä ei ole osa arvioinnin minimipolkua.

```bash
pixi run api
```

Test:

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/api/v1/health (jos endpoint on käytössä)

### Pro UI (Next.js)

Pro UI on Next.js-pohjainen dashboard.

Tämä ei ole osa arvioinnin minimipolkua.

```bash
cd frontend
npm install
npm run dev
```

## Data & storage

- data/: esim. sekvenssit ja ledger-data
- storage/YYYY/MM/: kuukausiarkisto (PDF/XML/export/meta)
- storage/**/meta/*.jsonl: append-only integrity ledger
- backups/: ZIP-varmuuskopiot (jos käytössä)

## Security notes

- Local-first: ei ulkoisia palveluja oletuksena
- Append-only integrity ledger (SHA-256)
- Atomic writes (Windows-safe)

## License

Planned: AGPLv3 (placeholder)
