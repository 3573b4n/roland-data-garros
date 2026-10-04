# 🎾 Roland Data Garros 2026

**[🇪🇸 Español](#-español) · [🇬🇧 English](#-english)**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Cron_15min-2088FF?style=flat&logo=githubactions&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-DB-003B57?style=flat&logo=sqlite&logoColor=white)

---

## 🇪🇸 Español

Dashboard interactivo con datos en vivo del torneo **Roland Garros 2026**, alimentado por un
pipeline de scraping propio que extrae datos oficiales, los procesa y los persiste en SQLite.

### ✨ Funcionalidades

- Partidos por cuadro (individuales masculino y femenino), ronda, pista y estado.
- Puntuaciones detalladas, incluidos tie-breaks y duración del partido.
- Fichas de jugadores: ranking, país, siembra, edad, mano y nacionalidad.
- Sesiones nocturnas y horarios programados.

### 🔄 Pipeline de datos

GitHub Actions ejecuta `scripts/update_data.py` **cada 15 minutos** (cron `*/15`) durante el
torneo. El scraper extrae los datos del sitio oficial (contenido Nuxt.js, se procesa con
Node.js + Python), se normaliza a CSV/SQLite y se hace commit automático en `data/`.

```text
Sitio oficial RG ──▶ scraper/ (scrape_draws → extract_nuxt → parse_data)
                          │   Node.js (extracción Nuxt) + Python (parseo)
                          ▼
                 data/ (roland_garros.db · matches.csv · players.csv)
                          │   commit automático por GitHub Actions
                          ▼
                 app.py (Streamlit) ──▶ Dashboard en vivo
```

### 🗂 Estructura del proyecto

| Ruta | Contenido |
|---|---|
| `app.py` | Aplicación Streamlit (dashboard interactivo) |
| `scraper/scrape_draws.py` | Descarga de cuadros y partidos |
| `scraper/extract_nuxt.py` | Extracción de datos embebidos (Nuxt.js) |
| `scraper/parse_data.py` | Normalización y limpieza de datos |
| `scripts/update_data.py` | Pipeline completo (lo ejecuta el workflow) |
| `data/` | SQLite + CSV versionados (actualizados cada 15 min) |
| `.github/workflows/update-data.yml` | Cron de GitHub Actions |

### ▶️ Ejecutar en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 🇬🇧 English

Interactive dashboard with live data from the **Roland Garros 2026** tournament, powered by a
custom scraping pipeline that extracts official data, processes it and stores it in SQLite.

### ✨ Features

- Matches per draw (men's and women's singles), round, court and status.
- Detailed scores, including tie-breaks and match duration.
- Player cards: ranking, country, seed, age, hand and nationality.
- Night sessions and scheduled times.

### 🔄 Data pipeline

GitHub Actions runs `scripts/update_data.py` **every 15 minutes** (cron `*/15`) during the
tournament. The scraper pulls data from the official site (Nuxt.js content, processed with
Node.js + Python), normalizes it to CSV/SQLite and automatically commits it to `data/`.

### ▶️ Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```
