"""
Roland Data Garros — Streamlit Dashboard v2
============================================
🎾 Visual dashboard for Roland Garros 2026 data.
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from pathlib import Path
from datetime import datetime

# ─── Config ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Roland Data Garros 2026",
    page_icon="🎾",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "roland_garros.db"

# RG Brand colors
RG_GREEN = "#00503c"
RG_GREEN_LIGHT = "#068d6d"
RG_ORANGE = "#cc4e0e"
RG_ORANGE_LIGHT = "#e38045"
RG_DARK = "#242424"
RG_GREY = "#848484"
RG_BG = "#fafafa"

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
    /* Global */
    .stApp {{ background-color: {RG_BG}; }}
    h1, h2, h3 {{ color: {RG_DARK} !important; }}
    
    /* Metric cards */
    div[data-testid="metric-container"] {{
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }}
    
    /* Buttons */
    .stButton button {{
        background-color: {RG_GREEN};
        color: white;
        border-radius: 8px;
        border: none;
        padding: 8px 20px;
    }}
    .stButton button:hover {{
        background-color: {RG_GREEN_LIGHT};
    }}
    
    /* Cards */
    .match-card {{
        background: white;
        border: 1px solid #e8e8e8;
        border-left: 4px solid {RG_GREEN};
        border-radius: 10px;
        padding: 14px;
        margin: 8px 0;
        transition: all 0.2s;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    .match-card:hover {{
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transform: translateY(-1px);
    }}
    .match-card.live {{ border-left-color: #ff6b35; }}
    .match-card.done {{ border-left-color: {RG_GREEN}; }}
    .match-card.upcoming {{ border-left-color: #bbb; }}
    
    .player-name {{ font-weight: 600; font-size: 0.95em; }}
    .seed-badge {{
        background: {RG_GREEN};
        color: white;
        padding: 1px 8px;
        border-radius: 12px;
        font-size: 0.7em;
        font-weight: 600;
    }}
    .entry-badge {{
        background: {RG_ORANGE};
        color: white;
        padding: 1px 7px;
        border-radius: 10px;
        font-size: 0.65em;
        font-weight: 600;
    }}
    .vs-text {{
        color: {RG_ORANGE};
        font-weight: bold;
        font-size: 0.85em;
        margin: 4px 0;
    }}
    .ranking-text {{ color: {RG_GREY}; font-size: 0.8em; }}
    
    .player-card {{
        background: white;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        border: 1px solid #eee;
        display: flex;
        align-items: center;
        gap: 12px;
    }}
    
    .header-title {{
        color: {RG_GREEN};
        font-size: 2.2em;
        font-weight: 700;
    }}
    .header-subtitle {{
        color: {RG_GREY};
        font-size: 0.9em;
    }}
    
    /* Status badge */
    .status-badge {{
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: 600;
    }}
    .status-live {{ background: #fff0e6; color: #cc4e0e; }}
    .status-done {{ background: #e6f4f0; color: #00503c; }}
    .status-upcoming {{ background: #f0f0f0; color: #666; }}
    
    /* Divider */
    .rg-divider {{
        height: 2px;
        background: linear-gradient(90deg, {RG_GREEN}, {RG_ORANGE});
        margin: 20px 0;
        border-radius: 2px;
    }}
</style>
""", unsafe_allow_html=True)


# ─── Data loading ───────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_data():
    if not DB_PATH.exists():
        return None, None
    conn = sqlite3.connect(str(DB_PATH))
    players = pd.read_sql("SELECT * FROM players ORDER BY ranking ASC", conn)
    matches = pd.read_sql(
        "SELECT * FROM matches ORDER BY draw_code, round_number, match_id", conn
    )
    conn.close()
    return players, matches


players_df, matches_df = load_data()
DATA_OK = players_df is not None


# ─── Helper functions ───────────────────────────────────────────────────────

def seed_badge(seed):
    return f'<span class="seed-badge">#{seed}</span>' if seed and seed <= 32 else ""

def entry_badge(entry):
    badges = {"W": "WC", "Q": "Q", "L": "LL"}
    if entry in badges:
        return f'<span class="entry-badge">{badges[entry]}</span>'
    return ""

def status_class(status):
    return {"IN_PROGRESS": "live", "FINISHED": "done", "NOT_STARTED": "upcoming"}.get(status, "upcoming")

