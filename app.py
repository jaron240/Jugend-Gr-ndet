import json
import sqlite3
import secrets
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "jugend_gruendet.db"


def get_connection() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db() -> None:
    with get_connection() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_bsc REAL DEFAULT 0,
                end_profit REAL DEFAULT 0,
                place INTEGER DEFAULT 0,
                current_period INTEGER DEFAULT 1,
                team_code TEXT
            );

            CREATE TABLE IF NOT EXISTS periods(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                period INTEGER NOT NULL,
                price1 REAL,
                price2 REAL,
                qty1 REAL,
                qty2 REAL,
                ads REAL,
                devs INTEGER,
                sales INTEGER,
                process REAL,
                profit REAL,
                bsc REAL,
                marketshare REAL,
                innovation REAL,
                awareness REAL,
                FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS strategic_decisions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                period INTEGER NOT NULL,
                decision_type TEXT NOT NULL,
                decision_value TEXT NOT NULL,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE CASCADE,
                UNIQUE(run_id, period, decision_type)
            );

            CREATE TABLE IF NOT EXISTS teams(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_code TEXT UNIQUE NOT NULL,
                team_name TEXT NOT NULL,
                created_by_device TEXT,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );


            """
        )


def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    with get_connection() as con:
        return pd.read_sql_query(sql, con, params=params)


def execute(sql: str, params: tuple = ()) -> int:
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(sql, params)
        con.commit()
        return cur.lastrowid


def format_currency(value: float) -> str:
    return f"{value:,.0f} EUR"


def format_run_label(runs: pd.DataFrame, run_id: int) -> str:
    match = runs.loc[runs["id"].eq(run_id), "name"]
    if match.empty:
        return f"Run #{run_id}"
    return f"{match.iloc[0]} (#{run_id})"


def build_backup_json() -> str:
    payload = {
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "runs": query_df("SELECT * FROM runs ORDER BY id").to_dict(orient="records"),
        "periods": query_df(
            "SELECT * FROM periods ORDER BY run_id, period, id"
        ).to_dict(orient="records"),
    }
    return json.dumps(payload, ensure_ascii=True, indent=2, default=str)


def save_period(
    run_id: int,
    period: int,
    price1: float,
    price2: float,
    qty1: int,
    qty2: int,
    ads: int,
    devs: int,
    sales: int,
    process: int,
    profit: float,
    bsc: float,
    marketshare: float,
    innovation: float,
    awareness: float,
) -> str:
    existing = query_df(
        "SELECT id FROM periods WHERE run_id = ? AND period = ? ORDER BY id LIMIT 1",
        (run_id, period),
    )

    values = (
        price1,
        price2,
        qty1,
        qty2,
        ads,
        devs,
        sales,
        process,
        profit,
        bsc,
        marketshare,
        innovation,
        awareness,
    )

    if existing.empty:
        execute(
            """
            INSERT INTO periods(
                run_id, period, price1, price2, qty1, qty2, ads, devs, sales,
                process, profit, bsc, marketshare, innovation, awareness
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, period, *values),
        )
        action = "saved"
    else:
        execute(
            """
            UPDATE periods
            SET price1 = ?, price2 = ?, qty1 = ?, qty2 = ?, ads = ?, devs = ?,
                sales = ?, process = ?, profit = ?, bsc = ?, marketshare = ?,
                innovation = ?, awareness = ?
            WHERE id = ?
            """,
            (*values, int(existing.iloc[0]["id"])),
        )
        action = "updated"

    execute(
        "UPDATE runs SET end_bsc = ?, end_profit = ? WHERE id = ?",
        (bsc, profit, run_id),
    )
    return action


init_db()

# SESSION STATE für Team-Kollaboration und Privatmodus
if 'team_code' not in st.session_state:
    st.session_state.team_code = None

if 'private_mode' not in st.session_state:
    st.session_state.private_mode = True  # Start im Privatmodus

# PERSISTENTE GERÄTE-BASIERTE TRENNUNG mit Session-Kontext
def get_session_based_device_id():
    """Generiert eine Device-ID basierend auf Session-Kontext für bessere Trennung"""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx:
            # Verwende Session-ID und andere Kontext-Informationen
            session_seed = f"{ctx.session_id}_{ctx.client_ip if hasattr(ctx, 'client_ip') else 'unknown'}_{secrets.token_hex(8)}"
            import hashlib
            device_id = hashlib.md5(session_seed.encode()).hexdigest()[:8].upper()
            return f"PRIVATE-{device_id}"
    except:
        pass

    # Fallback für den Fall, dass Kontext nicht verfügbar
    import hashlib
    import time
    device_seed = f"fallback_{time.time()}_{secrets.token_hex(8)}"
    device_id = hashlib.md5(device_seed.encode()).hexdigest()[:8].upper()
    return f"PRIVATE-{device_id}"

# Hole session-basierte Device-ID
if 'device_id' not in st.session_state:
    st.session_state.device_id = get_session_based_device_id()

# Im Privatmodus immer die Device-ID als Team-Code verwenden für echte Trennung
if st.session_state.private_mode:
    st.session_state.team_code = st.session_state.device_id
elif st.session_state.team_code is None:
    # Wenn kein Team-Code gesetzt und nicht im Privatmodus, Device-ID verwenden
    st.session_state.team_code = st.session_state.device_id

