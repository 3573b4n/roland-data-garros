#!/usr/bin/env python3
"""
Update script for Roland Data Garros.
Called by cron every 5 minutes during the tournament.

Scrapes draws (SM, SD) + players, parses to SQLite/CSV.
Silent if successful — only reports errors or meaningful changes.
"""

import sys, json, time, sqlite3
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scraper.extract_nuxt import fetch_nuxt_data, draw_url, players_url

DATA_DIR = ROOT / "data"
DRAWS_FILE = DATA_DIR / "draws_raw.json"
PLAYERS_FILE = DATA_DIR / "players_raw.json"
DB_FILE = DATA_DIR / "roland_garros.db"

DELAY = 0.5  # seconds between requests


def scrape_draw(draw_code: str) -> dict:
    """Scrape one draw (all rounds come in one response)."""
    url = draw_url(draw_code, 2026, round_num=1)
    return fetch_nuxt_data(url, timeout=20)


def scrape_players(sex: str) -> dict:
    """Scrape players page."""
    url = players_url(sex, 2026)
    return fetch_nuxt_data(url, timeout=20)


def save_json(data: dict, path: Path):
    """Save JSON atomically."""
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.rename(path)


def parse_and_store():
    """Run the parser and store results in SQLite."""
    # Deferred import to avoid circular issues
    sys.path.insert(0, str(ROOT))
    from scraper.parse_data import (
        get_players_from_draw,
        get_players_from_players,
        get_matches,
        merge_players,
        write_sqlite,
        write_csv,
    )
    
    draws_raw = json.loads(DRAWS_FILE.read_text())
    players_raw = json.loads(PLAYERS_FILE.read_text())
    
    draw_players = get_players_from_draw(draws_raw)
    page_m = get_players_from_players(players_raw, "M")
    page_w = get_players_from_players(players_raw, "W")
    all_players = merge_players(draw_players, page_m + page_w)
    
    all_matches = get_matches(draws_raw)
    
    write_sqlite(all_players, all_matches, DB_FILE)
    write_csv(all_players, all_matches, DATA_DIR)
    
    return len(all_players), len(all_matches)


def main():
    import os
    
    # Ensure data dir
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # 1. Scrape draws
        draws = {}
        for code in ("SM", "SD"):
            draws[code] = {"1": scrape_draw(code)}
            time.sleep(DELAY)
        
        save_json(draws, DRAWS_FILE)
        
        # 2. Scrape players
        players = {}
        for sex in ("M", "W"):
            players[sex] = scrape_players(sex)
            time.sleep(DELAY)
        
        save_json(players, PLAYERS_FILE)
        
        # 3. Parse & store
        n_players, n_matches = parse_and_store()
        
        # Silent output — cron delivers stdout only on changes/errors
        print(f"✅ RG Update: {n_players} jugadores, {n_matches} partidos", flush=True)
        
    except Exception as e:
        print(f"❌ RG Update ERROR: {e}", flush=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())