def status_icon(status):
    return {"IN_PROGRESS": "🔴", "FINISHED": "✅", "NOT_STARTED": "⏳"}.get(status, "⏳")

def get_player_image(player_id):
    if not DATA_OK:
        return None
    p = players_df[players_df["player_id"] == player_id]
    if len(p) > 0 and p.iloc[0]["image_url"]:
        return p.iloc[0]["image_url"]
    return None

def round_label(r):
    labels = {1: "1R", 2: "2R", 3: "3R", 4: "4R", 5: "QF", 6: "SF", 7: "F"}
    return labels.get(r, f"R{r}")

def round_name(r):
    names = {1: "1ª Ronda", 2: "2ª Ronda", 3: "3ª Ronda", 4: "4ª Ronda",
             5: "Cuartos de Final", 6: "Semifinal", 7: "Final"}
    return names.get(r, f"Ronda {r}")


# ─── Sidebar ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<h2 style="color:{RG_GREEN};">🎾 Roland<br>Data Garros</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="header-subtitle">18 May — 7 Jun 2026 · París</p>',
        unsafe_allow_html=True,
    )
    st.divider()
    
    page = st.radio(
        "Sección:",
        ["🏆 Cuadro", "👤 Jugadores", "📊 Estadísticas", "⚔️ Head-to-Head"],
        label_visibility="collapsed",
    )
    
    st.divider()
    
    if DATA_OK:
        n_m = len(players_df[players_df["sex"] == "M"])
        n_f = len(players_df[players_df["sex"] == "F"])
        n_matches = len(matches_df)
        
        st.markdown("### 📊 Resumen")
        st.metric("🏃 Hombres", n_m)
        st.metric("👩 Mujeres", n_f)
        st.metric("🎾 Partidos", n_matches)
        
        # Last update
        st.divider()
        st.caption(f"Actualizado: cada 5 min ⏱️")
        
        # Live indicator
        live_count = len(matches_df[matches_df["status"] == "IN_PROGRESS"])
        if live_count > 0:
            st.markdown(f'<p style="color:#ff6b35;font-weight:600;">🔴 {live_count} partidos en vivo</p>',
                       unsafe_allow_html=True)


# ─── HEADER ─────────────────────────────────────────────────────────────────

def show_header(title, subtitle=""):
    st.markdown(f'<p class="header-title">{title}</p>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<p class="header-subtitle">{subtitle}</p>', unsafe_allow_html=True)
    st.markdown('<div class="rg-divider"></div>', unsafe_allow_html=True)


# ─── PAGE: Bracket ──────────────────────────────────────────────────────────

def show_bracket():
    show_header("🏆 Cuadro del Torneo", "Explora los emparejamientos ronda a ronda")
    
    col1, col2 = st.columns(2)
    with col1:
        draw = st.selectbox(
            "Cuadro:", ["SM - Masculino", "SD - Femenino"],
            key="draw_sel"
        )
    draw_code = draw.split(" - ")[0]
    
    df = matches_df[matches_df["draw_code"] == draw_code]
    
    with col2:
        max_round = df["round_number"].max()
        current_round = st.select_slider(
            "Ronda:",
            options=list(range(1, max_round + 1)),
            value=1,
            format_func=round_name,
        )
    
    # Stats bar
    rnd_df = df[df["round_number"] == current_round]
    n_matches = len(rnd_df)
    completed = len(rnd_df[rnd_df["status"] == "FINISHED"])
    live = len(rnd_df[rnd_df["status"] == "IN_PROGRESS"])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Partidos", n_matches)
    col2.metric("Completados", completed)
    col3.metric("En juego", live)
    col4.metric("No empezados", n_matches - completed - live)
    
    st.markdown(f"### {round_name(current_round)}")
    
    # Different layouts per round
    if current_round in [1, 2, 3]:
        # 3-column grid
        cols = st.columns(3)
        for i, (_, m) in enumerate(rnd_df.iterrows()):
            with cols[i % 3]:
                render_match_card(m)
    elif current_round == 4:
        cols = st.columns(4)
        for i, (_, m) in enumerate(rnd_df.iterrows()):
            with cols[i]:
                render_match_card(m, large=True)
    elif current_round in [5, 6, 7]:
        # Center them
        cols_needed = len(rnd_df)
        cols = st.columns([1] * cols_needed + [1])
        for i, (_, m) in enumerate(rnd_df.iterrows()):
            with cols[i]:
                render_match_card(m, large=True, center=True)
    
    # Show bracket progression
    if current_round == 1:
        st.divider()
        st.markdown("### 📐 Progresión del cuadro")
        
        total = df["round_number"].value_counts().sort_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[round_name(r) for r in total.index],
            y=total.values,
            marker_color=[RG_GREEN, RG_GREEN_LIGHT, RG_ORANGE, RG_ORANGE_LIGHT, "#e38045", "#cc4e0e", "#ab3d16"],
            text=total.values,
            textposition="outside",
        ))
        fig.update_layout(
            title="Partidos por ronda",
            height=350,
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis_title="Partidos",
            xaxis_title="",
            font=dict(size=12),
        )
        st.plotly_chart(fig, use_container_width=True)