st.set_page_config(
    page_title="Planspiel Tracker JG",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* DARK MODE - SCHÖN & LESBAR */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
        line-height: 1.6;
    }

    /* HEADER - ELEGANTE GRADIENT */
    .main-header {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 50%, #1e40af 100%);
        color: white;
        padding: 3rem 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 20px 60px rgba(59, 130, 246, 0.15);
        position: relative;
        overflow: hidden;
    }
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: pulse 4s ease-in-out infinite;
    }
    .main-header h1 {
        position: relative;
        z-index: 2;
        margin: 0;
        font-size: 3rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        text-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    .main-header p {
        position: relative;
        z-index: 2;
        margin: 1rem 0 0;
        font-size: 1.2rem;
        opacity: 0.95;
        font-weight: 400;
    }

    /* KARTEN - GLAS-EFFEKT */
    .dashboard-card, .metric-card, .input-section, .decision-card, .settings-panel {
        background: rgba(30, 41, 59, 0.8);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 16px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .dashboard-card:hover, .metric-card:hover, .decision-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        border-color: rgba(59, 130, 246, 0.3);
    }

    /* METRIKEN - KLAR & ELEGANT */
    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: #60a5fa;
        margin: 0.5rem 0;
        text-shadow: 0 1px 2px rgba(0,0,0,0.5);
    }
    .metric-label {
        font-size: 0.9rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin: 0;
        font-weight: 600;
    }

    /* ENTSCHEIDUNGSKARTEN - FARBCODIERT */
    .decision-card {
        position: relative;
        overflow: hidden;
    }
    .decision-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 6px;
        height: 100%;
        background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%);
        border-radius: 0 4px 4px 0;
    }
    .conservative::before { background: linear-gradient(180deg, #10b981 0%, #059669 100%); }
    .balanced::before { background: linear-gradient(180deg, #f59e0b 0%, #d97706 100%); }
    .aggressive::before { background: linear-gradient(180deg, #ef4444 0%, #dc2626 100%); }

    /* BUTTONS - MODERN & INTERAKTIV */
    .stButton button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 1rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3);
        position: relative;
        overflow: hidden;
    }
    .stButton button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }
    .stButton button:hover::before {
        left: 100%;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4);
    }

    .delete-btn button {
        background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
        box-shadow: 0 4px 16px rgba(220, 38, 38, 0.3);
    }
    .delete-btn button:hover {
        box-shadow: 0 8px 25px rgba(220, 38, 38, 0.4);
    }

    /* FORM ELEMENTE - DARK THEME */
    .stSelectbox, .stNumberInput, .stSlider, .stTextInput {
        background: rgba(51, 65, 85, 0.8);
        border: 1px solid rgba(148, 163, 184, 0.3);
        border-radius: 12px;
        color: #f1f5f9;
        padding: 0.75rem;
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
    }
    .stSelectbox:hover, .stNumberInput:hover, .stSlider:hover, .stTextInput:hover {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        background: rgba(51, 65, 85, 0.9);
    }

    /* TABS - ELEGANTE NAVIGATION */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(30, 41, 59, 0.6);
        backdrop-filter: blur(20px);
        border-radius: 16px;
        padding: 0.75rem;
        border: 1px solid rgba(148, 163, 184, 0.1);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        gap: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8;
        border-radius: 12px;
        margin: 0;
        padding: 1rem 1.5rem;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    .stTabs [data-baseweb="tab"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.1), transparent);
        transition: left 0.5s;
    }
    .stTabs [data-baseweb="tab"]:hover::before {
        left: 100%;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #3b82f6;
        background: rgba(59, 130, 246, 0.1);
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.4);
        transform: translateY(-1px);
    }

    /* DATAFRAME - DARK THEME */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
    .stDataFrame [data-testid="stDataFrame"] {
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid rgba(148, 163, 184, 0.1);
    }

    /* ALERTS - SCHÖN GESTALTET */
    .warning-alert {
        background: rgba(245, 101, 101, 0.1);
        border: 1px solid rgba(245, 101, 101, 0.3);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: #fca5a5;
        backdrop-filter: blur(10px);
    }
    .success-alert {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: #6ee7b7;
        backdrop-filter: blur(10px);
    }

    /* FILE UPLOAD - ELEGANTE GESTALTUNG */
    .file-upload {
        border: 2px dashed rgba(148, 163, 184, 0.5);
        border-radius: 12px;
        padding: 3rem;
        text-align: center;
        background: rgba(51, 65, 85, 0.3);
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
        color: #94a3b8;
    }
    .file-upload:hover {
        border-color: #3b82f6;
        background: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
    }

    /* ANIMATIONS */
    @keyframes pulse {
        0%, 100% { opacity: 0.1; }
        50% { opacity: 0.2; }
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .dashboard-card, .metric-card, .decision-card {
        animation: fadeIn 0.6s ease-out;
    }

    /* RESPONSIVE DESIGN - MOBILE & TABLET OPTIMIERUNG */
    @media (max-width: 1024px) {
        /* Tablet */
        .main-header h1 {
            font-size: 2.2rem;
        }
        .metric-value {
            font-size: 2.2rem;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 0.8rem 1.2rem;
            font-size: 0.9rem;
        }
        .dashboard-card, .metric-card, .input-section, .decision-card, .settings-panel {
            padding: 1.5rem;
            margin: 1rem 0.5rem;
        }
    }

    @media (max-width: 768px) {
        /* Mobile */
        .main-header h1 {
            font-size: 1.8rem;
        }
        .main-header p {
            font-size: 1rem;
        }
        .metric-value {
            font-size: 1.8rem;
        }
        .metric-label {
            font-size: 0.8rem;
        }

        /* Tabs für Mobile optimieren */
        .stTabs [data-baseweb="tab-list"] {
            flex-wrap: wrap;
            gap: 0.25rem;
            padding: 0.5rem;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 0.6rem 0.8rem;
            font-size: 0.8rem;
            min-width: auto;
            flex: 1;
            text-align: center;
        }

        /* Karten für Mobile */
        .dashboard-card, .metric-card, .input-section, .decision-card, .settings-panel {
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 12px;
        }

        /* Buttons für Touch */
        .stButton button {
            padding: 0.8rem 1.2rem;
            font-size: 1rem;
            min-height: 44px; /* Apple Touch Target Size */
            width: 100%;
            margin: 0.25rem 0;
        }

        /* Form Elemente für Mobile */
        .stSelectbox, .stNumberInput, .stSlider, .stTextInput {
            margin: 0.5rem 0;
        }
        .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stTextInput input {
            font-size: 16px; /* Verhindert Zoom auf iOS */
            padding: 0.75rem;
            min-height: 44px;
        }

        /* Spalten für Mobile stacken */
        .stColumns {
            flex-direction: column;
        }
        .stColumns > div {
            margin: 0.5rem 0;
        }

        /* Charts für Mobile */
        .js-plotly-plot {
            height: 300px !important;
        }

        /* DataFrames für Mobile */
        .stDataFrame {
            font-size: 0.8rem;
            overflow-x: auto;
        }
    }

    @media (max-width: 480px) {
        /* Kleine Mobile */
        .main-header h1 {
            font-size: 1.5rem;
        }
        .main-header p {
            font-size: 0.9rem;
        }
        .metric-value {
            font-size: 1.5rem;
        }

        .stTabs [data-baseweb="tab"] {
            padding: 0.5rem 0.6rem;
            font-size: 0.75rem;
        }

        .dashboard-card, .metric-card, .input-section, .decision-card, .settings-panel {
            padding: 0.8rem;
        }

        .stButton button {
            padding: 0.7rem 1rem;
            font-size: 0.95rem;
        }
    }

    /* TOUCH-FRIENDLY INTERACTIONS */
    @media (hover: none) and (pointer: coarse) {
        /* Touch-Geräte */
        .stButton button {
            transform: none !important; /* Keine Hover-Effekte auf Touch */
        }

        .dashboard-card:hover, .metric-card:hover, .decision-card:hover {
            transform: none !important; /* Keine Hover-Effekte auf Touch */
        }
    }

    /* SAFARI & iOS SPEZIFISCH */
    @supports (-webkit-touch-callout: none) {
        /* iOS Safari */
        .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stTextInput input {
            font-size: 16px !important; /* Verhindert Zoom */
            -webkit-appearance: none;
            border-radius: 8px;
        }

        /* iOS Button Styling */
        .stButton button {
            -webkit-appearance: none;
            border-radius: 12px;
        }
    }

    /* TEXT LESBARKEIT SICHERSTELLEN */
    .stMarkdown, .stText, p, span, div {
        color: #f1f5f9 !important;
    }

    .stSelectbox div[data-baseweb="select"] span, .stNumberInput input, .stTextInput input {
        color: #f1f5f9 !important;
    }

    /* SICHERSTELLEN DASS ALLES LESBAR IST */
    * {
        color: #f1f5f9;
    }

    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        color: #f1f5f9 !important;
        font-weight: 700;
    }

    .stSuccess, .stWarning, .stError, .stInfo {
        background: rgba(30, 41, 59, 0.8) !important;
        color: #f1f5f9 !important;
        border-radius: 12px !important;
        border: 1px solid rgba(148, 163, 184, 0.2) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# TEAM-FILTERING: Zeige nur Runs des aktiven Teams oder alle Runs wenn kein Team aktiv
# Handle missing team_code column for backward compatibility
def get_runs_with_team_filter():
    # Check if team_code column exists
    column_exists = False
    try:
        # Try to query the column to see if it exists
        test_df = query_df("SELECT team_code FROM runs LIMIT 1")
        column_exists = True
    except:
        # Column doesn't exist, try to add it
        try:
            execute("ALTER TABLE runs ADD COLUMN team_code TEXT DEFAULT ''")
            column_exists = True
        except:
            # Can't add column, will work without team filtering
            column_exists = False

    # Query based on column availability
    if column_exists:
        # Always show runs with the current team_code (which is device_id in private mode)
        return query_df("SELECT * FROM runs WHERE team_code = ? ORDER BY id DESC", (st.session_state.team_code,))
    else:
        # Fallback: no team filtering available, show all runs
        return query_df("SELECT * FROM runs ORDER BY id DESC")

runs_df = get_runs_with_team_filter()

# KOMPAKTER HEADER
st.title("🎯 Planspiel Tracker JG")
st.caption("Live-Entscheidungshilfe für Jugend Gründet Teams")

# Team-Status Anzeige
col1, col2 = st.columns([6, 1])

with col1:
    if st.session_state.private_mode:
        st.info("🔒 **Privatmodus** - nur deine Daten")
    elif st.session_state.team_code:
        teams_df = query_df("SELECT * FROM teams WHERE team_code = ?", (st.session_state.team_code,))
        team_name = teams_df.iloc[0]['team_name'] if not teams_df.empty else "Unbekanntes Team"
        st.success(f"👥 **Team:** {team_name}")
    else:
        st.info("🔒 **Privatmodus** - nur deine Daten")

with col2:
    st.download_button(
        "💾 Backup",
        data=build_backup_json(),
        file_name="planspiel_tracker_jg_backup.json",
        mime="application/json",
        use_container_width=True,
    )

# EINZELNE TABS STATT SIDEBAR
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏠 Dashboard", "⚡ Quick Input", "🎯 Entscheidungen", "📊 Analyse",
    "🚨 Frühwarnsystem", "⚙️ Einstellungen", "🗑️ Run Management"
])

