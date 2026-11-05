# news-sentiment (News Mood)

Streamlit app that fetches RSS headlines, lets the user rate them positive/negative, and trains a personal sentiment model (TF-IDF + VADER feature + logistic regression) on those ratings.

Run: `venv/bin/streamlit run app.py` · Test: `venv/bin/python -m pytest -q`

## Git workflow: keep GitHub constantly updated

- After every meaningful, working change, commit it and push to `origin main` right away, without asking first.
- Make small, focused commits with clear messages in the imperative mood.
- Run the tests before committing. Don't commit broken code.
- Never commit `venv/`, `data/` (the user's ratings DB), secrets or API keys.
- If you add a dependency, update `requirements.txt` in the same commit.