def render_match_card(m, large=False, center=False):
    status = m["status"]
    status_cls = status_class(status)
    icon = status_icon(status)
    
    sa = seed_badge(m["player_a_seed"])
    sb = seed_badge(m["player_b_seed"])
    ea = entry_badge(m["player_a_entry_status"])
    eb = entry_badge(m["player_b_entry_status"])
    
    pa_name = m["player_a_name"]
    pb_name = m["player_b_name"]
    pa_rank = f"#{m['player_a_ranking']}" if pd.notna(m['player_a_ranking']) else "-"
    pb_rank = f"#{m['player_b_ranking']}" if pd.notna(m['player_b_ranking']) else "-"
    
    match_id = m["match_id"]
    
    # Try to get player images
    img_a = get_player_image(m["player_a_id"])
    img_b = get_player_image(m["player_b_id"])
    
    img_style = "width:32px;height:32px;border-radius:50%;object-fit:cover;border:2px solid #eee;" if img_a else "display:none;"
    img_a_html = f'<img src="{img_a}" style="{img_style}" />' if img_a else ""
    img_b_html = f'<img src="{img_b}" style="{img_style}" />' if img_b else ""
    
    if large:
        size_class = "match-card-large"
        html = f"""
        <div class="match-card {status_cls}" style="text-align:center;{'margin:0 auto;max-width:320px;' if center else ''}">
            <div style="font-size:0.8em;color:#888;margin-bottom:8px;">
                {icon} <span class="status-badge status-{status_cls}">{m['status_label']}</span>
            </div>
            <div style="margin:10px 0;display:flex;align-items:center;justify-content:center;gap:8px;">
                {img_a_html}
                <span class="player-name">{pa_name}</span> {sa} {ea}
            </div>
            <div class="vs-text">VS</div>
            <div style="margin:10px 0;display:flex;align-items:center;justify-content:center;gap:8px;">
                {img_b_html}
                <span class="player-name">{pb_name}</span> {sb} {eb}
            </div>
            <div class="ranking-text">{pa_rank} · {pb_rank}</div>
        </div>
        """
    else:
        html = f"""
        <div class="match-card {status_cls}">
            <div style="display:flex;justify-content:space-between;font-size:0.75em;color:#aaa;margin-bottom:6px;">
                <span>{icon} <span class="status-badge status-{status_cls}">{m['status_label']}</span></span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                {img_a_html}
                <span class="player-name">{pa_name}</span> {sa} {ea}
            </div>
            <div class="vs-text" style="margin-left:40px;">VS</div>
            <div style="display:flex;align-items:center;gap:8px;">
                {img_b_html}
                <span class="player-name">{pb_name}</span> {sb} {eb}
            </div>
            <div class="ranking-text" style="margin-left:40px;">{pa_rank} · {pb_rank}</div>
        </div>
        """
    
    st.markdown(html, unsafe_allow_html=True)


# ─── PAGE: Players ──────────────────────────────────────────────────────────