# TAB 1: LIVE CENTER - IMMER SICHTBAR
with tab1:
    if not runs_df.empty:
        st.subheader("📊 Aktuelle Runs")

        # Schnellübersicht
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if "current_period" in runs_df.columns:
                active_runs = len(runs_df[runs_df["current_period"] <= 8])
            else:
                active_runs = len(runs_df)
            st.metric("Aktive Runs", active_runs)

        with col2:
            if not runs_df.empty:
                best_bsc = runs_df["end_bsc"].max()
                st.metric("Bester BSC", f"{best_bsc:.1f}")

        with col3:
            if "current_period" in runs_df.columns:
                completed_runs = len(runs_df[runs_df["current_period"] > 8])
            else:
                completed_runs = 0
            st.metric("Abgeschlossene Runs", completed_runs)

        with col4:
            avg_bsc = runs_df["end_bsc"].mean() if not runs_df.empty else 0
            st.metric("Ø BSC", f"{avg_bsc:.1f}")

        # ERWEITERTE VISUALISIERUNGEN
        st.markdown("### 📈 Performance Übersicht")

        # BSC vs Gewinn Scatterplot
        col1, col2 = st.columns(2)
        with col1:
            scatter = px.scatter(
                runs_df,
                x="end_profit",
                y="end_bsc",
                text="name",
                title="BSC vs. Gewinn",
                color="end_bsc",
                color_continuous_scale="RdYlGn",
                size="end_bsc",
            )
            scatter.update_traces(textposition="top center")
            st.plotly_chart(scatter, use_container_width=True)

        with col2:
            # BSC-Verteilung
            bsc_hist = px.histogram(
                runs_df,
                x="end_bsc",
                title="BSC-Verteilung aller Runs",
                color_discrete_sequence=["#60a5fa"],
                nbins=10
            )
            bsc_hist.update_layout(showlegend=False)
            st.plotly_chart(bsc_hist, use_container_width=True)

        # Zeitliche Entwicklung
        st.markdown("### 📊 Entwicklung über Zeit")

        # Sammle alle Perioden-Daten für Zeitreihe
        all_periods_data = []
        for run_id in runs_df["id"]:
            periods = query_df("SELECT period, bsc, profit, marketshare FROM periods WHERE run_id = ? ORDER BY period", (run_id,))
            if not periods.empty:
                for _, period in periods.iterrows():
                    all_periods_data.append({
                        "Run": runs_df.loc[runs_df["id"] == run_id, "name"].iloc[0],
                        "Periode": period["period"],
                        "BSC": period["bsc"],
                        "Gewinn": period["profit"],
                        "Marktanteil": period["marketshare"]
                    })

        if all_periods_data:
            timeline_df = pd.DataFrame(all_periods_data)

            # BSC Timeline
            bsc_timeline = px.line(
                timeline_df,
                x="Periode",
                y="BSC",
                color="Run",
                title="BSC-Entwicklung aller Runs",
                markers=True
            )
            st.plotly_chart(bsc_timeline, use_container_width=True)

            # Gewinn Timeline
            profit_timeline = px.line(
                timeline_df,
                x="Periode",
                y="Gewinn",
                color="Run",
                title="Gewinn-Entwicklung aller Runs",
                markers=True
            )
            st.plotly_chart(profit_timeline, use_container_width=True)

        # Top Performer Charts
        st.markdown("### 🏆 Top Performer")

        col1, col2 = st.columns(2)
        with col1:
            # Top BSC Runs
            top_bsc = runs_df.nlargest(5, "end_bsc")
            bsc_bar = px.bar(
                top_bsc,
                x="name",
                y="end_bsc",
                title="Top 5 BSC-Scores",
                color="end_bsc",
                color_continuous_scale="Greens"
            )
            bsc_bar.update_layout(showlegend=False)
            st.plotly_chart(bsc_bar, use_container_width=True)

        with col2:
            # Top Profit Runs
            top_profit = runs_df.nlargest(5, "end_profit")
            profit_bar = px.bar(
                top_profit,
                x="name",
                y="end_profit",
                title="Top 5 Gewinne",
                color="end_profit",
                color_continuous_scale="Blues"
            )
            profit_bar.update_layout(showlegend=False)
            st.plotly_chart(profit_bar, use_container_width=True)

        # Korrelationsanalyse
        st.markdown("### 🔍 Korrelationsanalyse")

        if len(runs_df) > 1:
            corr_matrix = runs_df[["end_bsc", "end_profit", "place"]].corr()

            # Korrelations-Heatmap
            heatmap = px.imshow(
                corr_matrix,
                text_auto=True,
                title="Korrelationsmatrix",
                color_continuous_scale="RdBu_r",
                aspect="auto"
            )
            heatmap.update_layout(
                xaxis_title="",
                yaxis_title=""
            )
            st.plotly_chart(heatmap, use_container_width=True)

            # Scatterplot Matrix
            scatter_matrix = px.scatter_matrix(
                runs_df,
                dimensions=["end_bsc", "end_profit", "place"],
                title="Scatterplot Matrix",
                color="end_bsc",
                color_continuous_scale="Viridis"
            )
            st.plotly_chart(scatter_matrix, use_container_width=True)

    else:
        st.info("👋 Willkommen! Erstelle deinen ersten Run im 'Quick Input' Tab.")

