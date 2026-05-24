"""
Parse raw Roland Garros Nuxt data into clean CSVs and SQLite database.

Produces:
  data/roland_garros.db       (SQLite - tables: players, matches)
  data/players.csv            (player list)
  data/matches.csv            (all matches with details)
"""

import csv
import json
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def load_raw(filename: str) -> dict:
    """Load a raw JSON file."""
    path = DATA_DIR / filename
    with open(path) as f:
        return json.load(f)


# ─── Player parser ──────────────────────────────────────────────────────────

def get_players_from_draw(raw_draw: dict) -> list:
    """Extract unique players from a draw's matches (all rounds)."""
    seen = {}
    for round_key, round_data in raw_draw.items():
        if round_data.get("error"):
            continue
        round_results = (round_data.get("data", [{}])[0]
                         .get("tournamentEvent", {})
                         .get("roundResults", []))
        for round_info in round_results:
            for match in round_info.get("matches", []):
                for team_key in ("teamA", "teamB"):
                    team = match.get(team_key, {})
                    for player in team.get("players", []):
                        pid = player.get("id")
                        if pid and pid not in seen:
                            seen[pid] = {
                                "player_id": pid,
                                "first_name": player.get("firstName", ""),
                                "last_name": player.get("lastName", ""),
                                "short_name": player.get("shortName", ""),
                                "ranking": player.get("ranking"),
                                "ranking_double": player.get("rankingDouble"),
                                "country": player.get("country", ""),
                                "sex": player.get("sex", ""),
                                "image_url": (player.get("imageUrl") or "").split("?")[0],
                                "player_card_url": player.get("playerCardUrl", ""),
                            }
    return list(seen.values())


def get_players_from_players(raw_players: dict, sex: str) -> list:
    """Extract players from the /players page data."""
    if sex not in raw_players:
        return []
    players_data = raw_players[sex].get("data", [{}])[0].get("players", [])
    results = []
    for p in players_data:
        birth = p.get("birth", {})
        info = p.get("info", {})
        results.append({
            "player_id": p.get("id"),
            "first_name": p.get("firstName", ""),
            "last_name": p.get("lastName", ""),
            "short_name": p.get("shortName", ""),
            "ranking": p.get("ranking"),
            "ranking_double": p.get("rankingDouble"),
            "country": p.get("country", ""),
            "sex": p.get("sex", ""),
            "age": birth.get("age", ""),
            "birth_date": birth.get("birthDate", ""),
            "hand": info.get("hand", ""),
            "height": info.get("height", ""),
            "weight": info.get("weight", ""),
            "image_url": (p.get("imageUrl") or "").split("?")[0],
            "player_card_url": p.get("playerCardUrl", ""),
        })
    return results


# ─── Match parser ───────────────────────────────────────────────────────────

DRAW_LABELS = {
    "SM": "Men's Singles",
    "SD": "Women's Singles",
    "DM": "Men's Doubles",
    "DD": "Women's Doubles",
    "MX": "Mixed Doubles",
}


