# News Mood

Grabs the latest headlines and rates each one as **positive** or **negative**. You can rate them too, and a machine-learning model gradually learns to rate news the way *you* do.

## How it works

1. **Fetch:** pulls headlines from free RSS feeds (BBC, CNBC, MarketWatch, Guardian, NPR) in two categories, *Financial* and *General*.
2. **Generic start:** until you've rated enough articles, it uses [VADER](https://github.com/cjhutto/vaderSentiment), a general-purpose sentiment scorer.
3. **Learns you:** once you've rated 10 articles (at least 3 of each kind), it trains a logistic regression on TF-IDF word features plus the VADER score, and retrains every time you rate another one.
4. **Active learning:** the *Rate* tab shows the articles the model is least sure about first, because those teach it the most.
5. **Transparency:** the *What it has learned* tab shows which words push it towards positive or negative, and how often it agrees with you on ratings it wasn't trained on.

## Desktop app (macOS)

Build it once:

```bash
scripts/build_mac_app.sh
```

This creates **News Mood.app** in `~/Applications`, with a shortcut on your Desktop. Double-click it to open the app in its own window, with no browser. You can drag it to the Dock to keep it there. The app runs the code in this folder, so changes you make show up the next time you open it. Logs go to `~/Library/Logs/NewsMood.log`.

## Run it from the terminal

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python desktop.py        # native window
streamlit run app.py     # or in the browser
```

Run the tests with `pytest`.

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI |
| `desktop.py` | Opens the UI in a native window |
| `scripts/build_mac_app.sh` | Builds News Mood.app |
| `scripts/make_icon.py` | Draws the app icon |
| `news.py` | RSS feed list and fetching |
| `db.py` | SQLite storage for articles and ratings (`data/news.db`) |
| `model.py` | The personal sentiment model |
| `test_model.py` | Tests |
