# Jugend Gruender

Dunkles Live-Tool für Jugend Gründet Teams - BSC optimieren, besser entscheiden, Siege holen.

## Was ist das?

Ein einfaches, schnelles Tool für Jugend Gründet Teams mit dunklem Design:
- **🏠 Live Center** - Übersicht über alle Runs
- **⚡ Quick Input** - 30-Sekunden Dateneingabe pro Periode
- **🎯 Entscheidungen** - Drei strategische Optionen (Sicher/Balanciert/Aggressiv)
- **📊 Analyse** - Charts und Vergleiche

## Wichtige Erkenntnisse

- **BSC zählt mehr als Gewinn allein** - Innovation, Arbeitsplätze, Nachhaltigkeit entscheiden
- **Nicht zu konservativ** - zu wenig Mitarbeiter kann trotz Gewinn zum Verlust führen
- **Werbung wirkt langfristig** - früh investieren zahlt sich aus
- **Markt 2 ab Periode 5** - frühere Perioden haben nur Markt 1
- **Periodenbewusst** - Tool passt sich automatisch an die Spielphase an

## Dateien

- `app.py` - Haupt-Streamlit-App
- `requirements.txt` - Python-Abhängigkeiten für Streamlit Cloud
- `.gitignore` - ignoriert virtuelle Umgebungen, Cache-Dateien und lokale SQLite-Datenbank

## Lokal ausführen

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Auf GitHub hochladen

1. Erstelle einen neuen Ordner in VS Code und füge `app.py`, `requirements.txt`, `.gitignore` und diese `README.md` hinzu
2. Erstelle ein neues GitHub-Repository
3. Commite und pushe die Dateien

Beispiel-Befehle:

```bash
git init
git add .
git commit -m "Initial Jugend Gruender App"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

## Mit Streamlit Community Cloud verbinden

1. Öffne [https://share.streamlit.io/](https://share.streamlit.io/)
2. Melde dich mit GitHub an
3. Klicke **New app**
4. Wähle dein Repository und Branch
5. Setze den Haupt-Dateipfad auf `app.py`
6. Klicke **Deploy**

## Wichtiger Hinweis zu Daten

Die App speichert Daten in einer lokalen SQLite-Datei namens `jugend_gruendet.db`.

Das funktioniert gut auf deinem eigenen Rechner, aber auf Streamlit Community Cloud sind lokale Dateien nicht dauerhaft. Die App enthält daher einen **Backup als JSON herunterladen** Button in der Sidebar, damit du regelmäßig deine Daten exportieren kannst.