# TAB 2: QUICK INPUT - ALLES IN EINEM FENSTER
with tab2:
    st.subheader("⚡ SCHNELL-EINGABE")

    # Run Auswahl / Erstellung
    if not runs_df.empty:
        run_ids = runs_df["id"].tolist()
        selected_run = st.selectbox(
            "Run wählen",
            run_ids,
            format_func=lambda value: format_run_label(runs_df, value),
            key="run_selector"
        )
    else:
        selected_run = None

    # Neuer Run Button
    if st.button("➕ Neuer Run", type="primary"):
        new_name = f"Run {len(runs_df) + 1}"
        # Run mit Team-Code verknüpfen falls aktiv
        team_code = st.session_state.team_code if st.session_state.team_code else None
        execute("INSERT INTO runs(name, end_bsc, end_profit, place, team_code) VALUES(?, ?, ?, ?, ?)",
                (new_name, 0, 0, 0, team_code))
        st.success(f"Run '{new_name}' erstellt!" + (f" (Team: {team_code})" if team_code else ""))
        st.rerun()

    if selected_run:
        # Periode auswählen
        max_period_df = query_df("SELECT MAX(period) AS max_period FROM periods WHERE run_id = ?", (selected_run,))
        max_period = max_period_df.iloc[0]["max_period"]
        next_period = 1 if pd.isna(max_period) else min(8, int(max_period) + 1)

        period = st.selectbox("Periode", list(range(1, 9)), index=next_period-1, key="period_selector")

        # Periodenbewusste Eingabe
        st.markdown('<div class="quick-input">', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("💰 Preise & Mengen")
            price1 = st.number_input("Preis Markt 1", 450, 700, 559, key="price1")

            # Markt 2 nur ab Periode 5
            if period >= 5:
                price2 = st.number_input("Preis Markt 2", 450, 700, 549, key="price2")
                qty2 = st.number_input("Menge Markt 2", 0, 10000, 500, key="qty2")
            else:
                price2 = 0
                qty2 = 0

            qty1 = st.number_input("Menge Markt 1", 1000, 10000, 4000, key="qty1")

        with col2:
            st.subheader("👥 Personal & Budget")
            ads = st.number_input("Werbung", 50000, 500000, 150000, step=10000, key="ads")
            devs = st.number_input("Entwickler", 3, 10, 6, key="devs")
            sales = st.number_input("Vertrieb", 3, 10, 6, key="sales")
            process = st.number_input("Prozessbudget", 50000, 200000, 100000, step=10000, key="process")

        st.markdown('</div>', unsafe_allow_html=True)

        # Ergebnisse
        st.subheader("📈 Periodenergebnisse")

        col1, col2 = st.columns(2)
        with col1:
            profit = st.number_input("Gewinn", -1000000, 10000000, 0, step=10000, key="profit")
            bsc = st.number_input("BSC", 0.0, 1000.0, 0.0, step=10.0, key="bsc")

        with col2:
            marketshare = st.number_input("Marktanteil %", 0.0, 100.0, 20.0, step=5.0, key="marketshare")
            awareness = st.number_input("Bekanntheit", 0, 1000, 100, key="awareness")
            innovation = st.number_input("Innovation", 0, 1000, 200, key="innovation")

        # Speichern Button
        if st.button("💾 Periode speichern", type="primary", use_container_width=True):
            action = save_period(
                run_id=selected_run,
                period=period,
                price1=price1,
                price2=price2,
                qty1=qty1,
                qty2=qty2,
                ads=ads,
                devs=devs,
                sales=sales,
                process=process,
                profit=profit,
                bsc=bsc,
                marketshare=marketshare,
                innovation=innovation,
                awareness=awareness,
            )
            st.success(f"✅ Periode {period} gespeichert!")

# TAB 3: ENTSCHEIDUNGEN - VEREINFACHT
with tab3:
    st.subheader("🎯 SCHNELLE ENTSCHEIDUNGSHILFE")

    col1, col2 = st.columns(2)
    with col1:
        current_period = st.selectbox("Periode", list(range(1, 9)), index=0, key="decision_period")
        market_growth = st.slider("Marktwachstum %", -15, 20, 5, key="market_growth")

    with col2:
        competitor_price = st.number_input("Konkurrenz Preis", 450, 700, 559, key="comp_price")
        current_marketshare = st.slider("Dein Marktanteil %", 5, 50, 20, key="marketshare_slider")

    # Phase bestimmen
    if current_period <= 2:
        phase = "Frühphase"
    elif current_period <= 5:
        phase = "Mittelphase"
    else:
        phase = "Endgame"

    st.markdown(f"### 📊 {phase} (Periode {current_period})")

    # AUSFÜHRLICHE EMPFEHLUNGEN MIT BEGRÜNDUNG
    st.markdown("### 📋 Detaillierte Handlungsempfehlungen")

    # Berechne erwartete Auswirkungen
    price_diff = competitor_price - 559  # Referenzpreis
    market_pressure = "hoch" if price_diff > 20 else "mittel" if price_diff > 0 else "niedrig"

    # DREI OPTIONEN - AUSFÜHRLICH
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="decision-card conservative">
            <h4>🟢 SICHER - Risikominimierung</h4>
            """,
            unsafe_allow_html=True
        )

        if current_period <= 2:
            cons_price, cons_ads, cons_devs, cons_sales = 569, 100000, 5, 4
            cons_strategy = "Vertrauen aufbauen, stabile Basis schaffen"
            cons_risks = "Langsames Wachstum, verpasste Marktchancen"
            cons_benefits = "Sicherer Start, geringe Verluste, BSC-Grundlage"
        elif current_period <= 5:
            cons_price, cons_ads, cons_devs, cons_sales = 559, 150000, 6, 6
            cons_strategy = "Solide Marktposition halten, kontrolliert wachsen"
            cons_risks = "Konkurrenz könnte überholen"
            cons_benefits = "Stabile Margen, planbare Entwicklung"
        else:
            cons_price, cons_ads, cons_devs, cons_sales = 579, 200000, 7, 7
            cons_strategy = "BSC absichern, keine Fehler in Endphase"
            cons_risks = "Zu defensiv, Siegchance sinkt"
            cons_benefits = "Sicherer BSC, minimale Verluste"

        st.markdown(f"""
        **💰 Preis:** {cons_price}€
        **📢 Werbung:** {cons_ads:,}€
        **👨‍💼 Entwickler:** {cons_devs}
        **👨‍💼 Vertrieb:** {cons_sales}

        **🎯 Strategie:** {cons_strategy}

        **✅ Vorteile:** {cons_benefits}

        **⚠️ Risiken:** {cons_risks}
        """)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown(
            """
            <div class="decision-card balanced">
            <h4>🟡 BALANCIERT - Optimale Balance</h4>
            """,
            unsafe_allow_html=True
        )

        if current_period <= 2:
            bal_price, bal_ads, bal_devs, bal_sales = 559, 120000, 5, 5
            bal_strategy = "Ausgewogene Entwicklung, Marktchancen nutzen"
            bal_risks = "Mögliche Überinvestition bei Marktschwäche"
            bal_benefits = "Gute Marktposition, BSC-Aufbau, flexible Anpassung"
        elif current_period <= 5:
            bal_price, bal_ads, bal_devs, bal_sales = 549, 170000, 6, 6
            bal_strategy = "Aktives Wachstum mit Risikokontrolle"
            bal_risks = "Cashflow-Engpässe bei Fehleinschätzungen"
            bal_benefits = "Starke Marktposition, Innovation, Wettbewerbsfähigkeit"
        else:
            bal_price, bal_ads, bal_devs, bal_sales = 569, 220000, 7, 7
            bal_strategy = "BSC-Maximierung mit Gewinnorientierung"
            bal_risks = "Zu hohe Investitionen bei BSC-Fokus"
            bal_benefits = "Hohe Siegchance, optimale BSC-Gewinn-Balance"

        st.markdown(f"""
        **💰 Preis:** {bal_price}€
        **📢 Werbung:** {bal_ads:,}€
        **👨‍💼 Entwickler:** {bal_devs}
        **👨‍💼 Vertrieb:** {bal_sales}

        **🎯 Strategie:** {bal_strategy}

        **✅ Vorteile:** {bal_benefits}

        **⚠️ Risiken:** {bal_risks}
        """)
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown(
            """
            <div class="decision-card aggressive">
            <h4>🔴 AGGRESSIV - Volles Risiko</h4>
            """,
            unsafe_allow_html=True
        )

        if current_period <= 2:
            agg_price, agg_ads, agg_devs, agg_sales = 549, 140000, 6, 6
            agg_strategy = "Schneller Markteintritt, Dominanz aufbauen"
            agg_risks = "Hohe Verluste bei Misserfolg, Cashflow-Krise"
            agg_benefits = "Marktführerschaft möglich, starker BSC-Boost"
        elif current_period <= 5:
            agg_price, agg_ads, agg_devs, agg_sales = 539, 190000, 7, 7
            agg_strategy = "Maximale Marktpenetration, Innovationsführerschaft"
            agg_risks = "Existenzbedrohende Verluste, Arbeitsplatzabbau"
            agg_benefits = "Höchste Siegchance, Marktdominanz, BSC-Maximum"
        else:
            agg_price, agg_ads, agg_devs, agg_sales = 559, 240000, 8, 8
            agg_strategy = "Alles oder nichts - maximale BSC-Optimierung"
            agg_risks = "Totale Pleite bei Fehlentscheidungen"
            agg_benefits = "Höchstmögliche Siegchance, perfekte BSC"

        st.markdown(f"""
        **💰 Preis:** {agg_price}€
        **📢 Werbung:** {agg_ads:,}€
        **👨‍💼 Entwickler:** {agg_devs}
        **👨‍💼 Vertrieb:** {agg_sales}

        **🎯 Strategie:** {agg_strategy}

        **✅ Vorteile:** {agg_benefits}

        **⚠️ Risiken:** {agg_risks}
        """)
        st.markdown("</div>", unsafe_allow_html=True)

    # MARKTSITUATIONS-ANALYSE
    st.markdown("### 📊 Marktsituations-Analyse")

    situation_analysis = []

    if market_growth > 10:
        situation_analysis.append("📈 **Boom-Markt:** Höhere Investitionen lohnen sich, aggressivere Preise möglich")
    elif market_growth < -5:
        situation_analysis.append("📉 **Schwacher Markt:** Konservative Strategie, Preise anpassen, Investitionen reduzieren")

    if competitor_price < 550:
        situation_analysis.append("⚠️ **Preisdruck:** Konkurrenz ist günstig - Preisstrategie überdenken")
    elif competitor_price > 580:
        situation_analysis.append("💰 **Preisfreiheit:** Konkurrenz ist teuer - höhere Margen möglich")

    if current_marketshare < 20:
        situation_analysis.append("🎯 **Marktchance:** Niedriger Marktanteil - Wachstumspotenzial vorhanden")
    elif current_marketshare > 35:
        situation_analysis.append("👑 **Marktführer:** Hoher Marktanteil - Verteidigungsposition stärken")

    if situation_analysis:
        for analysis in situation_analysis:
            st.info(analysis)
    else:
        st.success("📊 Marktsituation ist ausgewogen - alle Strategien möglich")

    # BSC-ERINNERUNG
    st.markdown("### 🏆 BSC-Erinnerung")
    st.warning("""
    **WICHTIG:** Jugend Gründet bewertet NICHT nur Gewinn!

    **Entscheidend sind:**
    - **Innovation** (Forschung & Entwicklung)
    - **Bekanntheit** (Marketing & PR)
    - **Arbeitsplätze** (Personalaufstockung)
    - **Nachhaltigkeit** (strategische Entscheidungen)
    - **Gesellschaftliche Bedeutung** (strategische Ausrichtung)

    Hoher Gewinn ohne BSC = **KEIN SIEG!**
    """)

# TAB 4: ANALYSE - VEREINFACHT
with tab4:
    st.subheader("📊 RUN ANALYSE")

    if runs_df.empty:
        st.info("Noch keine Runs vorhanden.")
    else:
        run_ids = runs_df["id"].tolist()
        run_id = st.selectbox(
            "Run analysieren",
            run_ids,
            format_func=lambda value: format_run_label(runs_df, value),
            key="analysis_run"
        )

        periods_df = query_df(
            "SELECT * FROM periods WHERE run_id = ? ORDER BY period",
            (run_id,),
        )

        if periods_df.empty:
            st.info("Keine Daten für diesen Run.")
        else:
            # Metriken
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Perioden", len(periods_df))
            col2.metric("Max BSC", f"{periods_df['bsc'].max():.1f}")
            col3.metric("Max Gewinn", format_currency(float(periods_df["profit"].max())))
            col4.metric("Ø Marktanteil", f"{periods_df['marketshare'].mean():.1f}%")

            # ERWEITERTE VISUALISIERUNGEN
            st.markdown("### 📈 Detaillierte Analyse")

            # Haupt-KPIs Timeline
            col1, col2 = st.columns(2)
            with col1:
                # Multi-Line Chart für alle wichtigen Metriken
                multi_line = px.line(
                    periods_df.melt(id_vars=['period'],
                                  value_vars=['profit', 'bsc', 'marketshare', 'innovation', 'awareness'],
                                  var_name='Metrik', value_name='Wert'),
                    x='period', y='Wert', color='Metrik',
                    title='Alle KPIs im Zeitverlauf',
                    markers=True
                )
                multi_line.update_layout(
                    yaxis_title='Wert',
                    legend_title='Metrik'
                )
                st.plotly_chart(multi_line, use_container_width=True)

            with col2:
                # Korrelationsmatrix für diesen Run
                corr_vars = ['profit', 'bsc', 'marketshare', 'innovation', 'awareness', 'ads', 'devs', 'sales']
                corr_data = periods_df[corr_vars].corr()

                heatmap = px.imshow(
                    corr_data,
                    text_auto='.2f',
                    title='Korrelationsmatrix',
                    color_continuous_scale='RdBu_r',
                    aspect='auto'
                )
                heatmap.update_layout(
                    xaxis_title='',
                    yaxis_title=''
                )
                st.plotly_chart(heatmap, use_container_width=True)

            # Performance Breakdown
            st.markdown("### 📊 Performance Breakdown")

            perf_col1, perf_col2, perf_col3 = st.columns(3)

            with perf_col1:
                # BSC-Komponenten als Radar Chart
                if len(periods_df) >= 3:
                    latest_three = periods_df.tail(3)
                    radar_data = pd.DataFrame({
                        'Periode': [f'P{p}' for p in latest_three['period']],
                        'Innovation': latest_three['innovation'],
                        'Bekanntheit': latest_three['awareness'],
                        'Marktanteil': latest_three['marketshare']
                    })

                    radar_fig = px.line_polar(
                        radar_data.melt(id_vars=['Periode'], var_name='Komponente', value_name='Wert'),
                        r='Wert', theta='Komponente', color='Periode',
                        line_close=True, title='BSC-Komponenten Entwicklung'
                    )
                    st.plotly_chart(radar_fig, use_container_width=True)
                else:
                    st.info("Mindestens 3 Perioden für Radar-Chart benötigt")

            with perf_col2:
                # Investitions-Effizienz
                periods_df['invest_total'] = periods_df['ads'] + periods_df['process'] + (periods_df['devs'] + periods_df['sales']) * 50000
                periods_df['roi'] = periods_df['profit'] / periods_df['invest_total'].replace(0, 1) * 100

                roi_chart = px.bar(
                    periods_df, x='period', y='roi',
                    title='ROI pro Periode (%)',
                    color='roi',
                    color_continuous_scale='RdYlGn'
                )
                roi_chart.update_layout(showlegend=False)
                st.plotly_chart(roi_chart, use_container_width=True)

            with perf_col3:
                # Wachstumsraten
                periods_df['profit_growth'] = periods_df['profit'].pct_change() * 100
                periods_df['bsc_growth'] = periods_df['bsc'].pct_change() * 100

                growth_data = periods_df[['period', 'profit_growth', 'bsc_growth']].melt(
                    id_vars=['period'], var_name='Metrik', value_name='Wachstum'
                )

                growth_chart = px.bar(
                    growth_data, x='period', y='Wachstum', color='Metrik',
                    title='Wachstumsraten (%)',
                    barmode='group',
                    color_discrete_map={'profit_growth': '#10b981', 'bsc_growth': '#f59e0b'}
                )
                st.plotly_chart(growth_chart, use_container_width=True)

            # Strategische Analyse
            st.markdown("### 🎯 Strategische Analyse")

            strat_col1, strat_col2 = st.columns(2)

            with strat_col1:
                # Preisstrategie Analyse
                periods_df['price_trend'] = periods_df['price1'].pct_change() * 100

                price_analysis = px.scatter(
                    periods_df, x='price1', y='marketshare', size='ads',
                    color='period', title='Preis vs. Marktanteil',
                    color_continuous_scale='Viridis'
                )
                price_analysis.update_layout(
                    xaxis_title='Preis (€)',
                    yaxis_title='Marktanteil (%)'
                )
                st.plotly_chart(price_analysis, use_container_width=True)

            with strat_col2:
                # Werbeeffizienz
                periods_df['ads_efficiency'] = periods_df['awareness'] / periods_df['ads'].replace(0, 1) * 1000

                ads_eff = px.line(
                    periods_df, x='period', y='ads_efficiency', markers=True,
                    title='Werbeeffizienz (Bekanntheit/€)',
                    color_discrete_sequence=['#8b5cf6']
                )
                st.plotly_chart(ads_eff, use_container_width=True)

            # Daten-Tabelle mit erweiterten Metriken
            st.markdown("### 📋 Detaillierte Daten")

            # Berechne zusätzliche Metriken
            analysis_df = periods_df.copy()
            analysis_df['invest_total'] = analysis_df['ads'] + analysis_df['process'] + (analysis_df['devs'] + analysis_df['sales']) * 50000
            analysis_df['margin'] = (analysis_df['profit'] / analysis_df['invest_total'].replace(0, 1)) * 100
            analysis_df['efficiency_score'] = (analysis_df['bsc'] + analysis_df['marketshare'] + analysis_df['innovation']/10 + analysis_df['awareness']/10) / 4

            display_cols = ['period', 'price1', 'qty1', 'ads', 'devs', 'sales', 'profit', 'bsc',
                          'marketshare', 'innovation', 'awareness', 'invest_total', 'margin', 'efficiency_score']

            st.dataframe(
                analysis_df[display_cols].round(2),
                use_container_width=True,
                hide_index=True,
                column_config={
                    'period': 'Periode',
                    'price1': 'Preis 1 (€)',
                    'qty1': 'Menge 1',
                    'ads': 'Werbung (€)',
                    'devs': 'Entwickler',
                    'sales': 'Vertrieb',
                    'profit': 'Gewinn (€)',
                    'bsc': 'BSC',
                    'marketshare': 'Marktanteil (%)',
                    'innovation': 'Innovation',
                    'awareness': 'Bekanntheit',
                    'invest_total': 'Gesamt-Invest (€)',
                    'margin': 'Marge (%)',
                    'efficiency_score': 'Effizienz-Score'
                }
            )

# TAB 5: FRÜHWARNSYSTEM
with tab5:
    st.subheader("🚨 FRÜHWARNSYSTEM")
    st.caption("Risiken erkennen und vermeiden - bevor es zu spät ist")

    if runs_df.empty:
        st.warning("Lege zuerst einen Run an.")
    else:
        run_ids = runs_df["id"].tolist()
        run_id = st.selectbox(
            "Run analysieren",
            run_ids,
            format_func=lambda value: format_run_label(runs_df, value),
            key="warning_run"
        )

        periods_df = query_df(
            "SELECT * FROM periods WHERE run_id = ? ORDER BY period DESC LIMIT 1",
            (run_id,),
        )

        if periods_df.empty:
            st.info("Noch keine Periodendaten vorhanden.")
        else:
            latest = periods_df.iloc[0]
            current_period = runs_df.loc[runs_df["id"] == run_id, "current_period"].iloc[0] if "current_period" in runs_df.columns else 1

            st.markdown("### 📊 Aktuelle Situation")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Periode", current_period)
            col2.metric("BSC", f"{latest['bsc']:.1f}")
            col3.metric("Marktanteil", f"{latest['marketshare']:.1f}%")
            col4.metric("Bekanntheit", f"{latest['awareness']:.1f}")

            # RISIKOANALYSE
            st.markdown("### ⚠️ KRITISCHE RISIKEN")

            risks = []

            # Überinvestitionsrisiko
            total_investment = latest['ads'] + latest['process'] + (latest['devs'] + latest['sales']) * 50000
            if total_investment > latest['profit'] * 2 and latest['profit'] > 0:
                risk_level = "🔴 HOCH" if total_investment > latest['profit'] * 3 else "🟡 MITTEL"
                risks.append({
                    "type": "Überinvestition",
                    "level": risk_level,
                    "description": f"Investitionen ({total_investment:,}€) übersteigen Gewinn ({latest['profit']:,.0f}€) deutlich",
                    "consequence": "Cashflow-Probleme, BSC-Verlust durch Arbeitsplatzabbau",
                    "recommendation": "Investitionen um 20-30% reduzieren, Fokus auf Effizienz"
                })

            # Marktverlust-Risiko
            if latest['marketshare'] < 15 and current_period > 3:
                risks.append({
                    "type": "Marktverlust",
                    "level": "🔴 HOCH",
                    "description": f"Marktanteil nur {latest['marketshare']:.1f}% - zu niedrig für Periode {current_period}",
                    "consequence": "Konkurrenz übernimmt Markt, kein Wachstum möglich",
                    "recommendation": "Preis aggressiver senken, Werbung massiv erhöhen (+50k)"
                })

            # BSC-Verlust-Risiko
            bsc_risk_score = 0
            if latest['innovation'] < 200 and current_period > 4:
                bsc_risk_score += 2
            if latest['awareness'] < 150 and current_period > 5:
                bsc_risk_score += 2
            if latest['devs'] < 6 and current_period > 6:
                bsc_risk_score += 1

            if bsc_risk_score >= 3:
                risks.append({
                    "type": "BSC-Verlust",
                    "level": "🔴 KRITISCH",
                    "description": f"BSC-Komponenten zu niedrig für Endgame (Score: {bsc_risk_score}/5)",
                    "consequence": "Sieg unmöglich, auch bei hohem Gewinn",
                    "recommendation": "Sofort Innovation >200, Bekanntheit >150, Mitarbeiter +1"
                })

            # Planungsfehler-Risiko
            if current_period > 1:
                prev_periods = query_df(
                    "SELECT * FROM periods WHERE run_id = ? ORDER BY period DESC LIMIT 2",
                    (run_id,),
                )
                if len(prev_periods) >= 2:
                    prev_qty = prev_periods.iloc[1]['qty1']
                    curr_qty = latest['qty1']
                    qty_change = abs(curr_qty - prev_qty) / prev_qty if prev_qty > 0 else 0

                    if qty_change > 0.5:  # >50% Änderung
                        risks.append({
                            "type": "Planungsfehler",
                            "level": "🟡 MITTEL",
                            "description": f"Bestellmenge um {qty_change:.0%} geändert - zu große Sprünge",
                            "consequence": "Lagerprobleme, Cashflow-Unsicherheit",
                            "recommendation": "Mengenänderungen auf max. 30% pro Periode begrenzen"
                        })

            # Anzeige der Risiken
            if risks:
                for risk in risks:
                    st.error(f"""
                    **{risk['level']} - {risk['type']}**

                    {risk['description']}

                    **Folge:** {risk['consequence']}

                    **Empfehlung:** {risk['recommendation']}
                    """)
            else:
                st.success("✅ Keine kritischen Risiken erkannt - gute Arbeit!")

            # PRÄVENTIVE HINWEISE
            st.markdown("### 💡 Präventive Hinweise")

            tips = []

            if current_period <= 3 and latest['ads'] < 120000:
                tips.append("Frühphase: Werbung auf mind. 120k€ erhöhen für Markenaufbau")

            if current_period >= 6 and latest['devs'] < 7:
                tips.append("Endgame: Mindestens 7 Entwickler für BSC-Maximierung")

            if latest['innovation'] < 250 and current_period >= 7:
                tips.append("Innovation sollte >250 sein für Top-BSC-Platzierungen")

            if latest['marketshare'] < 25 and current_period >= 5:
                tips.append("Marktanteil sollte >25% sein für Wettbewerbsfähigkeit")

            for tip in tips:
                st.info(f"• {tip}")

# TAB 6: EINSTELLUNGEN
with tab6:
    st.subheader("⚙️ EINSTELLUNGEN")
    st.caption("Daten verwalten und zwischen Geräten synchronisieren")

    st.markdown('<div class="settings-panel">', unsafe_allow_html=True)
    st.subheader("💾 Daten-Export")

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📄 JSON Export (vollständig)",
            data=build_backup_json(),
            file_name=f"jugend_gruender_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
            help="Enthält alle Runs, Perioden und strategischen Entscheidungen"
        )

    with col2:
        if not runs_df.empty:
            # CSV Export für aktuellen Run
            run_ids = runs_df["id"].tolist()
            export_run_id = st.selectbox(
                "Run für CSV-Export",
                run_ids,
                format_func=lambda value: format_run_label(runs_df, value),
                key="export_run"
            )

            periods_df = query_df("SELECT * FROM periods WHERE run_id = ? ORDER BY period", (export_run_id,))
            if not periods_df.empty:
                csv_data = periods_df.to_csv(index=False)
                st.download_button(
                    "📊 CSV Export (Run-Daten)",
                    data=csv_data,
                    file_name=f"run_{export_run_id}_perioden.csv",
                    mime="text/csv",
                    use_container_width=True,
                    help="Excel-kompatible Tabelle mit Periodendaten"
                )

    st.markdown("---")
    st.subheader("📤 Daten-Import")

    uploaded_file = st.file_uploader(
        "JSON-Backup hochladen",
        type=["json"],
        help="Lade eine zuvor exportierte JSON-Datei hoch, um Daten wiederherzustellen"
    )

    if uploaded_file is not None:
        try:
            import_data = json.loads(uploaded_file.getvalue().decode('utf-8'))

            if st.button("🔄 Daten importieren", type="primary"):
                # Import Runs
                if "runs" in import_data:
                    for run in import_data["runs"]:
                        try:
                            execute(
                                "INSERT OR REPLACE INTO runs(id, name, created, end_bsc, end_profit, place, current_period) VALUES(?, ?, ?, ?, ?, ?, ?)",
                                (run["id"], run["name"], run["created"], run.get("end_bsc", 0), run.get("end_profit", 0), run.get("place", 0), run.get("current_period", 1))
                            )
                        except Exception as e:
                            st.warning(f"Run {run.get('name', 'Unknown')} konnte nicht importiert werden: {str(e)}")

                # Import Periods
                if "periods" in import_data:
                    for period in import_data["periods"]:
                        try:
                            execute(
                                """INSERT OR REPLACE INTO periods(
                                    id, run_id, period, price1, price2, qty1, qty2, ads, devs, sales,
                                    process, profit, bsc, marketshare, innovation, awareness
                                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (
                                    period["id"], period["run_id"], period["period"],
                                    period.get("price1"), period.get("price2"), period.get("qty1"), period.get("qty2"),
                                    period.get("ads"), period.get("devs"), period.get("sales"),
                                    period.get("process"), period.get("profit"), period.get("bsc"),
                                    period.get("marketshare"), period.get("innovation"), period.get("awareness")
                                )
                            )
                        except Exception as e:
                            st.warning(f"Periode {period.get('period', 'Unknown')} konnte nicht importiert werden: {str(e)}")

                st.success("✅ Daten erfolgreich importiert!")
                st.rerun()

        except Exception as e:
            st.error(f"❌ Fehler beim Import: {str(e)}")

    st.markdown("---")
    st.subheader("👥 Teams")

    # Aktuelle Teams laden
    teams_df = query_df("SELECT * FROM teams ORDER BY created DESC")

    # Team-Status
    if st.session_state.private_mode:
        st.info("🔒 **Privater Modus** - nur deine Daten")
    elif st.session_state.team_code:
        team_name = "Unbekanntes Team"
        if not teams_df.empty:
            team_match = teams_df[teams_df['team_code'] == st.session_state.team_code]
            if not team_match.empty:
                team_name = team_match.iloc[0]['team_name']
        st.success(f"👥 **Team:** {team_name}")

    # Team-Funktionen
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔒 Privat", use_container_width=True):
            st.session_state.team_code = None
            st.session_state.private_mode = True
            st.success("🔒 Privatmodus!")
            st.rerun()

    with col2:
        team_name_input = st.text_input("Team-Name", key="team_name_minimal")
        if st.button("➕ Team erstellen", use_container_width=True, disabled=not team_name_input.strip()):
            if team_name_input.strip():
                # Automatische Team-Code Generierung
                team_code = f"TEAM-{secrets.token_hex(3).upper()}"
                existing_team = query_df("SELECT id FROM teams WHERE team_code = ?", (team_code,))
                if not existing_team.empty:
                    team_code = f"TEAM-{secrets.token_hex(4).upper()}"

                execute("INSERT INTO teams(team_code, team_name, created_by_device) VALUES(?, ?, ?)",
                       (team_code, team_name_input.strip(), st.session_state.device_id))

                st.session_state.team_code = team_code
                st.session_state.private_mode = False
                st.success(f"✅ Team '{team_name_input.strip()}' erstellt!")
                st.success(f"🔒 **Geheimer Team-Code:** {team_code}")
                st.info("📤 Teile diesen Code nur mit vertrauten Teammitgliedern!")
                st.rerun()

    with col3:
        team_code_input = st.text_input("Team-Code eingeben", placeholder="z.B. TEAM-ABC123 oder ABC123", key="team_code_minimal")
        if st.button("🔗 Beitreten", use_container_width=True, disabled=not team_code_input.strip()):
            if team_code_input.strip():
                input_code = team_code_input.strip().upper()

                # Automatisch "TEAM-" Prefix hinzufügen wenn nicht vorhanden
                if not input_code.startswith("TEAM-"):
                    team_code = f"TEAM-{input_code}"
                else:
                    team_code = input_code

                team_data = query_df("SELECT * FROM teams WHERE team_code = ?", (team_code,))
                if team_data.empty:
                    st.error(f"❌ Team-Code '{team_code}' nicht gefunden!")
                    st.info("💡 **Mögliche Ursachen:**")
                    st.info("• Team-Code ist falsch geschrieben")
                    st.info("• Team wurde bereits gelöscht")
                    st.info("• Team wurde von jemand anderem erstellt")
                    st.info(f"**Du hast eingegeben:** {input_code}")
                    st.info(f"**Gesucht wird:** {team_code}")
                else:
                    team_name = team_data.iloc[0]['team_name']
                    st.session_state.team_code = team_code
                    st.session_state.private_mode = False
                    st.success(f"✅ Team '{team_name}' beigetreten!")
                    st.success(f"📋 Code: {team_code}")
                    st.rerun()

    with col4:
        if st.button("🔄 Aktualisieren", use_container_width=True):
            st.success("🔄 Ansicht aktualisiert!")
            st.rerun()

    # Team-Verwaltung (versteckt für Datenschutz)
    if not teams_df.empty:
        st.markdown("**Team-Verwaltung:**")
        current_team_count = len(teams_df)
        st.info(f"Du hast {current_team_count} Team(s) erstellt")

        # Debug: Zeige vorhandene Teams
        with st.expander("📋 Vorhandene Teams (Debug)"):
            for _, team in teams_df.iterrows():
                st.write(f"**{team['team_name']}** - Code: `{team['team_code']}`")

        # Team-Code Eingabe für Löschung
        delete_team_code = st.text_input("Team-Code zum Löschen", key="delete_team_code", placeholder="TEAM-ABC123 oder ABC123")
        if st.button("🗑️ Team löschen", use_container_width=True, disabled=not delete_team_code.strip()):
            if delete_team_code.strip():
                input_code = delete_team_code.strip().upper()

                # Automatisch "TEAM-" Prefix hinzufügen wenn nicht vorhanden
                if not input_code.startswith("TEAM-"):
                    team_code = f"TEAM-{input_code}"
                else:
                    team_code = input_code

                team_data = query_df("SELECT * FROM teams WHERE team_code = ?", (team_code,))
                if team_data.empty:
                    st.error(f"❌ Team-Code '{team_code}' nicht gefunden!")
                    st.info("💡 **Mögliche Ursachen:**")
                    st.info("• Team-Code ist falsch geschrieben")
                    st.info("• Team wurde bereits gelöscht")
                    st.info("• Team wurde von jemand anderem erstellt")
                    st.info(f"**Du hast eingegeben:** {input_code}")
                    st.info(f"**Gesucht wird:** {team_code}")
                else:
                    team_name = team_data.iloc[0]['team_name']
                    # Bestätigung
                    confirm_key = f"confirm_delete_{team_code}"
                    if confirm_key not in st.session_state:
                        st.session_state[confirm_key] = False

                    if not st.session_state[confirm_key]:
                        st.warning(f"Team '{team_name}' ({team_code}) wirklich löschen?")
                        if st.button("✅ Ja, löschen", key=f"confirm_yes_{team_code}"):
                            st.session_state[confirm_key] = True
                            st.rerun()
                    else:
                        # Lösche Team
                        execute("DELETE FROM teams WHERE team_code = ?", (team_code,))
                        # Lösche alle Runs dieses Teams
                        execute("DELETE FROM runs WHERE team_code = ?", (team_code,))
                        st.success(f"✅ Team '{team_name}' gelöscht!")
                        st.rerun()

    st.markdown("---")
    st.subheader("🔒 Geräte-Information")

    st.info(f"**Deine Geräte-ID:** {st.session_state.device_id}")
    st.caption("Jedes Gerät hat automatisch eine eigene, eindeutige ID für separate Datenspeicherung.")

    st.markdown("---")
    st.subheader("🗂️ Datenbank-Info")

    col1, col2, col3 = st.columns(3)
    with col1:
        total_runs = len(runs_df)
        st.metric("Gesamt Runs", total_runs)

    with col2:
        total_periods = len(query_df("SELECT * FROM periods"))
        st.metric("Gesamt Perioden", total_periods)

    with col3:
        db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
        st.metric("DB-Größe", f"{db_size / 1024:.1f} KB")

    st.markdown("</div>", unsafe_allow_html=True)

# TAB 7: RUN MANAGEMENT
with tab7:
    st.subheader("🗑️ RUN MANAGEMENT")
    st.caption("Runs löschen und verwalten")

    if runs_df.empty:
        st.info("Keine Runs zum Verwalten vorhanden.")
    else:
        st.markdown('<div class="settings-panel">', unsafe_allow_html=True)

        # Run Übersicht
        st.subheader("📋 Run Übersicht")

        # Erweitere runs_df um Perioden-Info
        runs_with_periods = runs_df.copy()
        runs_with_periods["perioden"] = runs_with_periods["id"].apply(
            lambda run_id: len(query_df("SELECT * FROM periods WHERE run_id = ?", (run_id,)))
        )

        display_df = runs_with_periods[["name", "created", "perioden", "end_bsc", "end_profit", "place"]].copy()
        display_df.columns = ["Name", "Erstellt", "Perioden", "End-BSC", "End-Gewinn", "Platz"]

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("🗑️ Run löschen")

        st.warning("⚠️ **Vorsicht:** Gelöschte Runs können nicht wiederhergestellt werden!")

        run_ids = runs_df["id"].tolist()
        run_to_delete = st.selectbox(
            "Zu löschenden Run wählen",
            run_ids,
            format_func=lambda value: format_run_label(runs_df, value),
            key="delete_run"
        )

        # Bestätigung
        confirm_text = st.text_input(
            "Bestätigung eingeben",
            placeholder=f"Tippe '{runs_df.loc[runs_df['id'] == run_to_delete, 'name'].iloc[0]}' ein",
            help="Gib den Namen des Runs ein, um die Löschung zu bestätigen"
        )

        run_name = runs_df.loc[runs_df["id"] == run_to_delete, "name"].iloc[0]

        if st.button("🗑️ Run endgültig löschen", type="secondary", disabled=confirm_text != run_name):
            if confirm_text == run_name:
                # Lösche alle abhängigen Daten
                execute("DELETE FROM strategic_decisions WHERE run_id = ?", (run_to_delete,))
                execute("DELETE FROM periods WHERE run_id = ?", (run_to_delete,))
                execute("DELETE FROM runs WHERE id = ?", (run_to_delete,))

                st.success(f"✅ Run '{run_name}' wurde gelöscht!")
                st.rerun()
            else:
                st.error("❌ Bestätigung fehlerhaft!")

        st.markdown("---")
        st.subheader("🧹 Datenbank bereinigen")

        if st.button("🧽 Leere Einträge entfernen", type="secondary"):
            # Entferne Runs ohne Perioden
            empty_runs = query_df("SELECT id FROM runs WHERE id NOT IN (SELECT DISTINCT run_id FROM periods)")
            if not empty_runs.empty:
                for run_id in empty_runs["id"]:
                    execute("DELETE FROM runs WHERE id = ?", (run_id,))
                st.success(f"✅ {len(empty_runs)} leere Runs entfernt!")
            else:
                st.info("Keine leeren Runs gefunden.")

        st.markdown("</div>", unsafe_allow_html=True)


