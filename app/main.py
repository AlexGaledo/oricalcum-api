import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import Settings
from app.mcp import mcp
from app.routers import (
    projects, nodes, edges, nodespaces, documents, sync, snapshots, public, auth,
    calendar_events, secrets, chat, storage,
)

logger = logging.getLogger("oricalcum")


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Streamable-http ASGI app exposing the assistant's MCP tools. Mounted at
    # /mcp -> reachable at /mcp/ . Its lifespan must run inside FastAPI's so
    # FastMCP's session manager starts.
    mcp_app = mcp.http_app(path="/")

    app = FastAPI(title="Oricalcum API", version="1.0.0", lifespan=mcp_app.lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_urls,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        logger.info(
            "%s %s -> %s  (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed * 1000,
        )
        return response

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": {"code": "INTERNAL_ERROR", "message": str(exc)},
            },
        )

    prefix = settings.api_prefix
    app.include_router(auth.router, prefix=prefix)
    app.include_router(projects.router, prefix=prefix)
    app.include_router(nodes.router, prefix=prefix)
    app.include_router(edges.router, prefix=prefix)
    app.include_router(nodespaces.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(sync.router, prefix=prefix)
    app.include_router(snapshots.router, prefix=prefix)
    app.include_router(public.router, prefix=prefix)
    app.include_router(calendar_events.router, prefix=prefix)
    app.include_router(secrets.router, prefix=prefix)
    app.include_router(chat.router, prefix=prefix)
    app.include_router(storage.router, prefix=prefix)

    # In-process MCP server the assistant's agent connects to over loopback HTTP.
    app.mount("/mcp", mcp_app)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
