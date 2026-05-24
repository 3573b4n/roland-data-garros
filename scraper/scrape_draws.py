"""
Scrape all draws and player data from Roland Garros 2026.

Usage:
    python -m scraper.scrape_draws           # Full scrape (all draws + players)
    python -m scraper.scrape_draws --draws-only   # Just draws
    python -m scraper.scrape_draws --players-only # Just players
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure scraper package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.extract_nuxt import fetch_nuxt_data, draw_url, players_url

DATA_DIR = Path(__file__).parent.parent / "data"

# All draw types we want to scrape
DRAW_TYPES = [
    ("SM", "Men's Singles"),
    ("SD", "Women's Singles"),
    ("DM", "Men's Doubles"),
    ("DD", "Women's Doubles"),
    ("MX", "Mixed Doubles"),
]

# Rounds (main draw: 7 rounds from R1 to Final)
ROUNDS = list(range(1, 8))

# Years available
YEAR = 2026


def scrape_draw(draw_code: str, year: int = YEAR, round_num: int = 1, delay: float = 0.5) -> dict:
    """Scrape one draw page and return parsed data."""
    url = draw_url(draw_code, year, round_num)
    print(f"  Fetching {draw_code} r{round_num}...", file=sys.stderr)
    time.sleep(delay)
    try:
        return fetch_nuxt_data(url)
    except Exception as e:
        print(f"  ⚠️  ERROR: {e}", file=sys.stderr)
        return {"error": str(e), "url": url}


def scrape_all_draws(year: int = YEAR, delay: float = 0.5) -> dict:
    """Scrape all draw types for all rounds."""
    results = {}
    
    for draw_code, draw_label in DRAW_TYPES:
        print(f"\n{'='*50}", file=sys.stderr)
        print(f"  {draw_label} ({draw_code})", file=sys.stderr)
        print(f"{'='*50}", file=sys.stderr)
        
        draws_for_type = {}
        for r in ROUNDS:
            raw = scrape_draw(draw_code, year, r, delay)
            if "error" not in raw:
                draws_for_type[str(r)] = raw
                # Extract round label from data
                data = raw.get("data", [{}])[0]
                td = data.get("tournamentEvent", {})
                rounds_info = td.get("roundNavs", [])
                if r <= len(rounds_info):
                    label = rounds_info[r-1]["label"]
                    n_matches = len(td.get("roundResults", [{}])[0].get("matches", []))
                    print(f"    ✓ R{r}: {label} ({n_matches} partidos)", file=sys.stderr)
            else:
                print(f"    ✗ R{r}: {raw.get('error', 'Unknown error')}", file=sys.stderr)
                break
        
        results[draw_code] = draws_for_type
    
    return results


def scrape_players(year: int = YEAR, delay: float = 0.5) -> dict:
    """Scrape player data."""
    results = {}
    for sex in ("M", "W"):
        label = "Men" if sex == "M" else "Women"
        url = players_url(sex, year)
        print(f"  Fetching {label}...", file=sys.stderr)
        time.sleep(delay)
        try:
            data = fetch_nuxt_data(url)
            results[sex] = data
            print(f"    ✓ {label}: OK", file=sys.stderr)
        except Exception as e:
            print(f"    ⚠️  {label}: {e}", file=sys.stderr)
            results[sex] = {"error": str(e)}
    return results


def _clean_save(data: dict, name: str):
    """Save data, removing __NUXT__ wrapper to save space."""
    path = DATA_DIR / name
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"  💾 Saved {name} ({size_mb:.1f} MB)", file=sys.stderr)
    return path


def main():
    parser = argparse.ArgumentParser(description="Scrape Roland Garros data")
    parser.add_argument("--draws-only", action="store_true", help="Scrape only draws")
    parser.add_argument("--players-only", action="store_true", help="Scrape only players")
    parser.add_argument("--year", type=int, default=YEAR, help="Year to scrape")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests (seconds)")
    args = parser.parse_args()
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    do_draws = not args.players_only
    do_players = not args.draws_only
    
    if do_draws:
        print("\n🎾 Extrayendo cuadros...", file=sys.stderr)
        draws = scrape_all_draws(args.year, args.delay)
        _clean_save(draws, "draws_raw.json")
    
    if do_players:
        print("\n🏃 Extrayendo jugadores...", file=sys.stderr)
        players = scrape_players(args.year, args.delay)
        _clean_save(players, "players_raw.json")
    
    print("\n✅ Extracción completa!", file=sys.stderr)


if __name__ == "__main__":
    main()
