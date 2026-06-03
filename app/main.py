from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import Settings
from app.routers import projects, nodes, edges, documents, sync, snapshots, public, auth


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    app = FastAPI(title="Oricalcum API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_urls,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
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
    app.include_router(documents.router, prefix=prefix)
    app.include_router(sync.router, prefix=prefix)
    app.include_router(snapshots.router, prefix=prefix)
    app.include_router(public.router, prefix=prefix)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
