import db
from model import Rater


def make(title, label):
    return {"title": title, "summary": "", "user_label": label}


def test_falls_back_to_generic_with_few_ratings():
    model = Rater().fit([make("Great win", 1), make("Awful crash", 0)])
    assert not model.is_personal
    good, bad = model.predict_proba([make("Wonderful happy news", None), make("Terrible disaster", None)])
    assert good > 0.5 > bad


def test_learns_personal_taste_that_disagrees_with_generic():
    # This user thinks rate cuts are good and tech layoffs are... also good (cheaper stocks?).
    # The point: the model must follow *the user*, not generic sentiment.
    data = (
        [make(f"Tech giant announces layoffs round {i}", 1) for i in range(8)]
        + [make(f"Celebrity wedding celebration party {i}", 0) for i in range(8)]
    )
    model = Rater().fit(data)
    assert model.is_personal
    layoffs, wedding = model.predict_proba(
        [make("Another tech firm announces layoffs", None), make("Lavish wedding celebration", None)]
    )
    assert layoffs > 0.5 > wedding


def test_db_roundtrip(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    art = {"link": "http://x", "title": "T", "summary": "", "source": "S",
           "category": "General", "published": None}
    assert db.add_articles(conn, [art, art]) == 1
    db.set_label(conn, "http://x", db.POSITIVE)
    assert db.get_articles(conn, rated=True)[0]["user_label"] == 1
    db.set_label(conn, "http://x", None)
    assert db.get_articles(conn, rated=False)
