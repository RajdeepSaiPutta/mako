"""Offline tests for the export endpoint and score suggestions.

Usage:
    python test_features.py
"""

import os
import sys
import tempfile

os.environ.setdefault("GROQ_API_KEY", "gsk_dummy")
os.environ.setdefault("GEMINI_API_KEY", "AIza_dummy")
os.environ.setdefault("ADMIN_API_KEY", "admin-secret-123")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:8000")
os.environ["DB_PATH"] = tempfile.mktemp(suffix=".db")

from fastapi.testclient import TestClient

from app.main import create_app

PASS = 0
FAIL = 0
ERRORS: list[str] = []


def test(name: str):
    def decorator(fn):
        global PASS, FAIL
        try:
            fn()
            PASS += 1
            print(f"  PASS  {name}")
        except Exception as e:
            FAIL += 1
            ERRORS.append(f"{name}: {type(e).__name__}: {e}")
            print(f"  FAIL  {name}: {e}")
        return fn

    return decorator


client = TestClient(create_app())


@test("export markdown echoes body with attachment header")
def _():
    r = client.post(
        "/api/export-article",
        json={"title": "Salt Desert Pricing Guide", "article_text": "# hello\n\nworld", "format": "md"},
    )
    assert r.status_code == 200, r.status_code
    assert r.text == "# hello\n\nworld"
    assert "text/markdown" in r.headers["content-type"]
    disp = r.headers["content-disposition"]
    assert disp == 'attachment; filename="salt-desert-pricing-guide.md"', disp


@test("export plain text works too")
def _():
    r = client.post(
        "/api/export-article",
        json={"title": "My Article", "article_text": "plain body", "format": "txt"},
    )
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    assert 'filename="my-article.txt"' in r.headers["content-disposition"]


@test("export rejects empty body and bad format")
def _():
    r = client.post("/api/export-article", json={"title": "x", "article_text": "", "format": "md"})
    assert r.status_code == 422, r.status_code
    r = client.post("/api/export-article", json={"title": "x", "article_text": "y", "format": "pdf"})
    assert r.status_code == 422, r.status_code


@test("score returns suggestions for a thin article")
def _():
    r = client.post("/api/score-article", json={"article_text": "tiny text here", "target_keyword": "salt"})
    assert r.status_code == 200, r.status_code
    body = r.json()
    assert "suggestions" in body and isinstance(body["suggestions"], list)
    joined = " ".join(body["suggestions"])
    assert "short" in joined
    assert "headings" in joined
    assert "salt" in joined  # keyword density tip names the keyword


@test("score of a solid article says so")
def _():
    text = "# Salt Deserts\n\nA fine and considerate article about salt deserts. " + "repeated ok words are fun " * 120 + "\n\n## Section one\n\nmore words here about salt and sun.\n\n## Section two\n\nand even more useful words following.\n\n## Section three\n\nenough."
    r = client.post("/api/score-article", json={"article_text": text})
    assert r.status_code == 200, r.status_code
    suggestions = r.json()["suggestions"]
    assert isinstance(suggestions, list) and len(suggestions) >= 1


print(f"\n{PASS} passed, {FAIL} failed")
if ERRORS:
    print("\n".join("ERROR: " + e for e in ERRORS))
sys.exit(1 if FAIL else 0)
