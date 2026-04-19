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
                place INTEGER DEFAULT 0
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
    page_title="Jugend Gruender Ultra",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top right, rgba(76, 201, 240, 0.12), transparent 26%),
            radial-gradient(circle at top left, rgba(128, 237, 153, 0.12), transparent 22%),
            linear-gradient(180deg, #07101a 0%, #0d1724 100%);
        color: #eef4ff;
    }
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }
    div[data-testid="metric-container"] {
        background: linear-gradient(180deg, rgba(17, 28, 43, 0.95), rgba(23, 40, 60, 0.95));
        border: 1px solid #29415f;
        border-radius: 18px;
        padding: 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #29415f;
        border-radius: 16px;
        overflow: hidden;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0c1522 0%, #0d1724 100%);
        border-right: 1px solid #29415f;
    }
    .hero {
        padding: 1.2rem 1.4rem;
        border: 1px solid #29415f;
        border-radius: 22px;
        background: linear-gradient(135deg, rgba(76, 201, 240, 0.12), rgba(128, 237, 153, 0.08));
        margin-bottom: 1rem;
    }
    .hero h1 {
        margin: 0;
        font-size: 2.1rem;
    }
    .hero p {
        margin: 0.35rem 0 0;
        color: #a6b6cc;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

runs_df = query_df("SELECT * FROM runs ORDER BY id DESC")

with st.sidebar:
    st.title("Jugend Gruender Ultra")
    st.caption("Paste-ready, GitHub-ready, Streamlit-ready.")
    menu = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Neuer Run",
            "Periode erfassen",
            "Run Analyse",
            "KI Optimierer",
            "Autopilot",
            "Konkurrenz Radar",
            "Strategie Guide",
        ],
    )
    st.download_button(
        "Backup als JSON herunterladen",
        data=build_backup_json(),
        file_name="jugend_gruender_backup.json",
        mime="application/json",
        use_container_width=True,
    )
    st.info(
        "Wichtig fuer Streamlit Cloud: Die lokale SQLite-Datei ist dort nicht dauerhaft. "
        "Lade deshalb regelmaessig dein Backup herunter."
    )

