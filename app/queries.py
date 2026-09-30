"""Database operations for thoughts and actions."""

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.dates import current_week_bounds_utc
from app.models import Action, AnonymousUser, Thought

CATEGORIES = (
    "work",
    "family",
    "personal",
    "money",
    "health",
    "ideas",
    "other",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _validate_thought_text(content: str) -> str:
    text = content.strip()
    if not text:
        raise ValueError("Thought cannot be empty.")
    if len(text) > settings.max_thought_chars:
        raise ValueError("too_long")
    return text


def _validate_action_text(action_text: str) -> str:
    text = action_text.strip()
    if not text:
        raise ValueError("Action cannot be empty.")
    if len(text) > settings.max_action_chars:
        raise ValueError("too_long")
    return text


def _thought_query(db: Session, user_id: UUID, thought_id: int) -> Thought | None:
    return db.scalar(
        select(Thought)
        .where(Thought.id == thought_id, Thought.anonymous_user_id == user_id)
        .options(selectinload(Thought.action))
    )


def thought_to_dict(thought: Thought) -> dict:
    action = thought.action
    revisit = thought.revisit_at.isoformat() if thought.revisit_at else None
    return {
        "id": thought.id,
        "content": thought.content,
        "category": thought.category,
        "status": thought.status,
        "created_at": thought.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": thought.updated_at.isoformat().replace("+00:00", "Z"),
        "revisit_at": revisit,
        "action": (
            {
                "id": action.id,
                "action_text": action.action_text,
                "completed": action.completed,
                "created_at": action.created_at.isoformat().replace("+00:00", "Z"),
                "completed_at": (
                    action.completed_at.isoformat().replace("+00:00", "Z")
                    if action.completed_at
                    else None
                ),
            }
            if action
            else None
        ),
    }


def create_anonymous_user(db: Session, user_id: UUID) -> AnonymousUser:
    now = utc_now()
    user = AnonymousUser(id=user_id, created_at=now, last_seen_at=now)
    db.add(user)
    db.commit()
    return user


def touch_last_seen(db: Session, user: AnonymousUser) -> None:
    now = utc_now()
    last_seen = ensure_utc(user.last_seen_at)
    if (now - last_seen).total_seconds() < 3600:
        return
    user.last_seen_at = now
    db.commit()


def create_thought(db: Session, user_id: UUID, content: str) -> int:
    text = _validate_thought_text(content)
    now = utc_now()
    thought = Thought(
        anonymous_user_id=user_id,
        content=text,
        status="new",
        created_at=now,
        updated_at=now,
    )
    db.add(thought)
    db.commit()
    db.refresh(thought)
    return thought.id


def get_thought(db: Session, user_id: UUID, thought_id: int) -> dict | None:
    thought = _thought_query(db, user_id, thought_id)
    if thought is None:
        return None
    return thought_to_dict(thought)


def list_active_inbox_thoughts(db: Session, user_id: UUID) -> list[dict]:
    today = date.today()
    rows = db.scalars(
        select(Thought)
        .where(
            Thought.anonymous_user_id == user_id,
            or_(
                Thought.status.in_(("new", "keep")),
                and_(
                    Thought.status == "revisit",
                    Thought.revisit_at.is_not(None),
                    Thought.revisit_at <= today,
                ),
            ),
        )
        .order_by(Thought.created_at.desc(), Thought.id.desc())
    ).all()
    return [thought_to_dict(row) for row in rows]


def list_thoughts_by_status(db: Session, user_id: UUID, status: str) -> list[dict]:
    rows = db.scalars(
        select(Thought)
        .where(Thought.anonymous_user_id == user_id, Thought.status == status)
        .order_by(Thought.created_at.desc(), Thought.id.desc())
    ).all()
    return [thought_to_dict(row) for row in rows]


def set_category(db: Session, user_id: UUID, thought_id: int, category: str | None) -> None:
    if category is not None and category not in CATEGORIES:
        raise ValueError("Unknown category.")
    thought = _thought_query(db, user_id, thought_id)
    if thought is None:
        raise LookupError("Thought not found.")
    thought.category = category
    thought.updated_at = utc_now()
    db.commit()


def save_action(db: Session, user_id: UUID, thought_id: int, action_text: str) -> None:
    text = _validate_action_text(action_text)
    thought = _thought_query(db, user_id, thought_id)
    if thought is None:
        raise LookupError("Thought not found.")

    now = utc_now()
    if thought.action is None:
        thought.action = Action(
            thought_id=thought.id,
            action_text=text,
            completed=False,
            created_at=now,
        )
    else:
        thought.action.action_text = text
        thought.action.completed = False
        thought.action.created_at = now
        thought.action.completed_at = None

    thought.status = "action"
    thought.revisit_at = None
    thought.updated_at = now
    db.commit()


def list_revisit_thoughts(db: Session, user_id: UUID) -> list[dict]:
    rows = db.scalars(
        select(Thought)
        .where(
            Thought.anonymous_user_id == user_id,
            Thought.status == "revisit",
            Thought.revisit_at.is_not(None),
        )
        .order_by(Thought.revisit_at.asc(), Thought.created_at.desc(), Thought.id.desc())
    ).all()
    return [thought_to_dict(row) for row in rows]


def revisit_now(db: Session, user_id: UUID, thought_id: int) -> None:
    thought = _thought_query(db, user_id, thought_id)
    if thought is None:
        raise LookupError("Thought not found.")
    thought.status = "new"
    thought.revisit_at = None
    thought.updated_at = utc_now()
    db.commit()


def schedule_revisit(db: Session, user_id: UUID, thought_id: int, revisit_on: date) -> None:
    if revisit_on < date.today():
        raise ValueError("past_date")
    thought = _thought_query(db, user_id, thought_id)
    if thought is None:
        raise LookupError("Thought not found.")
    thought.status = "revisit"
    thought.revisit_at = revisit_on
    thought.updated_at = utc_now()
    db.commit()


def mark_keep(db: Session, user_id: UUID, thought_id: int) -> None:
    thought = _thought_query(db, user_id, thought_id)
    if thought is None:
        raise LookupError("Thought not found.")
    thought.status = "keep"
    thought.revisit_at = None
    thought.updated_at = utc_now()
    db.commit()


def mark_let_go(db: Session, user_id: UUID, thought_id: int) -> None:
    thought = _thought_query(db, user_id, thought_id)
    if thought is None:
        raise LookupError("Thought not found.")
    thought.status = "let_go"
    thought.revisit_at = None
    thought.updated_at = utc_now()
    db.commit()


def mark_resolved(db: Session, user_id: UUID, thought_id: int) -> None:
    thought = _thought_query(db, user_id, thought_id)
    if thought is None:
        raise LookupError("Thought not found.")
    thought.status = "resolved"
    thought.revisit_at = None
    thought.updated_at = utc_now()
    db.commit()


def list_open_actions(db: Session, user_id: UUID) -> list[dict]:
    rows = db.execute(
        select(
            Action.id.label("action_id"),
            Action.action_text,
            Action.created_at.label("action_created_at"),
            Thought.id.label("thought_id"),
            Thought.content.label("thought_content"),
        )
        .join(Thought, Thought.id == Action.thought_id)
        .where(
            Thought.anonymous_user_id == user_id,
            Thought.status == "action",
            Action.completed.is_(False),
        )
        .order_by(Action.created_at.desc(), Action.id.desc())
    ).all()
    return [
        {
            "action_id": row.action_id,
            "action_text": row.action_text,
            "action_created_at": row.action_created_at.isoformat().replace("+00:00", "Z"),
            "thought_id": row.thought_id,
            "thought_content": row.thought_content,
        }
        for row in rows
    ]


def complete_action(db: Session, user_id: UUID, action_id: int) -> None:
    row = db.execute(
        select(Action, Thought)
        .join(Thought, Thought.id == Action.thought_id)
        .where(Action.id == action_id, Thought.anonymous_user_id == user_id)
    ).first()
    if row is None:
        raise LookupError("Action not found.")
    action, thought = row
    if action.completed:
        return
    now = utc_now()
    action.completed = True
    action.completed_at = now
    thought.status = "resolved"
    thought.updated_at = now
    db.commit()


def delete_all_for_user(db: Session, user_id: UUID) -> None:
    db.execute(delete(Thought).where(Thought.anonymous_user_id == user_id))
    db.execute(delete(AnonymousUser).where(AnonymousUser.id == user_id))
    db.commit()


def weekly_reflection_stats(db: Session, user_id: UUID) -> dict:
    week_start, week_end = current_week_bounds_utc()
    start_dt = ensure_utc(datetime.fromisoformat(week_start.replace("Z", "+00:00")))
    end_dt = ensure_utc(datetime.fromisoformat(week_end.replace("Z", "+00:00")))

    captured = db.scalar(
        select(func.count())
        .select_from(Thought)
        .where(
            Thought.anonymous_user_id == user_id,
            Thought.created_at >= start_dt,
            Thought.created_at <= end_dt,
        )
    )
    converted = db.scalar(
        select(func.count())
        .select_from(Action)
        .join(Thought, Thought.id == Action.thought_id)
        .where(
            Thought.anonymous_user_id == user_id,
            Action.created_at >= start_dt,
            Action.created_at <= end_dt,
        )
    )
    completed = db.scalar(
        select(func.count())
        .select_from(Action)
        .join(Thought, Thought.id == Action.thought_id)
        .where(
            Thought.anonymous_user_id == user_id,
            Action.completed_at.is_not(None),
            Action.completed_at >= start_dt,
            Action.completed_at <= end_dt,
        )
    )
    let_go = db.scalar(
        select(func.count())
        .select_from(Thought)
        .where(
            Thought.anonymous_user_id == user_id,
            Thought.status == "let_go",
            Thought.updated_at >= start_dt,
            Thought.updated_at <= end_dt,
        )
    )
    waiting = db.scalar(
        select(func.count())
        .select_from(Thought)
        .where(
            Thought.anonymous_user_id == user_id,
            Thought.status == "revisit",
        )
    )
    category_rows = db.execute(
        select(Thought.category, func.count().label("n"))
        .where(
            Thought.anonymous_user_id == user_id,
            Thought.created_at >= start_dt,
            Thought.created_at <= end_dt,
            Thought.category.is_not(None),
        )
        .group_by(Thought.category)
        .order_by(func.count().desc(), Thought.category.asc())
    ).all()

    return {
        "captured": captured or 0,
        "converted_to_actions": converted or 0,
        "completed": completed or 0,
        "let_go": let_go or 0,
        "waiting_revisit": waiting or 0,
        "categories": [{"category": row.category, "n": row.n} for row in category_rows],
    }