def get_matches(raw_draws: dict) -> list:
    """Extract all matches from all rounds into a flat list.
    
    Note: each draw page returns ALL 7 rounds, so we just need one
    request per draw type. The raw_draws dict may have duplicate entries
    for the same draw across different round keys; we only process one.
    """
    matches = []
    for draw_code, rounds_data in raw_draws.items():
        # Pick the first round that has clean data (they all contain full draw)
        first_valid = None
        for round_key, round_data in rounds_data.items():
            if not round_data.get("error"):
                first_valid = round_data
                break
        if first_valid is None:
            continue
        
        td = (first_valid.get("data", [{}])[0]
              .get("tournamentEvent", {}))
        round_results = td.get("roundResults", [])
        
        for round_info in round_results:
            round_number = round_info.get("roundNumber", 0)
            
            for match in round_info.get("matches", []):
                md = match.get("matchData", {})
                team_a = match.get("teamA", {})
                team_b = match.get("teamB", {})
                p_a = team_a.get("players", [{}])[0] if team_a.get("players") else {}
                p_b = team_b.get("players", [{}])[0] if team_b.get("players") else {}
                
                matches.append({
                    "match_id": match.get("id", ""),
                    "draw_code": draw_code,
                    "draw_label": DRAW_LABELS.get(draw_code, draw_code),
                    "round_number": round_number,
                    "round_label": md.get("roundLabel", ""),
                    "status": md.get("status", ""),
                    "status_label": md.get("statusLabel", ""),
                    "court_name": md.get("courtName", ""),
                    "date_schedule": md.get("dateSchedule", ""),
                    "duration_minutes": md.get("durationInMinutes"),
                    "is_night_session": md.get("isNightSession", False),
                    
                    "player_a_id": p_a.get("id"),
                    "player_a_name": p_a.get("shortName", ""),
                    "player_a_ranking": p_a.get("ranking"),
                    "player_a_country": p_a.get("country", ""),
                    "player_a_seed": team_a.get("seed"),
                    "player_a_entry_status": team_a.get("entryStatus", ""),
                    "player_a_winner": team_a.get("winner"),
                    "player_a_sets_won": len(team_a.get("sets", [])),
                    
                    "player_b_id": p_b.get("id"),
                    "player_b_name": p_b.get("shortName", ""),
                    "player_b_ranking": p_b.get("ranking"),
                    "player_b_country": p_b.get("country", ""),
                    "player_b_seed": team_b.get("seed"),
                    "player_b_entry_status": team_b.get("entryStatus", ""),
                    "player_b_winner": team_b.get("winner"),
                    "player_b_sets_won": len(team_b.get("sets", [])),
                })
    return matches


# ─── SQLite writer ──────────────────────────────────────────────────────────

