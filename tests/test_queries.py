"""Tests for thought and action behavior in the database layer."""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

import app.db as database
from app.queries import (
    complete_action,
    create_anonymous_user,
    create_thought,
    delete_all_for_user,
    get_thought,
    list_active_inbox_thoughts,
    list_open_actions,
    list_revisit_thoughts,
    revisit_now,
    save_action,
    schedule_revisit,
    weekly_reflection_stats,
)


@pytest.fixture
def db() -> Session:
    database.init_db()
    session = database.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _user(db: Session):
    user_id = uuid4()
    create_anonymous_user(db, user_id)
    return user_id


def test_capture_and_inbox_order(db: Session):
    user_id = _user(db)
    first = create_thought(db, user_id, "First")
    second = create_thought(db, user_id, "Second")
    inbox = list_active_inbox_thoughts(db, user_id)
    assert [row["id"] for row in inbox[:2]] == [second, first]


def test_empty_thought_rejected(db: Session):
    user_id = _user(db)
    with pytest.raises(ValueError):
        create_thought(db, user_id, "   ")


def test_action_leaves_inbox_until_completed(db: Session):
    user_id = _user(db)
    thought_id = create_thought(db, user_id, "Do something")
    save_action(db, user_id, thought_id, "One small step")
    assert not any(row["id"] == thought_id for row in list_active_inbox_thoughts(db, user_id))

    action_id = list_open_actions(db, user_id)[0]["action_id"]
    complete_action(db, user_id, action_id)
    assert not list_open_actions(db, user_id)


def test_revisit_hides_until_due(db: Session):
    user_id = _user(db)
    thought_id = create_thought(db, user_id, "Later")
    schedule_revisit(db, user_id, thought_id, date.today() + timedelta(days=2))
    assert thought_id in [row["id"] for row in list_revisit_thoughts(db, user_id)]
    assert thought_id not in [row["id"] for row in list_active_inbox_thoughts(db, user_id)]

    schedule_revisit(db, user_id, thought_id, date.today())
    assert thought_id in [row["id"] for row in list_active_inbox_thoughts(db, user_id)]


def test_revisit_now_returns_to_inbox(db: Session):
    user_id = _user(db)
    thought_id = create_thought(db, user_id, "Come back")
    schedule_revisit(db, user_id, thought_id, date.today() + timedelta(days=5))
    revisit_now(db, user_id, thought_id)
    assert thought_id in [row["id"] for row in list_active_inbox_thoughts(db, user_id)]
    assert thought_id not in [row["id"] for row in list_revisit_thoughts(db, user_id)]


def test_weekly_stats_increase_on_capture(db: Session):
    user_id = _user(db)
    before = weekly_reflection_stats(db, user_id)["captured"]
    create_thought(db, user_id, "Reflection count")
    after = weekly_reflection_stats(db, user_id)["captured"]
    assert after == before + 1


def test_user_isolation(db: Session):
    user_a = _user(db)
    user_b = _user(db)
    thought_a = create_thought(db, user_a, "Thought A")
    thought_b = create_thought(db, user_b, "Thought B")

    assert get_thought(db, user_a, thought_a) is not None
    assert get_thought(db, user_a, thought_b) is None
    assert get_thought(db, user_b, thought_b) is not None
    assert get_thought(db, user_b, thought_a) is None

    inbox_a = list_active_inbox_thoughts(db, user_a)
    assert len(inbox_a) == 1
    assert inbox_a[0]["content"] == "Thought A"


def test_delete_all_for_user(db: Session):
    user_id = _user(db)
    create_thought(db, user_id, "Remove me")
    delete_all_for_user(db, user_id)
    assert list_active_inbox_thoughts(db, user_id) == []
