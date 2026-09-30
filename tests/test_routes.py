"""Tests for main HTTP flows."""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Vinash" in response.text
    assert settings.cookie_name in response.cookies


def test_empty_capture_shows_error():
    response = client.post("/thoughts", data={"content": "  "}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/?error=empty"

    home = client.get("/?error=empty")
    assert "Write something first" in home.text


def test_capture_and_inbox():
    response = client.post(
        "/thoughts",
        data={"content": "Route test thought"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    inbox = client.get("/inbox")
    assert inbox.status_code == 200
    assert "Route test thought" in inbox.text


def test_reflection_page_is_observational():
    response = client.get("/reflection")
    assert response.status_code == 200
    assert "Not a diagnosis" in response.text
    assert "thoughts captured" in response.text


def test_anonymous_isolation_between_clients():
    user_a = TestClient(app)
    user_b = TestClient(app)

    user_a.post("/thoughts", data={"content": "Thought A"}, follow_redirects=True)
    user_b.post("/thoughts", data={"content": "Thought B"}, follow_redirects=True)

    inbox_a = user_a.get("/inbox")
    inbox_b = user_b.get("/inbox")

    assert "Thought A" in inbox_a.text
    assert "Thought B" not in inbox_a.text
    assert "Thought B" in inbox_b.text
    assert "Thought A" not in inbox_b.text


def test_same_client_keeps_identity():
    first = TestClient(app)
    first.post("/thoughts", data={"content": "Persistent"}, follow_redirects=True)
    cookie = first.cookies.get(settings.cookie_name)
    assert cookie

    second = TestClient(app)
    second.cookies.set(settings.cookie_name, cookie)
    inbox = second.get("/inbox")
    assert "Persistent" in inbox.text


def test_cannot_open_other_users_thought():
    user_a = TestClient(app)
    user_b = TestClient(app)

    user_a.post("/thoughts", data={"content": "Private"}, follow_redirects=True)
    thought_id = None
    inbox = user_a.get("/inbox")
    for line in inbox.text.split("thought-link"):
        if "Private" in line:
            break
    # fetch id from db via listing - use detail link pattern
    import re

    match = re.search(r"/thoughts/(\d+)", inbox.text)
    assert match
    thought_id = match.group(1)

    response = user_b.get(f"/thoughts/{thought_id}")
    assert response.status_code == 404


def test_let_go_flow():
    response = client.post("/thoughts", data={"content": "Let go me"}, follow_redirects=True)
    assert response.status_code == 200
    inbox = client.get("/inbox")
    import re

    match = re.search(r"/thoughts/(\d+)", inbox.text)
    assert match
    thought_id = match.group(1)

    client.post(f"/thoughts/{thought_id}/let-go", follow_redirects=True)
    let_go = client.get("/inbox?view=let_go")
    assert "Let go me" in let_go.text
