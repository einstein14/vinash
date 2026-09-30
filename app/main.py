"""Vinash web app."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.db import init_db
from app.identity import AnonymousUserMiddleware
from app.routes import router

APP_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=APP_DIR / "templates")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Vinash",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
app.add_middleware(AnonymousUserMiddleware)
app.include_router(router)


@app.exception_handler(HTTPException)
async def http_exception_page(request: Request, exc: HTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"title": "Not found", "message": "That page or thought is not here."},
            status_code=404,
        )
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={"title": "Something went wrong", "message": "Please try again."},
        status_code=exc.status_code,
    )


@app.exception_handler(404)
async def not_found_page(request: Request, _exc):
    if request.url.path.startswith("/static"):
        return HTMLResponse("Not found", status_code=404)
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={"title": "Not found", "message": "That page or thought is not here."},
        status_code=404,
    )


@app.exception_handler(500)
async def server_error_page(request: Request, _exc):
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "title": "Something went wrong",
            "message": "Please try again in a moment.",
        },
        status_code=500,
    )
