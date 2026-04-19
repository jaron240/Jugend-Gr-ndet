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
    page_title="Jugend Gruender",
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

st.markdown(
    """
    <div class="hero">
        <h1>Jugend Gruender</h1>
        <p>Entscheidungshilfe für Jugend Gründet Teams - BSC optimieren, besser entscheiden, Siege holen.</p>
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
        current_period = runs_df.loc[runs_df["id"] == run_id, "current_period"].iloc[0]
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
    st.subheader("Schnelle Entscheidungshilfen")
    st.caption("Praktische Empfehlungen basierend auf Spielphase und Marktlage")

    col1, col2 = st.columns(2)
    market_growth = col1.slider("Marktwachstum %", -15, 20, 5)
    current_period = col2.selectbox("Aktuelle Periode", list(range(1, 9)), index=0)

    # Phase bestimmen
    if current_period <= 2:
        phase = "Frühphase"
        phase_desc = "Fokus: Vertrauen aufbauen, effizient arbeiten"
        base_price = 569
        ads_rec = "90k-130k"
        devs_rec = 5
        sales_rec = "4-5"
        qty_factor = 1.0
    elif current_period <= 5:
        phase = "Mittelphase"
        phase_desc = "Fokus: Marktanteil gewinnen, Innovation steigern"
        base_price = 559
        ads_rec = "140k-180k"
        devs_rec = 6
        sales_rec = 6
        qty_factor = 1.1
    else:
        phase = "Endgame"
        phase_desc = "Fokus: BSC maximieren, saubere Performance"
        base_price = 579
        ads_rec = "180k-230k"
        devs_rec = 7
        sales_rec = 7
        qty_factor = 1.2

    # Marktadjustierung
    if market_growth > 8:
        base_price += 10
        ads_rec = "erhöhen (+25k)"
        sales_rec = str(int(sales_rec) + 1) if isinstance(sales_rec, int) else f"{sales_rec.split('-')[0]}-{int(sales_rec.split('-')[1]) + 1}"
        qty_factor *= 1.08
    elif market_growth < 0:
        base_price -= 15
        qty_factor *= 0.92

    base_qty = int(4000 * qty_factor)

    st.markdown(f"### {phase} (Periode {current_period})")
    st.info(phase_desc)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Preis", f"{base_price} EUR")
    c2.metric("Werbung", ads_rec)
    c3.metric("Entwickler", devs_rec)
    c4.metric("Vertrieb", sales_rec)
    c5.metric("Bestellmenge", f"{base_qty:,}")

    st.markdown("**Wichtige Tipps:**")
    tips = []
    if current_period <= 2:
        tips = [
            "Vertrauen durch saubere Prozesse aufbauen",
            "Nicht zu aggressiv starten",
            "Gewinn machen, aber BSC nicht vernachlässigen"
        ]
    elif current_period <= 5:
        tips = [
            "Marktanteil aktiv ausbauen",
            "Innovation über 200 halten",
            "Bekanntheit systematisch steigern"
        ]
    else:
        tips = [
            "BSC ist wichtiger als reiner Gewinn",
            "Arbeitsplätze schaffen zählt",
            "Keine Fehler in den letzten Perioden"
        ]

    if market_growth > 8:
        tips.append("Boommarkt: Mehr investieren!")
    elif market_growth < 0:
        tips.append("Schwacher Markt: Konservativ bleiben")

    for tip in tips:
        st.write(f"• {tip}")

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
