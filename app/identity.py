"""Login-free anonymous browser identity via cookie."""

import uuid
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings
from app.db import SessionLocal
from app.models import AnonymousUser
from app.queries import create_anonymous_user, touch_last_seen


def _parse_cookie(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


class AnonymousUserMiddleware(BaseHTTPMiddleware):
    """Attach anonymous_user_id to each request and set cookie when needed."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        user_id = _parse_cookie(request.cookies.get(settings.cookie_name))
        new_cookie = False

        with SessionLocal() as db:
            user = db.get(AnonymousUser, user_id) if user_id else None
            if user is None:
                user_id = uuid.uuid4()
                create_anonymous_user(db, user_id)
                new_cookie = True
            else:
                touch_last_seen(db, user)

        request.state.anonymous_user_id = user_id
        response: Response = await call_next(request)

        if new_cookie:
            response.set_cookie(
                key=settings.cookie_name,
                value=str(user_id),
                max_age=settings.cookie_max_age,
                httponly=True,
                secure=settings.cookie_secure,
                samesite="lax",
            )
        return response


def get_anonymous_user_id(request: Request) -> UUID:
    return request.state.anonymous_user_id


AnonymousUserId = Annotated[UUID, Depends(get_anonymous_user_id)]
