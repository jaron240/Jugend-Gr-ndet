import json
import sqlite3
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
                current_period INTEGER DEFAULT 1
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

st.set_page_config(
    page_title="Jugend Gruender - Live Tool",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 100%);
        color: #e2e8f0;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1400px;
    }
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1.5rem;
        text-align: center;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }
    .quick-input {
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid #475569;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        backdrop-filter: blur(10px);
    }
    .decision-card {
        background: rgba(30, 41, 59, 0.9);
        border: 2px solid #475569;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .conservative { border-left: 5px solid #10b981; box-shadow: 0 0 20px rgba(16, 185, 129, 0.2); }
    .balanced { border-left: 5px solid #f59e0b; box-shadow: 0 0 20px rgba(245, 158, 11, 0.2); }
    .aggressive { border-left: 5px solid #ef4444; box-shadow: 0 0 20px rgba(239, 68, 68, 0.2); }
    .warning-card {
        background: rgba(245, 101, 101, 0.1);
        border: 1px solid #f87171;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .success-card {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid #10b981;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .metric-box {
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid #475569;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        backdrop-filter: blur(10px);
    }
    .input-field {
        background: rgba(51, 65, 85, 0.8);
        border: 1px solid #64748b;
        border-radius: 8px;
        color: #e2e8f0;
        padding: 0.5rem;
    }
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
    }
    .stSelectbox, .stNumberInput, .stSlider {
        background: rgba(30, 41, 59, 0.8);
        border-radius: 8px;
        border: 1px solid #475569;
    }
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(30, 41, 59, 0.8);
        border-radius: 8px;
        padding: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        color: #e2e8f0;
        border-radius: 6px;
        margin: 0 0.25rem;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

runs_df = query_df("SELECT * FROM runs ORDER BY id DESC")

# HEADER MIT BACKUP
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(
        """
        <div class="main-header">
            <h1>🎯 JUGEND GRÜNDER</h1>
            <p>Live-Entscheidungshilfe für Jugend Gründet Teams</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.download_button(
        "💾 Backup",
        data=build_backup_json(),
        file_name="jugend_gruender_backup.json",
        mime="application/json",
        use_container_width=True,
    )

# EINZELNE TABS STATT SIDEBAR
tab1, tab2, tab3, tab4 = st.tabs(["🏠 Live Center", "⚡ Quick Input", "🎯 Entscheidungen", "📊 Analyse"])

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

        # BSC vs Gewinn Scatterplot
        scatter = px.scatter(
            runs_df,
            x="end_profit",
            y="end_bsc",
            text="name",
            title="BSC vs. Gewinn Übersicht",
            color="end_bsc",
            color_continuous_scale="RdYlGn",
        )
        scatter.update_traces(textposition="top center")
        st.plotly_chart(scatter, use_container_width=True)

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
        execute("INSERT INTO runs(name, end_bsc, end_profit, place) VALUES(?, ?, ?, ?)", (new_name, 0, 0, 0))
        st.success(f"Run '{new_name}' erstellt!")
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

    # DREI OPTIONEN - KOMPAKT
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="decision-card conservative">
            <h4>🟢 SICHER</h4>
            """,
            unsafe_allow_html=True
        )

        if current_period <= 2:
            cons_price, cons_ads, cons_devs = 569, 100000, 5
        elif current_period <= 5:
            cons_price, cons_ads, cons_devs = 559, 150000, 6
        else:
            cons_price, cons_ads, cons_devs = 579, 200000, 7

        st.write(f"Preis: {cons_price}€")
        st.write(f"Werbung: {cons_ads:,}€")
        st.write(f"Entwickler: {cons_devs}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown(
            """
            <div class="decision-card balanced">
            <h4>🟡 BALANCIERT</h4>
            """,
            unsafe_allow_html=True
        )

        if current_period <= 2:
            bal_price, bal_ads, bal_devs = 559, 120000, 5
        elif current_period <= 5:
            bal_price, bal_ads, bal_devs = 549, 170000, 6
        else:
            bal_price, bal_ads, bal_devs = 569, 220000, 7

        st.write(f"Preis: {bal_price}€")
        st.write(f"Werbung: {bal_ads:,}€")
        st.write(f"Entwickler: {bal_devs}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown(
            """
            <div class="decision-card aggressive">
            <h4>🔴 AGGRESSIV</h4>
            """,
            unsafe_allow_html=True
        )

        if current_period <= 2:
            agg_price, agg_ads, agg_devs = 549, 140000, 6
        elif current_period <= 5:
            agg_price, agg_ads, agg_devs = 539, 190000, 7
        else:
            agg_price, agg_ads, agg_devs = 559, 240000, 8

        st.write(f"Preis: {agg_price}€")
        st.write(f"Werbung: {agg_ads:,}€")
        st.write(f"Entwickler: {agg_devs}")
        st.markdown("</div>", unsafe_allow_html=True)

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

            # Charts
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                profit_chart = px.line(
                    periods_df, x="period", y="profit", markers=True,
                    title="Gewinn-Verlauf", color_discrete_sequence=["#10b981"]
                )
                st.plotly_chart(profit_chart, use_container_width=True)

            with chart_col2:
                bsc_chart = px.line(
                    periods_df, x="period", y="bsc", markers=True,
                    title="BSC-Verlauf", color_discrete_sequence=["#f59e0b"]
                )
                st.plotly_chart(bsc_chart, use_container_width=True)

            # Daten-Tabelle
            st.dataframe(periods_df, use_container_width=True, hide_index=True)


