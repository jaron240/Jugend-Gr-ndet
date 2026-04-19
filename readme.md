# 📖 Planspiel Tracker JG - Bedienungsanleitung

## 🎯 Überblick

**Planspiel Tracker JG** ist ein professionelles Tool für Jugend Gründet Teams, das BSC-Optimierung, Live-Entscheidungen und Siegchancen-Maximierung ermöglicht.

### ✨ Hauptfunktionen
- **🏠 Dashboard** - Live-Übersicht mit interaktiven Charts
- **⚡ Quick Input** - 30-Sekunden Dateneingabe pro Periode
- **🎯 Entscheidungen** - Strategische Empfehlungen mit Begründungen
- **📊 Analyse** - Erweiterte Visualisierungen & Korrelationen
- **🚨 Frühwarnsystem** - Risikoanalyse & präventive Hinweise
- **👥 Teams** - Kollaboration mit automatischen Team-Codes
- **💾 Backup** - Daten-Export/Import für Cross-Device-Sync

---

## 🚀 Erste Schritte

### 1. App starten
```bash
pip install -r requirements.txt
streamlit run app.py
```

### 2. Ersten Run erstellen
1. Gehe zum Tab **⚡ Quick Input**
2. Klicke **➕ Neuer Run**
3. Gib einen Namen ein (z.B. "Unser Jugend Gründet Run")
4. Der Run wird automatisch erstellt

### 3. Daten eingeben
1. Wähle deinen Run aus dem Dropdown
2. Wähle die Periode (1-8)
3. Gib deine Entscheidungen ein:
   - Preise für Markt 1 (und Markt 2 ab Periode 5)
   - Mengen für beide Märkte
   - Werbebudget, Entwickler, Vertrieb
   - Prozessbudget
4. Gib die Periodenergebnisse ein (Gewinn, BSC, etc.)
5. Klicke **💾 Periode speichern**

---

## 👥 Team-Funktionen

### Automatische Geräte-Trennung
Jedes Gerät bekommt automatisch eine eigene ID für separate Datenspeicherung. Keine Konfiguration nötig!

### Team erstellen
1. Gehe zum Tab **⚙️ Einstellungen**
2. Gib einen Team-Namen ein (z.B. "JG Team Alpha")
3. Klicke **🎯 Team erstellen**
4. **WICHTIG:** Merke dir den angezeigten **Team-Code** (z.B. `TEAM-A1B2C3`)
5. Teile den Code nur mit vertrauten Teammitgliedern

### Team beitreten
1. Gehe zum Tab **⚙️ Einstellungen**
2. Gib den Team-Code ein (z.B. `TEAM-A1B2C3` oder nur `A1B2C3`)
3. Klicke **🎯 Beitreten**
4. Du siehst jetzt die gemeinsamen Daten

### Team verlassen
1. Klicke **🔒 Privatmodus** in den Einstellungen
2. Du bist wieder in deinem privaten Modus

### Teams verwalten
- **Alle Teams anzeigen:** In den Einstellungen siehst du alle verfügbaren Teams
- **Team löschen:** Klicke das 🗑️ Symbol neben einem Team
- **Team-Codes:** Nur der Ersteller sieht den geheimen Code

---

## 📊 Dashboard verwenden

### Live-Übersicht
- **Aktive Runs:** Anzahl laufender Simulationen
- **Bester BSC:** Höchster erreichter BSC-Score
- **Abgeschlossene Runs:** Anzahl fertig gespielter Runs
- **Ø BSC:** Durchschnittlicher BSC aller Runs

### Visualisierungen
- **BSC vs. Gewinn:** Scatterplot zur Performance-Analyse
- **BSC-Verteilung:** Histogramm aller BSC-Werte
- **Zeitliche Entwicklung:** BSC- und Gewinn-Trends über Perioden

### Top-Performer
- **Top 5 BSC-Scores:** Beste Ergebnisse
- **Top 5 Gewinne:** Höchste Profite

---

## 🎯 Entscheidungshilfe

### Strategische Empfehlungen
1. Wähle die **Periode** und **Marktwachstum**
2. Gib deinen **Konkurrenzpreis** und **Marktanteil** ein
3. Erhalte **drei Strategien:**
   - 🟢 **Konservativ:** Risikominimierung
   - 🟡 **Ausgewogen:** Optimale Balance
   - 🔴 **Aggressiv:** Volles Risiko

### BSC-Erinnerung
**WICHTIG:** Jugend Gründet bewertet nicht nur Gewinn!
- **Innovation** (Forschung & Entwicklung)
- **Bekanntheit** (Marketing & PR)
- **Arbeitsplätze** (Personalaufstockung)
- **Nachhaltigkeit** (strategische Entscheidungen)

---

## 📈 Analyse-Funktionen

### Run-Analyse
1. Wähle einen Run aus
2. Sieh dir **Metriken** an: Perioden, Max BSC, Max Gewinn
3. Analysiere **Visualisierungen:**
   - KPIs im Zeitverlauf
   - Korrelationsmatrix
   - Radar-Charts für BSC-Komponenten
   - ROI-Analyse pro Periode

