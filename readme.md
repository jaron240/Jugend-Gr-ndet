Jugend Gruender Ultra

Deploy-ready Streamlit dashboard for tracking runs, entering periods, comparing outcomes and generating quick strategy recommendations.

## Files

- `app.py` - main Streamlit app
- `requirements.txt` - Python dependencies for Streamlit Cloud
- `.gitignore` - ignores virtual environments, cache files and the local SQLite database

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Upload to GitHub

1. Create a new folder in VS Code and paste in `app.py`, `requirements.txt`, `.gitignore`, and this `README.md`.
2. Create a new GitHub repository.
3. Commit and push the files.

Example commands:

```bash
git init
git add .
git commit -m "Initial Streamlit app"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

## Connect it with Streamlit Community Cloud

1. Open [https://share.streamlit.io/](https://share.streamlit.io/)
2. Sign in with GitHub
3. Click **New app**
4. Pick your repository and branch
5. Set the main file path to `app.py`
6. Click **Deploy**

## Important note about data

This app stores data in a local SQLite file called `jugend_gruendet.db`.

That works well on your own machine, but on Streamlit Community Cloud local files are not durable long-term. The app therefore includes a **Backup als JSON herunterladen** button in the sidebar so you can regularly export your data.