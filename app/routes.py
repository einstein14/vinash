"""Page routes for Vinash pages and form posts."""

from datetime import date
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import display
from app.config import settings
from app.dates import current_week_label, revisit_date_from_form
from app.db import get_db
from app.identity import AnonymousUserId
from app.queries import (
    complete_action,
    create_thought,
    delete_all_for_user,
    get_thought,
    list_active_inbox_thoughts,
    list_open_actions,
    list_revisit_thoughts,
    list_thoughts_by_status,
    mark_keep,
    mark_let_go,
    mark_resolved,
    revisit_now,
    save_action,
    schedule_revisit,
    set_category,
    weekly_reflection_stats,
)

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")

ERROR_MESSAGES = {
    "empty": "Write something first, or come back when you're ready.",
    "empty_action": "Add a small next step, or choose another option.",
    "bad_category": "That category is not available.",
    "bad_date": "Pick when you would like to revisit this.",
    "past_date": "Pick today or a future date.",
    "too_long": "That is a bit too long. Try a shorter note.",
}


def render(request: Request, name: str, current_path: str, **extra) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name=name,
        context={"current_path": current_path, **extra},
    )


def enrich_action(row: dict) -> dict:
    return {
        **row,
        "created_label": display.format_created_at(row["action_created_at"]),
    }


def enrich_thought(row: dict) -> dict:
    action = row.get("action")
    enriched = {k: v for k, v in row.items() if k != "action"}
    enriched["status_label"] = display.STATUS_LABELS.get(
        enriched["status"], enriched["status"]
    )
    enriched["category_label"] = (
        display.CATEGORY_LABELS.get(enriched["category"])
        if enriched.get("category")
        else None
    )
    enriched["created_label"] = display.format_created_at(enriched["created_at"])
    enriched["revisit_label"] = (
        display.format_revisit_date(enriched["revisit_at"])
        if enriched.get("revisit_at")
        else None
    )
    enriched["action_text"] = action["action_text"] if action else ""
    return enriched


def redirect_thought_error(thought_id: int, code: str) -> RedirectResponse:
    return RedirectResponse(
        url=f"/thoughts/{thought_id}?error={code}",
        status_code=303,
    )


def redirect_after_thought_action(return_to: str) -> str:
    if return_to == "revisit":
        return "/revisit"
    return "/inbox"