def write_sqlite(players: list, matches: list, db_path: Path):
    """Write players and matches data to SQLite."""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            short_name TEXT,
            ranking INTEGER,
            ranking_double INTEGER,
            country TEXT,
            sex TEXT,
            age TEXT,
            birth_date TEXT,
            hand TEXT,
            height TEXT,
            weight TEXT,
            image_url TEXT,
            player_card_url TEXT
        );
        
        CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            draw_code TEXT,
            draw_label TEXT,
            round_number INTEGER,
            round_label TEXT,
            status TEXT,
            status_label TEXT,
            court_name TEXT,
            date_schedule TEXT,
            duration_minutes INTEGER,
            is_night_session INTEGER,
            
            player_a_id INTEGER,
            player_a_name TEXT,
            player_a_ranking INTEGER,
            player_a_country TEXT,
            player_a_seed INTEGER,
            player_a_entry_status TEXT,
            player_a_winner INTEGER,
            player_a_sets_won INTEGER,
            
            player_b_id INTEGER,
            player_b_name TEXT,
            player_b_ranking INTEGER,
            player_b_country TEXT,
            player_b_seed INTEGER,
            player_b_entry_status TEXT,
            player_b_winner INTEGER,
            player_b_sets_won INTEGER,
            
            FOREIGN KEY (player_a_id) REFERENCES players(player_id),
            FOREIGN KEY (player_b_id) REFERENCES players(player_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_matches_draw ON matches(draw_code);
        CREATE INDEX IF NOT EXISTS idx_matches_round ON matches(round_number);
        CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
        CREATE INDEX IF NOT EXISTS idx_players_ranking ON players(ranking);
    """)
    
    # Insert players (upsert)
    for p in players:
        cur.execute("""
            INSERT OR REPLACE INTO players
            (player_id, first_name, last_name, short_name, ranking, ranking_double,
             country, sex, age, birth_date, hand, height, weight, image_url, player_card_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["player_id"], p["first_name"], p["last_name"], p["short_name"],
            p["ranking"], p.get("ranking_double"),
            p["country"], p["sex"],
            p.get("age", ""), p.get("birth_date", ""), p.get("hand", ""),
            p.get("height", ""), p.get("weight", ""),
            p.get("image_url", ""), p.get("player_card_url", ""),
        ))
    
    # Insert matches (upsert)
    for m in matches:
        cur.execute("""
            INSERT OR REPLACE INTO matches
            (match_id, draw_code, draw_label, round_number, round_label,
             status, status_label, court_name, date_schedule, duration_minutes, is_night_session,
             player_a_id, player_a_name, player_a_ranking, player_a_country, player_a_seed,
             player_a_entry_status, player_a_winner, player_a_sets_won,
             player_b_id, player_b_name, player_b_ranking, player_b_country, player_b_seed,
             player_b_entry_status, player_b_winner, player_b_sets_won)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            m["match_id"], m["draw_code"], m["draw_label"], m["round_number"], m["round_label"],
            m["status"], m["status_label"], m["court_name"], m["date_schedule"],
            m["duration_minutes"], 1 if m["is_night_session"] else 0,
            m["player_a_id"], m["player_a_name"], m["player_a_ranking"], m["player_a_country"],
            m["player_a_seed"], m["player_a_entry_status"], m["player_a_winner"], m["player_a_sets_won"],
            m["player_b_id"], m["player_b_name"], m["player_b_ranking"], m["player_b_country"],
            m["player_b_seed"], m["player_b_entry_status"], m["player_b_winner"], m["player_b_sets_won"],
        ))
    
    conn.commit()
    conn.close()


def write_csv(players: list, matches: list, data_dir: Path):
    """Write CSVs."""
    # Players CSV
    if players:
        with open(data_dir / "players.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=players[0].keys())
            w.writeheader()
            w.writerows(players)
    
    # Matches CSV
    if matches:
        with open(data_dir / "matches.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=matches[0].keys())
            w.writeheader()
            w.writerows(matches)


def merge_players(draw_players: list, page_players: list) -> list:
    """Merge player data from draws (basic) with /players page (detailed)."""
    by_id = {}
    for p in draw_players:
        by_id[p["player_id"]] = p
    for p in page_players:
        pid = p["player_id"]
        if pid in by_id:
            by_id[pid].update(p)
        else:
            by_id[pid] = p
    return list(by_id.values())


def main():
    print("📂 Cargando datos raw...")
    draws_raw = load_raw("draws_raw.json")
    players_raw = load_raw("players_raw.json")
    
    print("👤 Extrayendo jugadores...")
    draw_players = get_players_from_draw(draws_raw)
    page_players_m = get_players_from_players(players_raw, "M")
    page_players_w = get_players_from_players(players_raw, "W")
    all_players = merge_players(draw_players, page_players_m + page_players_w)
    print(f"  → {len(all_players)} jugadores únicos")
    
    print("🏸 Extrayendo partidos...")
    all_matches = get_matches(draws_raw)
    print(f"  → {len(all_matches)} partidos (todas las rondas)")
    
    print("💾 Escribiendo CSVs...")
    write_csv(all_players, all_matches, DATA_DIR)
    
    print("🗄️  Escribiendo SQLite...")
    db_path = DATA_DIR / "roland_garros.db"
    write_sqlite(all_players, all_matches, db_path)
    db_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"  → {db_path.name} ({db_mb:.1f} MB)")
    
    # Quick stats
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT sex, COUNT(*) FROM players GROUP BY sex")
    print(f"\n📊 Estadísticas:")
    for sex, count in cur.fetchall():
        label = "Hombres" if sex == "M" else "Mujeres" if sex == "F" else sex
        print(f"  {label}: {count}")
    cur.execute("SELECT draw_label, round_number, COUNT(*) FROM matches GROUP BY draw_label, round_number")
    for label, rnd, cnt in cur.fetchall():
        print(f"  {label} R{rnd}: {cnt}")
    conn.close()
    
    print("\n✅ Parseo completado!")


if __name__ == "__main__":
    main()