### Korrelationsanalyse
- **Scatterplot-Matrix:** Zusammenhänge zwischen Variablen
- **Korrelations-Heatmap:** Stärke der Beziehungen
- **Wachstumsraten:** Perioden-über-Perioden Entwicklung

---

## 🚨 Frühwarnsystem

### Risikoanalyse
Das System erkennt automatisch kritische Risiken:
- **Überinvestition:** Zu hohe Ausgaben vs. Gewinn
- **Marktverlust:** Zu niedriger Marktanteil
- **BSC-Verlust:** Fehlende Innovation/Bekanntheit
- **Planungsfehler:** Zu große Mengenänderungen

### Präventive Hinweise
- **Frühphase:** Werbung aufbauen
- **Endgame:** Innovation maximieren
- **Marktposition:** Marktanteil überwachen

---

## 💾 Daten-Management

### Backup erstellen
1. Gehe zu **⚙️ Einstellungen**
2. Klicke **💾 Backup** (oben rechts)
3. JSON-Datei wird heruntergeladen

### Daten importieren
1. Gehe zu **⚙️ Einstellungen**
2. Ziehe eine JSON-Backup-Datei in den Upload-Bereich
3. Klicke **🔄 Daten importieren**

### Runs verwalten
1. Gehe zu **🗑️ Run Management**
2. Sieh dir die **Run-Übersicht** an
3. Zum Löschen: Run auswählen, Namen bestätigen, **🗑️ Run endgültig löschen**

---

## 🔧 Einstellungen & Konfiguration

### Team-Status
Im Header siehst du immer deinen aktuellen Modus:
- 🔒 **Privatmodus** - Nur deine Daten
- 👥 **Team: [Name]** - Gemeinsame Daten

### Datenbank-Info
- **Gesamt Runs:** Anzahl aller Runs
- **Gesamt Perioden:** Anzahl aller Eingaben
- **DB-Größe:** Speicherplatz-Verbrauch

---

## 📱 Mobile Nutzung

Das Tool ist vollständig mobil optimiert:
- **Touch-freundliche Buttons** (44px Mindestgröße)
- **Responsive Layout** - passt sich automatisch an
- **Keine Zoom-Probleme** auf iOS
- **Vollständige Funktionalität** auf Smartphones & Tablets

---

## 🆘 Fehlerbehebung

### Team-Code funktioniert nicht
- Stelle sicher, dass du den **genauen Code** eingibst
- Codes sind case-sensitive (Groß-/Kleinschreibung)
- Der Code muss mit `TEAM-` beginnen oder du gibst nur den Teil danach ein

### Daten werden nicht gespeichert
- Auf Streamlit Cloud: Nutze regelmäßig den **Backup-Button**
- Lokal: Daten bleiben in `jugend_gruendet.db` erhalten

### App reagiert nicht
- **🔄 Aktualisieren** Button in den Einstellungen
- Seite neu laden (F5)
- Bei Streamlit Cloud: App neu starten

### Team-Daten verschwinden
- Teams können von jedem gelöscht werden
- Erstelle bei Bedarf ein neues Team
- Nutze regelmäßige Backups

---

## 📋 Wichtige Jugend Gründet Tipps

### BSC-Maximierung
- **Nicht zu konservativ:** Zu wenig Mitarbeiter = BSC-Verlust
- **Werbung wirkt langfristig:** Früh investieren zahlt sich aus
- **Innovation zählt:** Forschung & Entwicklung nicht vernachlässigen
- **Arbeitsplätze schaffen:** Personal aufstocken für BSC-Punkte

### Strategische Entscheidungen
- **Markt 2 ab Periode 5:** Frühere Perioden haben nur Markt 1
- **Periodenbewusst:** Tool passt sich automatisch an
- **Balance halten:** Gewinn UND BSC sind wichtig
- **Risiken vermeiden:** Frühwarnsystem nutzen

### Datenmanagement
- **Regelmäßige Backups:** Auf Streamlit Cloud essentiell
- **Team-Codes geheim halten:** Nur vertrauten Mitgliedern geben
- **Runs dokumentieren:** Klare Namen für bessere Übersicht

---

## 🛠️ Technische Informationen

### Dateien
- `app.py` - Haupt-Streamlit-Anwendung
- `requirements.txt` - Python-Abhängigkeiten
- `.gitignore` - Git-Konfiguration
- `jugend_gruendet.db` - Lokale SQLite-Datenbank

### Systemanforderungen
- **Python 3.8+**
- **Streamlit**
- **Pandas, Plotly**
- **SQLite** (automatisch enthalten)

### Deployment
```bash
# Lokal testen
pip install -r requirements.txt
streamlit run app.py

# Auf Streamlit Cloud deployen
1. GitHub-Repository erstellen
2. share.streamlit.io besuchen
3. Repository verbinden
4. app.py als Hauptfile setzen
```

---

## 📞 Support & Hilfe

Bei Problemen:
1. **🔄 Aktualisieren** Button probieren
2. Seite neu laden (F5)
3. Backup erstellen und App neu starten
4. Bei anhaltenden Problemen: Daten zurücksetzen und neu beginnen

**Viel Erfolg bei Jugend Gründet!** 🏆

---

*Planspiel Tracker JG v2.0 - Professionelle BSC-Optimierung für Jugend Gründet Teams*