def load_thought_or_404(db: Session, user_id: UUID, thought_id: int) -> dict:
    row = get_thought(db, user_id, thought_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Thought not found.")
    return row


@router.get("/health")
def health():
    return JSONResponse({"status": "ok"})


@router.get("/")
def home(request: Request, user_id: AnonymousUserId, error: str | None = None):
    message = ERROR_MESSAGES.get(error) if error else None
    return render(request, "home.html", "/", error=error, error_message=message)


@router.post("/thoughts")
def save_thought(
    user_id: AnonymousUserId,
    db: Session = Depends(get_db),
    content: str = Form(default=""),
):
    try:
        create_thought(db, user_id, content)
    except ValueError as exc:
        if str(exc) == "too_long":
            return RedirectResponse(url="/?error=too_long", status_code=303)
        return RedirectResponse(url="/?error=empty", status_code=303)
    return RedirectResponse(url="/inbox", status_code=303)


@router.get("/inbox")
def inbox(
    request: Request,
    user_id: AnonymousUserId,
    db: Session = Depends(get_db),
    view: str | None = None,
):
    if view == "let_go":
        thoughts = [
            enrich_thought(row) for row in list_thoughts_by_status(db, user_id, "let_go")
        ]
        title = "Let go"
        subtitle = "Thoughts you chose not to act on. They are still here if you need them."
    elif view == "resolved":
        thoughts = [
            enrich_thought(row) for row in list_thoughts_by_status(db, user_id, "resolved")
        ]
        title = "Resolved"
        subtitle = "Thoughts you marked as done or finished with."
    else:
        thoughts = [
            enrich_thought(row) for row in list_active_inbox_thoughts(db, user_id)
        ]
        title = "Inbox"
        subtitle = "Thoughts you have not sorted yet, or chose to keep here."

    return render(
        request,
        "inbox.html",
        "/inbox",
        thoughts=thoughts,
        inbox_title=title,
        inbox_subtitle=subtitle,
        inbox_view=view,
    )


@router.get("/thoughts/{thought_id}")
def thought_detail(
    request: Request,
    thought_id: int,
    user_id: AnonymousUserId,
    db: Session = Depends(get_db),
    error: str | None = None,
):
    thought = enrich_thought(load_thought_or_404(db, user_id, thought_id))
    category_options = [
        {"value": key, "label": label} for key, label in display.CATEGORY_LABELS.items()
    ]
    return render(
        request,
        "thought.html",
        "/inbox",
        thought=thought,
        categories=category_options,
        error=error,
        error_message=ERROR_MESSAGES.get(error) if error else None,
        today_iso=date.today().isoformat(),
    )


@router.post("/thoughts/{thought_id}/category")
def update_category(
    thought_id: int,
    user_id: AnonymousUserId,
    db: Session = Depends(get_db),
    category: str = Form(default=""),
):
    value = category.strip() or None
    try:
        set_category(db, user_id, thought_id, value)
    except ValueError:
        return redirect_thought_error(thought_id, "bad_category")
    except LookupError:
        raise HTTPException(status_code=404, detail="Thought not found.")
    return RedirectResponse(url=f"/thoughts/{thought_id}", status_code=303)


@router.post("/thoughts/{thought_id}/action")
def add_action(
    thought_id: int,
    user_id: AnonymousUserId,
    db: Session = Depends(get_db),
    action_text: str = Form(default=""),
):
    try:
        save_action(db, user_id, thought_id, action_text)
    except ValueError as exc:
        code = "too_long" if str(exc) == "too_long" else "empty_action"
        return redirect_thought_error(thought_id, code)
    except LookupError:
        raise HTTPException(status_code=404, detail="Thought not found.")
    return RedirectResponse(url="/actions", status_code=303)


@router.post("/thoughts/{thought_id}/revisit")
def add_revisit(
    thought_id: int,
    user_id: AnonymousUserId,
    db: Session = Depends(get_db),
    preset: str = Form(default=""),
    custom_date: str = Form(default=""),
    return_to: str = Form(default="detail"),
):
    try:
        revisit_on = revisit_date_from_form(preset, custom_date)
        schedule_revisit(db, user_id, thought_id, revisit_on)
    except ValueError as exc:
        code = str(exc) if str(exc) in ERROR_MESSAGES else "bad_date"
        if return_to == "revisit":
            return RedirectResponse(url=f"/revisit?error={code}", status_code=303)
        return redirect_thought_error(thought_id, code)
    except LookupError:
        raise HTTPException(status_code=404, detail="Thought not found.")
    return RedirectResponse(url="/revisit", status_code=303)


@router.post("/thoughts/{thought_id}/revisit-now")
def revisit_now_route(
    thought_id: int,
    user_id: AnonymousUserId,
    db: Session = Depends(get_db),
):
    try:
        revisit_now(db, user_id, thought_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Thought not found.")
    return RedirectResponse(url="/inbox", status_code=303)


@router.post("/thoughts/{thought_id}/keep")
def keep_thought(
    thought_id: int,
    user_id: AnonymousUserId,
    db: Session = Depends(get_db),
):
    try:
        mark_keep(db, user_id, thought_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Thought not found.")
    return RedirectResponse(url="/inbox", status_code=303)


@router.post("/thoughts/{thought_id}/let-go")
def let_go_thought(
    thought_id: int,
    user_id: AnonymousUserId,
    db: Session = Depends(get_db),
    return_to: str = Form(default="inbox"),
):
    try:
        mark_let_go(db, user_id, thought_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Thought not found.")
    return RedirectResponse(
        url=redirect_after_thought_action(return_to),
        status_code=303,
    )


@router.post("/thoughts/{thought_id}/resolve")
def resolve_thought(
    thought_id: int,
    user_id: AnonymousUserId,
    db: Session = Depends(get_db),
    return_to: str = Form(default="inbox"),
):
    try:
        mark_resolved(db, user_id, thought_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Thought not found.")
    return RedirectResponse(
        url=redirect_after_thought_action(return_to),
        status_code=303,
    )


@router.get("/actions")
def actions_page(
    request: Request,
    user_id: AnonymousUserId,
    db: Session = Depends(get_db),
):
    items = [enrich_action(row) for row in list_open_actions(db, user_id)]
    return render(request, "actions.html", "/actions", action_items=items)


@router.post("/actions/{action_id}/complete")
def complete_action_route(
    action_id: int,
    user_id: AnonymousUserId,
    db: Session = Depends(get_db),
):
    try:
        complete_action(db, user_id, action_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Action not found.")
    return RedirectResponse(url="/actions", status_code=303)


@router.get("/revisit")
def revisit_page(
    request: Request,
    user_id: AnonymousUserId,
    db: Session = Depends(get_db),
    error: str | None = None,
):
    thoughts = [enrich_thought(row) for row in list_revisit_thoughts(db, user_id)]
    return render(
        request,
        "revisit.html",
        "/revisit",
        revisit_thoughts=thoughts,
        error=error,
        error_message=ERROR_MESSAGES.get(error) if error else None,
        today_iso=date.today().isoformat(),
    )


@router.get("/reflection")
def reflection_page(
    request: Request,
    user_id: AnonymousUserId,
    db: Session = Depends(get_db),
):
    stats = weekly_reflection_stats(db, user_id)
    category_lines = [
        {
            "label": display.CATEGORY_LABELS.get(row["category"], row["category"]),
            "count": row["n"],
        }
        for row in stats["categories"]
    ]
    return render(
        request,
        "reflection.html",
        "/reflection",
        stats=stats,
        category_lines=category_lines,
        week_label=current_week_label(),
    )


@router.get("/privacy")
def privacy_page(request: Request, user_id: AnonymousUserId):
    return render(request, "privacy.html", "/privacy")


@router.post("/privacy/delete-all")
def privacy_delete_all(
    request: Request,
    user_id: AnonymousUserId,
    db: Session = Depends(get_db),
    confirm: str = Form(default=""),
):
    if confirm != "yes":
        return render(
            request,
            "privacy.html",
            "/privacy",
            error_message="Please confirm before deleting.",
        )
    delete_all_for_user(db, user_id)
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(settings.cookie_name)
    return response
