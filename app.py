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
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #f8f9fa;
        color: #212529;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1200px;
    }
    .live-center {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    .decision-card {
        background: white;
        border: 2px solid #e9ecef;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .conservative { border-left: 5px solid #28a745; }
    .balanced { border-left: 5px solid #ffc107; }
    .aggressive { border-left: 5px solid #dc3545; }
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .metric-large {
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
    }
    .input-large {
        font-size: 1.2rem;
        padding: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

runs_df = query_df("SELECT * FROM runs ORDER BY id DESC")

with st.sidebar:
    st.title("Jugend Gruender")
    st.caption("Entscheidungshilfe für Jugend Gründet Teams")
    menu = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Neuer Run",
            "Periode auswählen",
            "Periode eintragen",
            "Strategieentscheidungen",
            "Frühwarnsystem",
            "Szenario Tester",
            "Analyse",
            "Empfehlungen",
            "Run Vergleich",
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

# LIVE RUN CENTER - Haupteingang für Live-Spiele
st.markdown(
    """
    <div class="live-center">
        <h1 style="margin: 0; font-size: 2.5rem;">🎯 LIVE RUN CENTER</h1>
        <p style="margin: 0.5rem 0; font-size: 1.2rem;">Schnelle Dateneingabe für Jugend Gründet - 30 Sekunden pro Periode</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Live Run Center - immer sichtbar oben
if not runs_df.empty:
    st.subheader("📊 Aktuelle Runs")

    # Schnellübersicht
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        # Handle missing current_period column for existing runs
        if "current_period" in runs_df.columns:
            active_runs = len(runs_df[runs_df["current_period"] <= 8])
        else:
            active_runs = len(runs_df)  # All runs are active if no period tracking
        st.metric("Aktive Runs", active_runs)

    with col2:
        if not runs_df.empty:
            best_bsc = runs_df["end_bsc"].max()
            st.metric("Bester BSC", f"{best_bsc:.1f}")

    with col3:
        # Handle missing current_period column for existing runs
        if "current_period" in runs_df.columns:
            completed_runs = len(runs_df[runs_df["current_period"] > 8])
        else:
            completed_runs = 0  # No completed runs if no period tracking
        st.metric("Abgeschlossene Runs", completed_runs)

    with col4:
        avg_bsc = runs_df["end_bsc"].mean() if not runs_df.empty else 0
        st.metric("Ø BSC", f"{avg_bsc:.1f}")

# Navigation für erweiterte Funktionen
st.markdown("---")
st.subheader("🔧 Erweiterte Funktionen")

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

elif menu == "Periode auswählen":
    st.subheader("Periode für Run auswählen")
    if runs_df.empty:
        st.warning("Lege zuerst einen Run an.")
    else:
        run_ids = runs_df["id"].tolist()
        run_id = st.selectbox(
            "Run wählen",
            run_ids,
            format_func=lambda value: format_run_label(runs_df, value),
        )

        # Aktuelle Periode des Runs
        # Handle missing current_period column for existing runs
        if "current_period" in runs_df.columns:
            current_period = runs_df.loc[runs_df["id"] == run_id, "current_period"].iloc[0]
        else:
            current_period = 1  # Default for existing runs without period tracking
        st.info(f"Aktuelle Periode des Runs: {current_period}")

        # Nächste verfügbare Periode
        max_period_df = query_df(
            "SELECT MAX(period) AS max_period FROM periods WHERE run_id = ?",
            (run_id,),
        )
        max_completed = max_period_df.iloc[0]["max_period"]
        next_available = 1 if pd.isna(max_completed) else int(max_completed) + 1

        if next_available > 8:
            st.success("Alle Perioden abgeschlossen!")
        else:
            st.markdown(f"### Nächste Periode: {next_available}")

            # Perioden-Info anzeigen
            period_info = {
                1: "Finanzierung - Vertrauen aufbauen",
                2: "Standort - Basis legen",
                3: "Rechtsform - Wachstum starten",
                4: "Büroanwendungen - Effizienz steigern",
                5: "Markt 2 + Schlüsselperson - Expansion",
                6: "Reparaturrecht + Patent - Reputation",
                7: "Doktorand:in + Compliance - Personal",
                8: "CSR + Wetterinfo - Finale"
            }

            st.info(f"**Periode {next_available}:** {period_info.get(next_available, 'Unbekannt')}")

            if st.button(f"Periode {next_available} starten", type="primary"):
                execute("UPDATE runs SET current_period = ? WHERE id = ?", (next_available, run_id))
                st.success(f"Periode {next_available} für {format_run_label(runs_df, run_id)} gestartet!")
                st.rerun()

elif menu == "Frühwarnsystem":
    st.subheader("🚨 FRÜHWARNSYSTEM")
    st.caption("Risiken erkennen und vermeiden - bevor es zu spät ist")

    if runs_df.empty:
        st.warning("Lege zuerst einen Run an.")
    else:
        run_ids = runs_df["id"].tolist()
        run_id = st.selectbox(
            "Run wählen",
            run_ids,
            format_func=lambda value: format_run_label(runs_df, value),
        )

        # Aktuelle Periode und Daten laden
        # Handle missing current_period column for existing runs
        if "current_period" in runs_df.columns:
            current_period = runs_df.loc[runs_df["id"] == run_id, "current_period"].iloc[0]
        else:
            current_period = 1  # Default for existing runs without period tracking

        periods_df = query_df(
            "SELECT * FROM periods WHERE run_id = ? ORDER BY period DESC LIMIT 1",
            (run_id,),
        )

        if periods_df.empty:
            st.info("Noch keine Periodendaten vorhanden. Trage zuerst eine Periode ein.")
        else:
            latest = periods_df.iloc[0]

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

elif menu == "Szenario Tester":
    st.subheader("🔮 SZENARIO TESTER")
    st.caption("Was wäre wenn? - Auswirkungen deiner Entscheidungen simulieren")

    if runs_df.empty:
        st.warning("Lege zuerst einen Run an.")
    else:
        run_ids = runs_df["id"].tolist()
        run_id = st.selectbox(
            "Run wählen",
            run_ids,
            format_func=lambda value: format_run_label(runs_df, value),
        )

        periods_df = query_df(
            "SELECT * FROM periods WHERE run_id = ? ORDER BY period DESC LIMIT 1",
            (run_id,),
        )

        if periods_df.empty:
            st.info("Noch keine Periodendaten vorhanden. Trage zuerst eine Periode ein.")
        else:
            baseline = periods_df.iloc[0]

            st.markdown("### 📊 Ausgangssituation")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Basis-Preis", f"{baseline['price1']:.0f}€")
            col2.metric("Basis-Werbung", f"{baseline['ads']:,.0f}€")
            col3.metric("Basis-Entwickler", baseline['devs'])
            col4.metric("Basis-BSC", f"{baseline['bsc']:.1f}")

            st.markdown("### 🎛️ Was-If Szenarien")

            # Eingabeparameter für Szenario
            col1, col2, col3 = st.columns(3)
            with col1:
                price_change = st.slider("Preisänderung", -50, +50, 0, help="€ Änderung zum Basispreis")
                ads_change = st.slider("Werbeänderung", -50000, +50000, 0, step=5000, help="€ Änderung zur Basiswerbung")
            with col2:
                devs_change = st.slider("Entwickler-Änderung", -2, +2, 0, help="Änderung zur Basisanzahl")
                sales_change = st.slider("Vertrieb-Änderung", -2, +2, 0, help="Änderung zur Basisanzahl")
            with col3:
                qty_change_pct = st.slider("Mengenänderung", -50, +50, 0, help="% Änderung zur Basismenge")

            # Berechnung der Auswirkungen (vereinfachtes Modell)
            new_price = baseline['price1'] + price_change
            new_ads = baseline['ads'] + ads_change
            new_devs = baseline['devs'] + devs_change
            new_sales = baseline['sales'] + sales_change
            new_qty = baseline['qty1'] * (1 + qty_change_pct / 100)

            # Vereinfachte Schätzungen (basierend auf typischen Spielmechaniken)
            # Preisimpact auf Marktanteil
            price_impact = max(-20, min(20, (559 - new_price) * 0.5))  # 1€ Preisänderung = 0.5% Marktanteil

            # Werbeimpact auf Bekanntheit
            ads_impact = min(50, new_ads / 2000)  # 2000€ Werbung = 1 Punkt Bekanntheit

            # Personalimpact auf BSC
            personal_impact = (new_devs - baseline['devs']) * 15 + (new_sales - baseline['sales']) * 10

            # Mengenimpact auf Gewinn (vereinfacht)
            qty_impact = (new_qty - baseline['qty1']) / baseline['qty1'] * 30  # 10% Mengenänderung = 3% Gewinnänderung

            # Gesamteffekte
            estimated_marketshare = baseline['marketshare'] + price_impact
            estimated_awareness = min(1000, baseline['awareness'] + ads_impact)
            estimated_bsc = max(0, baseline['bsc'] + personal_impact)
            estimated_profit = baseline['profit'] * (1 + qty_impact / 100)

            st.markdown("### 🔍 Szenario-Ergebnisse")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                delta_ms = estimated_marketshare - baseline['marketshare']
                col1.metric(
                    "Marktanteil",
                    f"{estimated_marketshare:.1f}%",
                    f"{delta_ms:+.1f}%" if abs(delta_ms) > 0.1 else None,
                    delta_color="normal"
                )
            with col2:
                delta_awa = estimated_awareness - baseline['awareness']
                col2.metric(
                    "Bekanntheit",
                    f"{estimated_awareness:.1f}",
                    f"{delta_awa:+.1f}" if abs(delta_awa) > 0.1 else None,
                    delta_color="normal"
                )
            with col3:
                delta_bsc = estimated_bsc - baseline['bsc']
                col3.metric(
                    "BSC",
                    f"{estimated_bsc:.1f}",
                    f"{delta_bsc:+.1f}" if abs(delta_bsc) > 0.1 else None,
                    delta_color="normal"
                )
            with col4:
                delta_profit = estimated_profit - baseline['profit']
                col4.metric(
                    "Gewinn",
                    f"{estimated_profit:,.0f}€",
                    f"{delta_profit:+,.0f}€" if abs(delta_profit) > 1000 else None,
                    delta_color="normal"
                )

            # Interpretation
            st.markdown("### 💭 Interpretation")

            insights = []

            if abs(price_change) > 20:
                if price_change < 0:
                    insights.append("⚠️ Starke Preissenkung: Guter Marktanteil, aber Margen unter Druck")
                else:
                    insights.append("⚠️ Preiserhöhung: Höhere Margen, aber Marktanteil schrumpft")

            if ads_change > 20000:
                insights.append("📈 Hohe Werbeinvestition: Starke Bekanntheitssteigerung, aber Cashflow beachten")

            if devs_change > 0:
                insights.append("🏆 Mehr Entwickler: BSC-Boost durch Innovation, aber Personalkosten steigen")

            if abs(qty_change_pct) > 30:
                if qty_change_pct > 0:
                    insights.append("📦 Mengensteigerung: Höherer Gewinn möglich, aber Lager- und Cashflow-Risiko")
                else:
                    insights.append("📦 Mengenreduktion: Sicherer Cashflow, aber Wachstum gebremst")

            if estimated_bsc > baseline['bsc'] + 50:
                insights.append("🎯 BSC-Sprung! Diese Änderungen würden BSC stark verbessern")

            if estimated_marketshare < 15:
                insights.append("🚨 Marktanteil kritisch niedrig - aggressive Preisstrategie nötig")

            if not insights:
                insights.append("🔄 Moderate Änderungen - ausgewogene Entwicklung")

            for insight in insights:
                st.write(insight)

            st.info("**Hinweis:** Dies sind Schätzungen basierend auf typischen Spielmechaniken. Die tatsächlichen Auswirkungen können variieren.")

elif menu == "Strategieentscheidungen":
    st.subheader("Strategische Entscheidungen")
    if runs_df.empty:
        st.warning("Lege zuerst einen Run an.")
    else:
        run_ids = runs_df["id"].tolist()
        run_id = st.selectbox(
            "Run wählen",
            run_ids,
            format_func=lambda value: format_run_label(runs_df, value),
        )

        current_period = runs_df.loc[runs_df["id"] == run_id, "current_period"].iloc[0]

        if current_period == 1:
            st.info("Periode 1: Wähle deine Finanzierung")
            with st.form("financing_decision"):
                financing = st.radio(
                    "Finanzierungsoption",
                    ["Green Climate Fund (empfohlen)", "Investor", "Bankkredit"],
                    help="Green Climate Fund gibt BSC-Boost für Nachhaltigkeit"
                )
                submitted = st.form_submit_button("Finanzierung wählen")
                if submitted:
                    execute(
                        "INSERT OR REPLACE INTO strategic_decisions (run_id, period, decision_type, decision_value) VALUES (?, ?, ?, ?)",
                        (run_id, 1, "financing", financing.split(" ")[0])
                    )
                    st.success(f"Finanzierung '{financing}' gewählt!")

        elif current_period == 2:
            st.info("Periode 2: Wähle deinen Standort")
            with st.form("location_decision"):
                location = st.radio(
                    "Standort",
                    ["Passau (empfohlen)", "Dresden", "Freudenstadt"],
                    help="Passau gibt BSC-Vorteile für Nachhaltigkeit"
                )
                submitted = st.form_submit_button("Standort wählen")
                if submitted:
                    execute(
                        "INSERT OR REPLACE INTO strategic_decisions (run_id, period, decision_type, decision_value) VALUES (?, ?, ?, ?)",
                        (run_id, 2, "location", location.split(" ")[0])
                    )
                    st.success(f"Standort '{location}' gewählt!")

        elif current_period == 3:
            st.info("Periode 3: Wähle deine Rechtsform")
            with st.form("legal_form_decision"):
                legal_form = st.radio(
                    "Rechtsform",
                    ["GmbH (empfohlen)", "AG", "GbR"],
                    help="GmbH bietet beste Balance für Wachstum"
                )
                submitted = st.form_submit_button("Rechtsform wählen")
                if submitted:
                    execute(
                        "INSERT OR REPLACE INTO strategic_decisions (run_id, period, decision_type, decision_value) VALUES (?, ?, ?, ?)",
                        (run_id, 3, "legal_form", legal_form.split(" ")[0])
                    )
                    st.success(f"Rechtsform '{legal_form}' gewählt!")

        elif current_period == 4:
            st.info("Periode 4: Wähle Büroanwendungen")
            with st.form("software_decision"):
                software = st.radio(
                    "Büroanwendungen",
                    ["Cloud Computing (empfohlen)", "Open Source", "Klassische Lizenzen"],
                    help="Cloud Computing gibt Effizienz- und BSC-Vorteile"
                )
                submitted = st.form_submit_button("Büroanwendungen wählen")
                if submitted:
                    execute(
                        "INSERT OR REPLACE INTO strategic_decisions (run_id, period, decision_type, decision_value) VALUES (?, ?, ?, ?)",
                        (run_id, 4, "software", "Cloud" if "Cloud" in software else "Open" if "Open" in software else "Classic")
                    )
                    st.success(f"Büroanwendungen '{software}' gewählt!")

        elif current_period == 5:
            st.info("Periode 5: Strategische Entscheidungen")
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Schlüsselperson")
                with st.form("key_person_decision"):
                    key_person = st.radio(
                        "Schlüsselperson",
                        ["Elena Equitara", "Hugo Humanitas", "Fiona Finance"],
                        help="Hugo Humanitas gibt BSC-Boost für gesellschaftliche Bedeutung"
                    )
                    submitted1 = st.form_submit_button("Schlüsselperson wählen")
                    if submitted1:
                        execute(
                            "INSERT OR REPLACE INTO strategic_decisions (run_id, period, decision_type, decision_value) VALUES (?, ?, ?, ?)",
                            (run_id, 5, "key_person", key_person.split(" ")[1])
                        )
                        st.success(f"Schlüsselperson '{key_person}' gewählt!")

            with col2:
                st.subheader("Klimakommunikation")
                with st.form("climate_decision"):
                    climate = st.radio(
                        "Klimakommunikation",
                        ["Bewusstsein herstellen (empfohlen)", "Angst schüren", "Nicht thematisieren"],
                        help="Bewusstsein herstellen gibt BSC-Vorteile für Nachhaltigkeit"
                    )
                    submitted2 = st.form_submit_button("Klimakommunikation wählen")
                    if submitted2:
                        execute(
                            "INSERT OR REPLACE INTO strategic_decisions (run_id, period, decision_type, decision_value) VALUES (?, ?, ?, ?)",
                            (run_id, 5, "climate", "Bewusstsein" if "Bewusstsein" in climate else "Angst" if "Angst" in climate else "Nichts")
                        )
                        st.success(f"Klimakommunikation '{climate}' gewählt!")

        elif current_period == 6:
            st.info("Periode 6: Strategische Entscheidungen")
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Reparaturrecht")
                with st.form("repair_decision"):
                    repair = st.radio(
                        "Reparaturrecht",
                        ["Minimum", "Garantieverlängerung (empfohlen)", "Neue EU-Richtlinie"],
                        help="Garantieverlängerung gibt BSC-Boost für Kundenzufriedenheit"
                    )
                    submitted1 = st.form_submit_button("Reparaturrecht wählen")
                    if submitted1:
                        execute(
                            "INSERT OR REPLACE INTO strategic_decisions (run_id, period, decision_type, decision_value) VALUES (?, ?, ?, ?)",
                            (run_id, 6, "repair", "Garantie" if "Garantie" in repair else "Minimum" if "Minimum" in repair else "EU")
                        )
                        st.success(f"Reparaturrecht '{repair}' gewählt!")

            with col2:
                st.subheader("Patentmanagement")
                with st.form("patent_decision"):
                    patent = st.radio(
                        "Patentmanagement",
                        ["Nichts", "Patentanmeldung (empfohlen)", "Offenlegung"],
                        help="Patentanmeldung stärkt Innovation und BSC"
                    )
                    submitted2 = st.form_submit_button("Patentmanagement wählen")
                    if submitted2:
                        execute(
                            "INSERT OR REPLACE INTO strategic_decisions (run_id, period, decision_type, decision_value) VALUES (?, ?, ?, ?)",
                            (run_id, 6, "patent", "Patent" if "Patent" in patent else "Nichts" if "Nichts" in patent else "Offenlegung")
                        )
                        st.success(f"Patentmanagement '{patent}' gewählt!")

        elif current_period == 7:
            st.info("Periode 7: Strategische Entscheidungen")
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Doktorand:in")
                with st.form("phd_decision"):
                    phd = st.radio(
                        "Doktorand:in",
                        ["Hochschule Technik (empfohlen)", "Hochschule Gestaltung", "Hochschule Ökonomie"],
                        help="Hochschule Technik gibt BSC-Boost für Innovation"
                    )
                    submitted1 = st.form_submit_button("Doktorand:in wählen")
                    if submitted1:
                        execute(
                            "INSERT OR REPLACE INTO strategic_decisions (run_id, period, decision_type, decision_value) VALUES (?, ?, ?, ?)",
                            (run_id, 7, "phd", "Technik" if "Technik" in phd else "Gestaltung" if "Gestaltung" in phd else "Ökonomie")
                        )
                        st.success(f"Doktorand:in '{phd}' gewählt!")

            with col2:
                st.subheader("Compliance")
                with st.form("compliance_decision"):
                    compliance = st.radio(
                        "Compliance",
                        ["Freiheiten", "Richtlinien (empfohlen)", "Überwachung"],
                        help="Richtlinien geben BSC-Boost für Vertrauen"
                    )
                    submitted2 = st.form_submit_button("Compliance wählen")
                    if submitted2:
                        execute(
                            "INSERT OR REPLACE INTO strategic_decisions (run_id, period, decision_type, decision_value) VALUES (?, ?, ?, ?)",
                            (run_id, 7, "compliance", "Richtlinien" if "Richtlinien" in compliance else "Freiheiten" if "Freiheiten" in compliance else "Überwachung")
                        )
                        st.success(f"Compliance '{compliance}' gewählt!")

        elif current_period == 8:
            st.info("Periode 8: Strategische Entscheidungen")
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("CSR")
                with st.form("csr_decision"):
                    csr = st.radio(
                        "CSR",
                        ["Solidaritätsabgabe", "Vereinssponsoring", "Gesundheitsprogramm (empfohlen)"],
                        help="Gesundheitsprogramm gibt BSC-Boost für Mitarbeiterwohl"
                    )
                    submitted1 = st.form_submit_button("CSR wählen")
                    if submitted1:
                        execute(
                            "INSERT OR REPLACE INTO strategic_decisions (run_id, period, decision_type, decision_value) VALUES (?, ?, ?, ?)",
                            (run_id, 8, "csr", "Gesundheit" if "Gesundheit" in csr else "Solidaritaet" if "Solidaritaet" in csr else "Sponsoring")
                        )
                        st.success(f"CSR '{csr}' gewählt!")

            with col2:
                st.subheader("Wetterinformationen")
                with st.form("weather_decision"):
                    weather = st.radio(
                        "Wetterinformationen",
                        ["Kein Zukauf", "Rohdaten kaufen (empfohlen)", "KI-Software"],
                        help="Rohdaten kaufen stärkt Innovation und BSC"
                    )
                    submitted2 = st.form_submit_button("Wetterinformationen wählen")
                    if submitted2:
                        execute(
                            "INSERT OR REPLACE INTO strategic_decisions (run_id, period, decision_type, decision_value) VALUES (?, ?, ?, ?)",
                            (run_id, 8, "weather", "Rohdaten" if "Rohdaten" in weather else "Kein" if "Kein" in weather else "KI")
                        )
                        st.success(f"Wetterinformationen '{weather}' gewählt!")

        else:
            st.info("Alle strategischen Entscheidungen wurden getroffen!")

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

elif menu == "Periode eintragen":
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

            # Markt 2 nur ab Periode 5
            if period >= 5:
                price2 = col1.number_input(
                    "Preis Markt 2",
                    min_value=0.0,
                    max_value=2000.0,
                    value=float(defaults.get("price2") or 559.0),
                )
            else:
                price2 = 0.0  # Default für frühere Perioden

            qty1 = col2.number_input(
                "Menge Markt 1",
                min_value=0,
                max_value=50000,
                value=int(defaults.get("qty1") or 4000),
            )

            # Markt 2 nur ab Periode 5
            if period >= 5:
                qty2 = col2.number_input(
                    "Menge Markt 2",
                    min_value=0,
                    max_value=50000,
                    value=int(defaults.get("qty2") or 500),
                )
            else:
                qty2 = 0  # Default für frühere Perioden

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

elif menu == "Analyse":
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

elif menu == "Empfehlungen":
    st.subheader("🎯 ENTSCHEIDUNGSHILFE")
    st.caption("Drei strategische Optionen mit Begründung - keine Fake-Präzision")

    # Eingabeparameter
    col1, col2, col3 = st.columns(3)
    with col1:
        current_period = st.selectbox("Aktuelle Periode", list(range(1, 9)), index=0)
        market_growth = st.slider("Marktwachstum %", -15, 20, 5)
    with col2:
        competitor_price = st.number_input("Konkurrenz Preis", 450, 700, 559)
        current_marketshare = st.slider("Dein Marktanteil %", 5, 50, 20)
    with col3:
        current_awareness = st.slider("Deine Bekanntheit", 50, 200, 110)
        current_innovation = st.slider("Deine Innovation", 100, 400, 230)

    # Phase bestimmen
    if current_period <= 2:
        phase = "Frühphase"
        phase_focus = "Vertrauen aufbauen, effizient arbeiten"
    elif current_period <= 5:
        phase = "Mittelphase"
        phase_focus = "Marktanteil gewinnen, Innovation steigern"
    else:
        phase = "Endgame"
        phase_focus = "BSC maximieren, Arbeitsplätze schaffen"

    st.markdown(f"### 📊 {phase} (Periode {current_period})")
    st.info(f"**Fokus:** {phase_focus}")

    # DREI OPTIONEN mit Begründung
    st.markdown("### Drei strategische Optionen:")

    # Konservative Option
    st.markdown(
        """
        <div class="decision-card conservative">
        <h4>🟢 KONSERVATIV - Sicher spielen</h4>
        """,
        unsafe_allow_html=True
    )

    if current_period <= 2:
        cons_price = 569
        cons_ads = 100000
        cons_devs = 5
        cons_qty = 3800
        cons_reason = f"Preis {cons_price}€ liegt im sicheren Bereich. Werbung {cons_ads:,}€ für Grundpräsenz. Nicht zu aggressiv starten."
    elif current_period <= 5:
        cons_price = 559
        cons_ads = 150000
        cons_devs = 6
        cons_qty = 4200
        cons_reason = f"Preis {cons_price}€ für stabile Margen. Werbung {cons_ads:,}€ für Marktanteil. Solide Mittelphase."
    else:
        cons_price = 579
        cons_ads = 200000
        cons_devs = 7
        cons_qty = 4800
        cons_reason = f"Preis {cons_price}€ für BSC-Fokus. Werbung {cons_ads:,}€ für finale Präsenz. Keine Risiken."

    # Marktadjustierung für konservative Option
    if market_growth > 8:
        cons_price += 5
        cons_ads += 10000
        cons_reason += " Boommarkt: Leicht höher investieren."
    elif market_growth < 0:
        cons_price -= 10
        cons_qty *= 0.95
        cons_reason += " Schwacher Markt: Preise anpassen, Mengen reduzieren."

    st.markdown(f"""
    **Preis:** {cons_price}€
    **Werbung:** {cons_ads:,}€
    **Entwickler:** {cons_devs}
    **Bestellmenge:** {cons_qty:,}

    **Begründung:** {cons_reason}
    """)
    st.markdown("</div>", unsafe_allow_html=True)

    # Ausgewogene Option
    st.markdown(
        """
        <div class="decision-card balanced">
        <h4>🟡 AUSGEWOGEN - Balancierte Strategie</h4>
        """,
        unsafe_allow_html=True
    )

    if current_period <= 2:
        bal_price = 559
        bal_ads = 120000
        bal_devs = 5
        bal_qty = 4000
        bal_reason = f"Preis {bal_price}€ für gute Margen bei Marktakzeptanz. Werbung {bal_ads:,}€ für Wachstum. Ausgewogen starten."
    elif current_period <= 5:
        bal_price = 549
        bal_ads = 170000
        bal_devs = 6
        bal_qty = 4500
        bal_reason = f"Preis {bal_price}€ für Marktanteil. Werbung {bal_ads:,}€ für Bekanntheit. Aktiv wachsen."
    else:
        bal_price = 569
        bal_ads = 220000
        bal_devs = 7
        bal_qty = 5200
        bal_reason = f"Preis {bal_price}€ für Gewinn-BSC-Balance. Werbung {bal_ads:,}€ für maximale Präsenz. BSC-Push."

    # Marktadjustierung für ausgewogene Option
    if market_growth > 8:
        bal_price += 8
        bal_ads += 20000
        bal_qty *= 1.05
        bal_reason += " Boommarkt: Mehr Kapital nutzen."
    elif market_growth < 0:
        bal_price -= 5
        bal_qty *= 0.9
        bal_reason += " Schwacher Markt: Risiken minimieren."

    st.markdown(f"""
    **Preis:** {bal_price}€
    **Werbung:** {bal_ads:,}€
    **Entwickler:** {bal_devs}
    **Bestellmenge:** {bal_qty:,}

    **Begründung:** {bal_reason}
    """)
    st.markdown("</div>", unsafe_allow_html=True)

    # Aggressive Option
    st.markdown(
        """
        <div class="decision-card aggressive">
        <h4>🔴 AGGRESSIV - Volles Risiko</h4>
        """,
        unsafe_allow_html=True
    )

    if current_period <= 2:
        agg_price = 549
        agg_ads = 140000
        agg_devs = 6
        agg_qty = 4200
        agg_reason = f"Preis {agg_price}€ für schnellen Marktanteil. Werbung {agg_ads:,}€ für Dominanz. Risiko für frühen Vorsprung."
    elif current_period <= 5:
        agg_price = 539
        agg_ads = 190000
        agg_devs = 7
        agg_qty = 4800
        agg_reason = f"Preis {agg_price}€ für Marktführerschaft. Werbung {agg_ads:,}€ für Überlegenheit. Volles Risiko für maximalen Erfolg."
    else:
        agg_price = 559
        agg_ads = 240000
        agg_devs = 8
        agg_qty = 5600
        agg_reason = f"Preis {agg_price}€ für finale Marktanteile. Werbung {agg_ads:,}€ für Sieg. Alles oder nichts."

    # Marktadjustierung für aggressive Option
    if market_growth > 8:
        agg_price += 12
        agg_ads += 30000
        agg_qty *= 1.1
        agg_reason += " Boommarkt: Maximum investieren!"
    elif market_growth < 0:
        agg_reason += " ⚠️ Schwacher Markt: Hohes Risiko - nicht empfohlen!"

    st.markdown(f"""
    **Preis:** {agg_price}€
    **Werbung:** {agg_ads:,}€
    **Entwickler:** {agg_devs}
    **Bestellmenge:** {agg_qty:,}

    **Begründung:** {agg_reason}
    """)
    st.markdown("</div>", unsafe_allow_html=True)

    # Wichtige Hinweise
    st.markdown("### ⚠️ Wichtige Hinweise:")
    warnings = []

    if competitor_price < cons_price - 20:
        warnings.append("Konkurrenz ist deutlich günstiger - Preisrisiko!")
    if current_marketshare < 15:
        warnings.append("Marktanteil zu niedrig - aggressiver werden!")
    if current_awareness < 120 and current_period > 3:
        warnings.append("Bekanntheit zu niedrig für diese Phase!")
    if current_innovation < 200 and current_period > 4:
        warnings.append("Innovation zu niedrig - BSC-Gefahr!")

    if warnings:
        for warning in warnings:
            st.warning(f"• {warning}")
    else:
        st.success("Parameter sehen grundsätzlich gut aus!")

    # BSC-Erinnerung
    st.info("**BSC-Erinnerung:** Nicht nur Gewinn zählt! Innovation, Arbeitsplätze, Nachhaltigkeit sind entscheidend für den Sieg.")

elif menu == "Run Vergleich":
    st.subheader("Run Vergleich")
    st.caption("Vergleiche deine Runs und lerne aus Erfolgen/Misserfolgen")

    if runs_df.empty:
        st.warning("Noch keine Runs zum Vergleichen vorhanden.")
    else:
        # BSC vs Gewinn Scatterplot
        scatter = px.scatter(
            runs_df,
            x="end_profit",
            y="end_bsc",
            text="name",
            title="Alle Runs: BSC vs. Gewinn",
            color="end_bsc",
            color_continuous_scale="RdYlGn",
            size="end_bsc",
        )
        scatter.update_traces(textposition="top center")
        st.plotly_chart(scatter, use_container_width=True)

        # Top 5 nach BSC
        st.subheader("🏆 Top Runs nach BSC")
        top_bsc = runs_df.nlargest(5, "end_bsc")[["name", "end_bsc", "end_profit", "place"]]
        top_bsc.columns = ["Run", "BSC", "Gewinn", "Platz"]
        st.dataframe(top_bsc, use_container_width=True, hide_index=True)

        # Top 5 nach Gewinn
        st.subheader("💰 Top Runs nach Gewinn")
        top_profit = runs_df.nlargest(5, "end_profit")[["name", "end_profit", "end_bsc", "place"]]
        top_profit.columns = ["Run", "Gewinn", "BSC", "Platz"]
        st.dataframe(top_profit, use_container_width=True, hide_index=True)

        # Durchschnittswerte
        col1, col2, col3 = st.columns(3)
        col1.metric("Ø BSC", f"{runs_df['end_bsc'].mean():.1f}")
        col2.metric("Ø Gewinn", format_currency(float(runs_df["end_profit"].mean())))
        col3.metric("Beste BSC", f"{runs_df['end_bsc'].max():.1f}")

        # Lernpunkte
        st.subheader("📚 Lernpunkte aus deinen Runs")
        best_run = runs_df.loc[runs_df["end_bsc"].idxmax()]
        worst_run = runs_df.loc[runs_df["end_bsc"].idxmin()]

        st.success(f"**Bester Run ({best_run['name']}):** BSC {best_run['end_bsc']:.1f}, Gewinn {format_currency(float(best_run['end_profit']))}")

        if len(runs_df) > 1:
            st.warning(f"**Verbesserungspotenzial ({worst_run['name']}):** BSC nur {worst_run['end_bsc']:.1f} - analysiere was schief lief")

        st.info("**Wichtige Erkenntnisse:** BSC zählt mehr als Gewinn allein. Arbeitsplätze, Innovation und Nachhaltigkeit sind entscheidend für den Sieg.")
