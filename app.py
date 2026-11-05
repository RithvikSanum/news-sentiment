"""Streamlit app: read the latest news, rate it, and watch the model learn your taste.

Run with:  streamlit run app.py
"""

import hashlib

import pandas as pd
import streamlit as st

import db
import news
from model import MIN_PER_CLASS, MIN_RATINGS, Rater

st.set_page_config(page_title="News Mood", page_icon="📰", layout="wide")


@st.cache_resource
def get_conn():
    return db.connect()


@st.cache_resource(max_entries=1)
def get_model(_conn, version):
    """Retrain only when the ratings change (version is the cache key)."""
    return Rater().fit(db.get_articles(_conn, rated=True))


def key_for(link, suffix):
    return f"{suffix}-{hashlib.md5(link.encode()).hexdigest()}"


def fetch(conn, categories):
    with st.spinner("Fetching the latest headlines..."):
        articles, errors = news.fetch_all(categories)
        added = db.add_articles(conn, articles)
    st.session_state.fetch_msg = (added, errors)


def rate(link, label):
    db.set_label(get_conn(), link, label)


def badge(prob):
    if prob >= 0.5:
        return f":green[**▲ Positive**] · {prob:.0%}"
    return f":red[**▼ Negative**] · {1 - prob:.0%}"


conn = get_conn()
st.session_state.setdefault("skipped", set())

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("📰 News Mood")
    categories = st.multiselect("Categories", list(news.FEEDS), default=list(news.FEEDS))
    if st.button("Fetch latest news", type="primary", use_container_width=True):
        fetch(conn, categories or list(news.FEEDS))

    if "fetch_msg" in st.session_state:
        added, errors = st.session_state.fetch_msg
        st.success(f"Added {added} new article{'s' * (added != 1)}.")
        for err in errors:
            st.warning(err)

    model = get_model(conn, db.ratings_version(conn))
    st.divider()
    st.subheader("Model")
    if model.is_personal:
        st.markdown(f"🧠 **Personal model** trained on **{model.n_trained}** of your ratings.")
        if model.cv_accuracy is not None:
            st.metric("Agrees with you", f"{model.cv_accuracy:.0%}",
                      help="Cross-validated: accuracy on ratings it wasn't trained on.")
    else:
        st.markdown("🤖 Using a **generic** sentiment model for now.")
        st.progress(min(model.n_trained / MIN_RATINGS, 1.0),
                    text=f"{model.n_trained}/{MIN_RATINGS} ratings until it learns your taste "
                         f"(need at least {MIN_PER_CLASS} positive and {MIN_PER_CLASS} negative)")
    if model.vader_accuracy is not None:
        st.caption(f"Generic model agrees with you {model.vader_accuracy:.0%} of the time.")

# First run: grab some news automatically.
if not db.get_articles(conn):
    fetch(conn, list(news.FEEDS))
    st.rerun()

articles = db.get_articles(conn, categories=categories or None)
probs = model.predict_proba(articles)
for a, p in zip(articles, probs):
    a["prob"] = float(p)

feed_tab, rate_tab, stats_tab = st.tabs(["Feed", "Rate", "What it has learned"])

# ---------------------------------------------------------------- feed
with feed_tab:
    c1, c2, c3 = st.columns([2, 2, 3])
    mood = c1.radio("Show", ["All", "Positive", "Negative"], horizontal=True)
    sources = sorted({a["source"] for a in articles})
    chosen = c2.multiselect("Sources", sources, placeholder="All sources")
    search = c3.text_input("Search", placeholder="Filter headlines...")

    shown = [
        a for a in articles
        if (mood == "All" or (a["prob"] >= 0.5) == (mood == "Positive"))
        and (not chosen or a["source"] in chosen)
        and search.lower() in (a["title"] + " " + (a["summary"] or "")).lower()
    ]
    st.caption(f"{len(shown)} articles")

    for a in shown[:100]:
        with st.container(border=True):
            left, right = st.columns([6, 1.4])
            left.markdown(f"**[{a['title']}]({a['link']})**")
            if a["summary"]:
                left.caption(a["summary"])
            date = (a["published"] or a["fetched_at"])[:10]
            left.markdown(f"{badge(a['prob'])} &nbsp;·&nbsp; {a['source']} · {date}")

            label = a["user_label"]
            right.button("👍 Positive", key=key_for(a["link"], "fp"), on_click=rate,
                         args=(a["link"], db.POSITIVE), use_container_width=True,
                         type="primary" if label == db.POSITIVE else "secondary")
            right.button("👎 Negative", key=key_for(a["link"], "fn"), on_click=rate,
                         args=(a["link"], db.NEGATIVE), use_container_width=True,
                         type="primary" if label == db.NEGATIVE else "secondary")
    if len(shown) > 100:
        st.caption("Showing the first 100. Narrow the filters to see more.")

# ---------------------------------------------------------------- rate
with rate_tab:
    st.markdown("Rate articles one at a time. It shows the ones the model is **least sure about** "
                "first, because those teach it the most.")
    queue = sorted(
        (a for a in articles
         if a["user_label"] is None and a["link"] not in st.session_state.skipped),
        key=lambda a: abs(a["prob"] - 0.5),
    )
    if not queue:
        st.info("Nothing left to rate. Fetch more news from the sidebar.")
    else:
        a = queue[0]
        st.caption(f"{len(queue)} unrated · {a['source']} · {a['category']}")
        with st.container(border=True):
            st.subheader(a["title"])
            if a["summary"]:
                st.write(a["summary"])
            st.markdown(f"Model's guess: {badge(a['prob'])} &nbsp; [Read article]({a['link']})")
        b1, b2, b3 = st.columns(3)
        b1.button("👍 Positive", on_click=rate, args=(a["link"], db.POSITIVE),
                  use_container_width=True, type="primary", key="rate-pos")
        b2.button("👎 Negative", on_click=rate, args=(a["link"], db.NEGATIVE),
                  use_container_width=True, type="primary", key="rate-neg")
        b3.button("Skip", on_click=lambda link=a["link"]: st.session_state.skipped.add(link),
                  use_container_width=True, key="rate-skip")

# ---------------------------------------------------------------- stats
with stats_tab:
    rated = db.get_articles(conn, rated=True)
    if not rated:
        st.info("Rate some articles and this tab will show what the model has learned about you.")
    else:
        n_pos = sum(a["user_label"] == db.POSITIVE for a in rated)
        m1, m2, m3 = st.columns(3)
        m1.metric("Your ratings", len(rated))
        m2.metric("Positive", n_pos)
        m3.metric("Negative", len(rated) - n_pos)

        pos_words, neg_words = model.top_words()
        if pos_words or neg_words:
            st.subheader("Words that sway the model")
            w1, w2 = st.columns(2)
            w1.markdown("**Make it think *positive***")
            w1.dataframe(pd.DataFrame(pos_words, columns=["word", "weight"]),
                         hide_index=True, use_container_width=True)
            w2.markdown("**Make it think *negative***")
            w2.dataframe(pd.DataFrame(neg_words, columns=["word", "weight"]),
                         hide_index=True, use_container_width=True)

        st.subheader("Your recent ratings")
        recent = sorted(rated, key=lambda a: a["rated_at"] or "", reverse=True)[:30]
        for a in recent:
            c1, c2 = st.columns([8, 1])
            mark = "👍" if a["user_label"] == db.POSITIVE else "👎"
            c1.markdown(f"{mark} {a['title']}  \n:gray[{a['source']}]")
            c2.button("Undo", key=key_for(a["link"], "undo"), on_click=rate, args=(a["link"], None))
