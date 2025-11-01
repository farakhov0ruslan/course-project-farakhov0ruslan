from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse, Response

from app.routers import notes as notes_api
from app.routers import tags as tags_api
from infrastructure.db import init_db
from utils_library.logger import setup_logging

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Study Notes API", version="0.1.0", lifespan=lifespan)

app.include_router(notes_api.router)
app.include_router(tags_api.router)
app.add_middleware(CorrelationIdMiddleware, header_name="X-Request-ID")  # noqa


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> Response:
    # Problem Details (RFC 9457 совместим с 7807)
    from asgi_correlation_id.context import correlation_id

    body = {
        "type": "about:blank",
        "title": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
        "status": exc.status_code,
        "detail": None if isinstance(exc.detail, str) else str(exc.detail),
        "instance": str(request.url),
        "correlation_id": correlation_id.get(),
    }
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> Response:
    from asgi_correlation_id.context import correlation_id

    body = {
        "type": "about:blank",
        "title": "Unprocessable Entity",
        "status": 422,
        "detail": "Request validation failed",
        "errors": exc.errors(),
        "instance": str(request.url),
        "correlation_id": correlation_id.get(),
    }
    return JSONResponse(status_code=422, content=body)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    from asgi_correlation_id.context import correlation_id

    body = {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "Unexpected server error",
        "instance": str(request.url),
        "correlation_id": correlation_id.get(),
    }
    return JSONResponse(status_code=500, content=body)


@app.get("/health")
def health():
    return {"status": "ok"}