st.markdown(
    """
    <div class="hero">
        <h1>Jugend Gruender ULTRA Command Center</h1>
        <p>Dark dashboard for runs, period tracking, analysis, optimization and quick deployment.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if menu == "Dashboard":
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Runs", len(runs_df))
    c2.metric("Beste BSC", "0" if runs_df.empty else f"{runs_df['end_bsc'].max():.1f}")
    c3.metric(
        "Bester Gewinn",
        "0 EUR" if runs_df.empty else format_currency(float(runs_df["end_profit"].max())),
    )
    c4.metric(
        "Avg End-BSC",
        "0" if runs_df.empty else f"{runs_df['end_bsc'].mean():.1f}",
    )

    if runs_df.empty:
        st.info("Noch keine Daten vorhanden. Starte mit 'Neuer Run' und erfasse danach deine Perioden.")
    else:
        top_run = runs_df.sort_values(
            ["end_bsc", "end_profit"], ascending=[False, False]
        ).iloc[0]
        st.success(
            f"Top Run aktuell: {top_run['name']} mit {top_run['end_bsc']:.1f} BSC "
            f"und {format_currency(float(top_run['end_profit']))} Gewinn."
        )

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            scatter = px.scatter(
                runs_df,
                x="end_profit",
                y="end_bsc",
                text="name",
                title="Run Vergleich: Gewinn vs. BSC",
                color="end_bsc",
                color_continuous_scale="Tealgrn",
            )
            scatter.update_traces(textposition="top center")
            st.plotly_chart(scatter, use_container_width=True)

        with chart_col2:
            leaderboard = runs_df.sort_values("end_profit", ascending=False).head(10)
            bar = px.bar(
                leaderboard,
                x="name",
                y="end_profit",
                title="Top Gewinne",
                color="end_profit",
                color_continuous_scale="Blues",
            )
            st.plotly_chart(bar, use_container_width=True)

        display_runs = runs_df.rename(
            columns={
                "id": "ID",
                "name": "Name",
                "created": "Erstellt",
                "end_bsc": "End-BSC",
                "end_profit": "End-Gewinn",
                "place": "Platz",
            }
        )
        st.dataframe(display_runs, use_container_width=True, hide_index=True)

elif menu == "Neuer Run":
    st.subheader("Neuen Run anlegen")
    with st.form("new_run_form", clear_on_submit=True):
        name = st.text_input("Run Name", value="Run 1")
        place = st.number_input("Abschlussplatz (optional)", min_value=0, max_value=99, value=0)
        submitted = st.form_submit_button("Run speichern", use_container_width=True)

    if submitted:
        clean_name = name.strip()
        if not clean_name:
            st.error("Bitte gib einen Run-Namen ein.")
        else:
            execute(
                "INSERT INTO runs(name, end_bsc, end_profit, place) VALUES(?, ?, ?, ?)",
                (clean_name, 0, 0, int(place)),
            )
            st.success(f"{clean_name} wurde angelegt.")
            st.rerun()

    if not runs_df.empty:
        st.caption("Vorhandene Runs")
        st.dataframe(
            runs_df[["id", "name", "created", "end_bsc", "end_profit", "place"]],
            use_container_width=True,
            hide_index=True,
        )

elif menu == "Periode erfassen":
    st.subheader("Periode speichern oder aktualisieren")
    if runs_df.empty:
        st.warning("Lege zuerst einen Run an.")
    else:
        run_ids = runs_df["id"].tolist()
        select_col1, select_col2 = st.columns([2, 1])
        run_id = select_col1.selectbox(
            "Run waehlen",
            run_ids,
            format_func=lambda value: format_run_label(runs_df, value),
        )

        max_period_df = query_df(
            "SELECT MAX(period) AS max_period FROM periods WHERE run_id = ?",
            (run_id,),
        )
        max_period = max_period_df.iloc[0]["max_period"]
        next_period = 1 if pd.isna(max_period) else min(8, int(max_period) + 1)
        period = select_col2.number_input(
            "Periode",
            min_value=1,
            max_value=8,
            value=next_period,
            step=1,
        )

        existing_period = query_df(
            "SELECT * FROM periods WHERE run_id = ? AND period = ? ORDER BY id LIMIT 1",
            (run_id, int(period)),
        )
        defaults = existing_period.iloc[0].to_dict() if not existing_period.empty else {}

        with st.form("period_form"):
            col1, col2, col3 = st.columns(3)
            price1 = col1.number_input(
                "Preis Markt 1",
                min_value=0.0,
                max_value=2000.0,
                value=float(defaults.get("price1") or 579.0),
            )
            price2 = col1.number_input(
                "Preis Markt 2",
                min_value=0.0,
                max_value=2000.0,
                value=float(defaults.get("price2") or 559.0),
            )
            qty1 = col2.number_input(
                "Menge Markt 1",
                min_value=0,
                max_value=50000,
                value=int(defaults.get("qty1") or 4000),
            )
            qty2 = col2.number_input(
                "Menge Markt 2",
                min_value=0,
                max_value=50000,
                value=int(defaults.get("qty2") or 500),
            )
            ads = col2.number_input(
                "Werbung",
                min_value=0,
                max_value=1000000,
                value=int(defaults.get("ads") or 100000),
            )
            devs = col3.number_input(
                "Entwickler",
                min_value=0,
                max_value=100,
                value=int(defaults.get("devs") or 5),
            )
            sales = col3.number_input(
                "Vertrieb",
                min_value=0,
                max_value=100,
                value=int(defaults.get("sales") or 5),
            )
            process = col3.number_input(
                "Prozessbudget",
                min_value=0,
                max_value=1000000,
                value=int(defaults.get("process") or 80000),
            )

            perf1, perf2, perf3, perf4 = st.columns(4)
            profit = perf1.number_input(
                "Gewinn",
                min_value=-10000000.0,
                max_value=10000000.0,
                value=float(defaults.get("profit") or 0.0),
            )
            bsc = perf2.number_input(
                "BSC",
                min_value=0.0,
                max_value=5000.0,
                value=float(defaults.get("bsc") or 0.0),
            )
            marketshare = perf3.number_input(
                "Marktanteil %",
                min_value=0.0,
                max_value=100.0,
                value=float(defaults.get("marketshare") or 20.0),
            )
            awareness = perf4.number_input(
                "Bekanntheit",
                min_value=0.0,
                max_value=1000.0,
                value=float(defaults.get("awareness") or 80.0),
            )
            innovation = st.number_input(
                "Innovation",
                min_value=0.0,
                max_value=1000.0,
                value=float(defaults.get("innovation") or 150.0),
            )

            submit_period = st.form_submit_button(
                "Periode aktualisieren" if defaults else "Periode speichern",
                use_container_width=True,
            )

        if submit_period:
            action = save_period(
                run_id=run_id,
                period=int(period),
                price1=price1,
                price2=price2,
                qty1=int(qty1),
                qty2=int(qty2),
                ads=int(ads),
                devs=int(devs),
                sales=int(sales),
                process=int(process),
                profit=profit,
                bsc=bsc,
                marketshare=marketshare,
                innovation=innovation,
                awareness=awareness,
            )
            st.success(
                f"Periode {int(period)} fuer {format_run_label(runs_df, run_id)} wurde {action}."
            )
            st.rerun()

elif menu == "Run Analyse":
    st.subheader("Run Analyse")
    if runs_df.empty:
        st.warning("Noch keine Runs vorhanden.")
    else:
        run_ids = runs_df["id"].tolist()
        run_id = st.selectbox(
            "Run waehlen",
            run_ids,
            format_func=lambda value: format_run_label(runs_df, value),
        )
        periods_df = query_df(
            "SELECT * FROM periods WHERE run_id = ? ORDER BY period, id",
            (run_id,),
        )

        if periods_df.empty:
            st.info("Fuer diesen Run wurden noch keine Perioden erfasst.")
        else:
            latest = periods_df.sort_values("period").iloc[-1]
            best_profit_row = periods_df.loc[periods_df["profit"].idxmax()]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Letzte BSC", f"{latest['bsc']:.1f}")
            c2.metric("Max Gewinn", format_currency(float(periods_df["profit"].max())))
            c3.metric("Avg Marktanteil", f"{periods_df['marketshare'].mean():.1f}%")
            c4.metric("Beste Gewinn-Periode", f"P{int(best_profit_row['period'])}")

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                profit_chart = px.line(
                    periods_df,
                    x="period",
                    y="profit",
                    markers=True,
                    title="Gewinn-Verlauf",
                )
                st.plotly_chart(profit_chart, use_container_width=True)

            with chart_col2:
                bsc_chart = px.line(
                    periods_df,
                    x="period",
                    y="bsc",
                    markers=True,
                    title="BSC-Verlauf",
                )
                st.plotly_chart(bsc_chart, use_container_width=True)

            combo = px.line(
                periods_df,
                x="period",
                y=["innovation", "awareness", "marketshare"],
                markers=True,
                title="Innovation, Bekanntheit und Marktanteil",
            )
            st.plotly_chart(combo, use_container_width=True)

            st.download_button(
                "Run als CSV herunterladen",
                data=periods_df.to_csv(index=False).encode("utf-8"),
                file_name=f"run_{run_id}_perioden.csv",
                mime="text/csv",
            )
            st.dataframe(periods_df, use_container_width=True, hide_index=True)

elif menu == "KI Optimierer":
    st.subheader("KI Optimierer")
    st.caption("Schnelle datenbasierte Empfehlung fuer Preis, Menge und Risiko.")

    col1, col2 = st.columns(2)
    market = col1.slider("Marktwachstum %", -15, 20, 5)
    current_price = col1.slider("Aktueller Preis", 450, 700, 559)
    awareness = col2.slider("Bekanntheit", 50, 200, 110)
    innovation = col2.slider("Innovation", 100, 400, 230)

    price_adjustment = (12 if innovation > 220 else -10) + (6 if awareness > 110 else -6)
    optimal_price = current_price + price_adjustment
    demand_score = (
        100
        + market * 3
        + (awareness - 100) * 0.45
        + (innovation - 200) * 0.35
        - max(0, optimal_price - current_price) * 0.55
    )
    order = max(1000, int(demand_score * 44))
    win_prob = max(
        5,
        min(
            95,
            int(
                48
                + market * 2
                + (innovation - 220) * 0.16
                + (awareness - 110) * 0.18
            ),
        ),
    )
    risk = "Niedrig" if market >= 2 else "Mittel" if market > -5 else "Hoch"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Empfohlener Preis", format_currency(float(optimal_price)))
    c2.metric("Empfohlene Bestellmenge", f"{order:,}")
    c3.metric("Risiko", risk)
    c4.metric("Siegchance", f"{win_prob}%")

    recommendations = []
    if awareness < 115:
        recommendations.append("Werbung leicht erhoehen, um Bekanntheit zu stabilisieren.")
    if innovation < 220:
        recommendations.append("Innovation ausbauen, damit hoehere Preise glaubwuerdiger werden.")
    if market < 0:
        recommendations.append("Bestellmenge konservativ halten und Marge absichern.")
    if not recommendations:
        recommendations.append("Deine Parameter sind solide. Fokus auf saubere Ausfuehrung.")

    st.markdown("**Empfehlung**")
    for item in recommendations:
        st.write(f"- {item}")

elif menu == "Autopilot":
    st.subheader("Autopilot")
    st.caption("Schnellentscheidung nach Spielphase und Marktlage.")

    market = st.number_input("Marktwachstum %", value=5)
    phase = st.selectbox("Spielphase", ["Frueh (1-2)", "Mitte (3-5)", "Endgame (6-8)"])

    base_price = 559 if phase != "Endgame (6-8)" else 579
    ads = 120000 if phase == "Frueh (1-2)" else 165000 if phase == "Mitte (3-5)" else 220000
    devs = 5 if phase == "Frueh (1-2)" else 6 if phase == "Mitte (3-5)" else 7
    sales = 5 if phase == "Frueh (1-2)" else 6 if phase == "Mitte (3-5)" else 7
    qty = max(2500, int((4000 + market * 120) * (1.15 if phase == "Endgame (6-8)" else 1.0)))

    if market > 8:
        ads += 25000
        sales += 1
        qty = int(qty * 1.08)
    elif market < 0:
        base_price -= 15
        qty = int(qty * 0.92)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Preis", format_currency(float(base_price)))
    c2.metric("Werbung", format_currency(float(ads)))
    c3.metric("Entwickler", devs)
    c4.metric("Vertrieb", sales)
    c5.metric("Bestellmenge", f"{qty:,}")

    st.success(
        "Autopilot-Regel: Fruehe Phase = Effizienz, Mitte = Marktanteil, Ende = BSC und saubere Performance."
    )

elif menu == "Konkurrenz Radar":
    st.subheader("Konkurrenz Radar")
    st.caption("Einfacher Bedrohungscheck auf Basis bekannter Konkurrenzwerte.")

    col1, col2, col3 = st.columns(3)
    cprice = col1.slider("Konkurrenz Preis", 450, 700, 559)
    cads = col2.slider("Konkurrenz Werbung", 0, 500000, 150000)
    cinnovation = col3.slider("Konkurrenz Innovation", 50, 400, 180)

    if cprice < 540 and cads > 250000:
        status = "Aggressiver Marktanteils-Angriff"
        status_type = st.error
    elif cprice > 590 and cinnovation > 220:
        status = "Premiumstrategie mit starkem Qualitaetsfokus"
        status_type = st.info
    else:
        status = "Ausgewogene Konkurrenzstrategie"
        status_type = st.success

    threat = min(100, int((700 - cprice) * 0.18 + cads / 7000 + cinnovation * 0.08))
    reaction = (
        "Reagiere mit Werbung und Vertrieb."
        if threat >= 70
        else "Halte Preisdisziplin und beobachte die naechste Periode."
    )

    status_type(status)
    r1, r2 = st.columns(2)
    r1.metric("Bedrohungslevel", f"{threat}%")
    r2.metric("Empfohlene Reaktion", "Offensiv" if threat >= 70 else "Kontrolliert")
    st.write(reaction)

elif menu == "Strategie Guide":
    st.subheader("Strategie Guide")
    st.markdown(
        """
        **Fruehe Phasen**
        - Fokus auf Effizienz, saubere Prozesse und Vertrauen.

        **Mittlere Phasen**
        - Marktanteil, Bekanntheit und Innovation aktiv ausbauen.

        **Endgame**
        - BSC maximieren, Fehler vermeiden, Daten sauber aussteuern.

        **Boommarkt**
        - Werbung und Vertrieb mutiger hochfahren.

        **Schwacher Markt**
        - Preise moderat anpassen und Bestellmengen diszipliniert halten.
        """
    )
    st.info(
        "Deploy-Tipp: Fuer Streamlit Community Cloud einfach dieses Repo hochladen und als Startdatei 'app.py' auswaehlen."
    )