def show_players():
    show_header("👤 Jugadores", f"{len(players_df)} tenistas en Roland Garros 2026")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        sex = st.selectbox("Género:", ["Todos", "🏃 Masculino", "👩 Femenino"])
    with col2:
        hand = st.selectbox("Mano:", ["Todas", "Diestro", "Zurdo"])
    with col3:
        search = st.text_input("🔍 Buscar:", placeholder="Nombre...")
    
    df = players_df.copy()
    
    if sex == "🏃 Masculino":
        df = df[df["sex"] == "M"]
    elif sex == "👩 Femenino":
        df = df[df["sex"] == "F"]
    
    hand_map = {"Diestro": "Right", "Zurdo": "Left"}
    if hand in hand_map:
        df = df[df["hand"] == hand_map[hand]]
    
    if search:
        df = df[
            df["first_name"].str.contains(search, case=False, na=False) |
            df["last_name"].str.contains(search, case=False, na=False) |
            df["short_name"].str.contains(search, case=False, na=False)
        ]
    
    st.markdown(f"**{len(df)}** jugadores encontrados")
    
    # Players grid
    per_page = 24
    total_pages = max(1, (len(df) + per_page - 1) // per_page)
    
    if total_pages > 1:
        page = st.number_input("Pág.", min_value=1, max_value=total_pages, value=1)
    else:
        page = 1
    
    start = (page - 1) * per_page
    
    cols = st.columns(3)
    for i, (_, p) in enumerate(df.iloc[start:start + per_page].iterrows()):
        with cols[i % 3]:
            sex_icon = "🏃" if p["sex"] == "M" else "👩"
            hand_icon = "✋" if p["hand"] == "Right" else "✌️" if p["hand"] == "Left" else ""
            
            img_html = ""
            if p["image_url"]:
                img_html = f'<img src="{p["image_url"]}" style="width:60px;height:60px;border-radius:50%;object-fit:cover;border:2px solid #eee;" />'
            else:
                img_html = f'<div style="width:60px;height:60px;border-radius:50%;background:#f0f0f0;display:flex;align-items:center;justify-content:center;font-size:1.5em;">🎾</div>'
            
            age = p["age"] if p["age"] else ""
            
            html = f"""
            <div class="player-card">
                {img_html}
                <div>
                    <div class="player-name">{p['first_name']} {p['last_name']}</div>
                    <div style="font-size:0.75em;color:#888;">
                        {sex_icon} · {hand_icon} · Ranking: #{p['ranking']}
                    </div>
                    <div style="font-size:0.75em;color:#aaa;">
                        {p['country']} · {age}
                    </div>
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)


# ─── PAGE: Statistics ───────────────────────────────────────────────────────

def show_stats():
    show_header("📊 Estadísticas del Torneo")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Country distribution - top 15
        country_counts = players_df["country"].value_counts().head(15).reset_index()
        country_counts.columns = ["País", "Jugadores"]
        fig = px.bar(
            country_counts, x="País", y="Jugadores",
            title="Top 15 Países por Jugadores",
            color="Jugadores",
            color_continuous_scale=["#e8f5e9", RG_GREEN],
            text="Jugadores",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            height=400,
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # World map
        country_counts_map = players_df["country"].value_counts().reset_index()
        country_counts_map.columns = ["country", "count"]
        
        # Country code mapping for plotly (ISO-3)
        country_iso = {
            "ITA": "ITA", "FRA": "FRA", "ESP": "ESP", "USA": "USA", "ARG": "ARG",
            "GBR": "GBR", "GER": "GER", "CZE": "CZE", "AUS": "AUS", "CHN": "CHN",
            "SRB": "SRB", "NED": "NED", "POL": "POL", "BRA": "BRA", "CAN": "CAN",
            "KAZ": "KAZ", "BOL": "BOL", "CRO": "CRO", "CHI": "CHI", "HUN": "HUN",
            "AUT": "AUT", "NOR": "NOR", "BEL": "BEL", "MON": "MON", "SUI": "SUI",
            "UKR": "UKR", "GRE": "GRE", "SVK": "SVK", "TUR": "TUR", "JPN": "JPN",
            "POR": "POR", "PER": "PER", "LAT": "LAT", "DEN": "DEN", "CHN": "CHN",
            "HKG": "HKG", "INA": "INA", "MEX": "MEX", "EGY": "EGY", "PHI": "PHI",
            "PAR": "PAR", "---": "", "": "",
        }
        country_counts_map["iso"] = country_counts_map["country"].map(country_iso)
        country_counts_map = country_counts_map[country_counts_map["iso"] != ""]
        
        fig = px.choropleth(
            country_counts_map,
            locations="iso",
            color="count",
            hover_name="country",
            color_continuous_scale=["#e8f5e9", RG_GREEN],
            title="Procedencia de los Jugadores",
        )
        fig.update_layout(height=400, geo=dict(showframe=False))
        st.plotly_chart(fig, use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Ranking distribution
        ranking_bins = pd.cut(
            players_df["ranking"].dropna(),
            bins=[0, 10, 20, 50, 100, 200, 500, 2000],
            labels=["Top 10", "11-20", "21-50", "51-100", "101-200", "201-500", "500+"],
        )
        rank_dist = ranking_bins.value_counts().sort_index().reset_index()
        rank_dist.columns = ["Rango", "Jugadores"]
        fig = px.bar(
            rank_dist, x="Rango", y="Jugadores",
            title="Distribución por Ranking",
            color="Jugadores",
            color_continuous_scale=["#fef0e6", RG_ORANGE],
            text="Jugadores",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=350, plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Sex distribution
        sex_data = players_df["sex"].value_counts().reset_index()
        sex_data.columns = ["sex", "count"]
        sex_data["label"] = sex_data["sex"].map({"M": "🏃 Hombres", "F": "👩 Mujeres"})
        fig = px.pie(
            sex_data, values="count", names="label",
            title="Hombres vs Mujeres",
            color="label",
            color_discrete_map={"🏃 Hombres": RG_GREEN, "👩 Mujeres": RG_ORANGE},
            hole=0.4,
        )
        fig.update_traces(textinfo="label+percent")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Handedness
        hand_data = players_df["hand"].fillna("Desconocido").value_counts().reset_index()
        hand_data.columns = ["Mano", "count"]
        fig = px.bar(
            hand_data, x="Mano", y="count",
            title="Mano Dominante",
            color="Mano",
            color_discrete_map={
                "Right": RG_GREEN, "Left": RG_ORANGE, "Desconocido": "#ccc",
            },
            text="count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, height=350, plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Match status
        status_data = matches_df["status"].value_counts().reset_index()
        status_data.columns = ["status", "count"]
        labels = {"NOT_STARTED": "⏳ No empezado", "IN_PROGRESS": "🔴 En vivo",
                  "FINISHED": "✅ Finalizado", "CANCELED": "❌ Cancelado",
                  "INTERRUPTED": "⚠️ Interrumpido"}
        status_data["label"] = status_data["status"].map(labels)
        colors = {"NOT_STARTED": "#bbb", "IN_PROGRESS": "#ff6b35",
                  "FINISHED": RG_GREEN, "CANCELED": "#dc3545", "INTERRUPTED": "#ffc107"}
        
        fig = go.Figure(data=[go.Pie(
            labels=status_data["label"],
            values=status_data["count"],
            marker=dict(colors=[colors.get(s, "#ccc") for s in status_data["status"]]),
            hole=0.4,
            textinfo="label+percent",
        )])
        fig.update_layout(title="Estado de Partidos", height=350)
        st.plotly_chart(fig, use_container_width=True)


# ─── PAGE: Head-to-Head ─────────────────────────────────────────────────────

def show_h2h():
    show_header("⚔️ Comparativa de Jugadores", "Selecciona dos jugadores para comparar sus perfiles")
    
    col1, col2 = st.columns(2)
    
    names = sorted(players_df["short_name"].unique())
    
    with col1:
        p1_name = st.selectbox("Jugador 1:", names, index=0)
    with col2:
        p2_name = st.selectbox("Jugador 2:", [n for n in names if n != p1_name], index=0)
    
    if p1_name and p2_name:
        p1 = players_df[players_df["short_name"] == p1_name].iloc[0]
        p2 = players_df[players_df["short_name"] == p2_name].iloc[0]
        
        col1, col2 = st.columns(2)
        
        for col, p in [(col1, p1), (col2, p2)]:
            with col:
                sex_icon = "🏃" if p["sex"] == "M" else "👩"
                name = f"{p['first_name']} {p['last_name']}"
                
                img_html = ""
                if p["image_url"]:
                    img_html = f'<img src="{p["image_url"]}" style="width:120px;height:120px;border-radius:50%;object-fit:cover;border:3px solid {RG_GREEN};margin:10px 0;" />'
                
                st.markdown(f"""
                <div style="text-align:center;background:white;border-radius:12px;padding:20px;border:1px solid #eee;">
                    {img_html}
                    <h3>{sex_icon} {name}</h3>
                    <p style="color:#888;"><strong>{p['short_name']}</strong></p>
                </div>
                """, unsafe_allow_html=True)
        
        # Stats comparison
        st.divider()
        st.markdown("### 📋 Ficha comparativa")
        
        stats = [
            ("Ranking", f"#{p1['ranking']}", f"#{p2['ranking']}"),
            ("País", p1['country'], p2['country']),
            ("Edad", p1['age'], p2['age']),
            ("Mano", p1['hand'], p2['hand']),
            ("Altura", p1['height'], p2['height']),
            ("Peso", p1['weight'], p2['weight']),
        ]
        
        html = "<table style='width:100%;border-collapse:collapse;'>"
        html += "<tr style='border-bottom:2px solid #eee;'><th style='padding:10px;text-align:left;color:grey;'>Atributo</th>"
        html += f"<th style='padding:10px;text-align:center;color:{RG_GREEN};'>{p1_name}</th>"
        html += f"<th style='padding:10px;text-align:center;color:{RG_ORANGE};'>{p2_name}</th></tr>"
        
        for label, v1, v2 in stats:
            winner = "⭐" if isinstance(v1, str) and isinstance(v2, str) and v1 and v2 and v1 != v2 else ""
            html += f"<tr style='border-bottom:1px solid #f0f0f0;'>"
            html += f"<td style='padding:8px 10px;font-weight:500;'>{label}</td>"
            html += f"<td style='padding:8px 10px;text-align:center;'>{v1} {winner if v1 and v2 and v1 != v2 else ''}</td>"
            html += f"<td style='padding:8px 10px;text-align:center;'>{v2}</td>"
            html += "</tr>"
        
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)
        
        # Radar chart
        st.divider()
        st.markdown("### 📊 Comparativa Radar")
        
        def score_ranking(r):
            return max(0, min(100, 100 - (r or 100) * 0.5))
        
        def score_age(a):
            m = re.search(r"(\d+)", str(a))
            if m:
                age = int(m.group(1))
                return max(0, min(100, (35 - age) * 5.8))
            return 50
        
        def score_height(h):
            m = re.search(r"(\d+)", str(h))
            if m:
                h_cm = int(m.group(1))
                return max(0, min(100, (h_cm - 160) * 2.6))
            return 50
        
        categories = ["Ranking", "Edad", "Altura", "Experiencia", "Potencial"]
        
        p1_vals = [
            score_ranking(p1["ranking"]),
            score_age(p1["age"]),
            score_height(p1["height"]),
            score_ranking(p1["ranking"]) * 0.7 + 30,
            score_age(p1["age"]) * 0.6 + 20,
        ]
        p2_vals = [
            score_ranking(p2["ranking"]),
            score_age(p2["age"]),
            score_height(p2["height"]),
            score_ranking(p2["ranking"]) * 0.7 + 30,
            score_age(p2["age"]) * 0.6 + 20,
        ]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=p1_vals + [p1_vals[0]],
            theta=categories + [categories[0]],
            name=p1_name,
            line=dict(color=RG_GREEN, width=3),
            fill="toself",
            fillcolor="rgba(0,80,60,0.1)",
        ))
        fig.add_trace(go.Scatterpolar(
            r=p2_vals + [p2_vals[0]],
            theta=categories + [categories[0]],
            name=p2_name,
            line=dict(color=RG_ORANGE, width=3),
            fill="toself",
            fillcolor="rgba(204,78,14,0.1)",
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], showticklabels=False),
            ),
            height=450,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2),
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Matchup info
        p1_id = p1["player_id"]
        p2_id = p2["player_id"]
        
        common = matches_df[
            ((matches_df["player_a_id"] == p1_id) & (matches_df["player_b_id"] == p2_id)) |
            ((matches_df["player_a_id"] == p2_id) & (matches_df["player_b_id"] == p1_id))
        ]
        
        if len(common) > 0:
            st.divider()
            st.markdown("### 🎯 Encuentro en el cuadro")
            for _, m in common.iterrows():
                icon = status_icon(m["status"])
                rname = round_name(m["round_number"])
                st.success(
                    f"{icon} **{m['draw_label']}** — {rname}: "
                    f"{m['player_a_name']} vs {m['player_b_name']} ({m['status_label']})"
                )


# ─── Router ─────────────────────────────────────────────────────────────────

if not DATA_OK:
    st.error("❌ No hay datos disponibles. Ejecuta el scraper primero:")
    st.code("cd /home/diaza/roland-data-garros && python3 -m scraper.scrape_draws")
else:
    if page == "🏆 Cuadro":
        show_bracket()
    elif page == "👤 Jugadores":
        show_players()
    elif page == "📊 Estadísticas":
        show_stats()
    elif page == "⚔️ Head-to-Head":
        show_h2h()