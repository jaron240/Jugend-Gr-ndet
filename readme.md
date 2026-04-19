# Jugend Gruender

Entscheidungshilfe für Jugend Gründet Teams - BSC optimieren, besser entscheiden, Siege holen.

## Was ist das?

Ein einfaches, praktisches Tool für Jugend Gründet Teams, das hilft:
- Runs und Perioden zu tracken
- BSC und Gewinn zu analysieren
- Schnelle Entscheidungshilfen zu bekommen
- Aus vergangenen Runs zu lernen

## Wichtige Erkenntnisse

- **BSC zählt mehr als Gewinn allein** - Innovation, Nachhaltigkeit und Arbeitsplätze sind entscheidend
- **Nicht zu konservativ sein** - zu wenig Mitarbeiter/Innovation kann trotz gutem Gewinn zum Verlust führen
- **Werbung wirkt langfristig** - früh investieren lohnt sich
- **Prozessbudget ist wichtig** - effiziente Abläufe zahlen sich aus

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
