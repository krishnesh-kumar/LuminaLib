from fastapi import FastAPI
from app.core.logging import configure_logging
from app.core.config import settings
from app.api import health, auth, books, borrows, reviews, analysis, recommendations, metrics, files


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.APP_NAME)

    app.include_router(health.router, prefix=settings.API_PREFIX)
    app.include_router(auth.router, prefix=settings.API_PREFIX)
    app.include_router(books.router, prefix=settings.API_PREFIX)
    app.include_router(borrows.router, prefix=settings.API_PREFIX)
    app.include_router(reviews.router, prefix=settings.API_PREFIX)
    app.include_router(analysis.router, prefix=settings.API_PREFIX)
    app.include_router(recommendations.router, prefix=settings.API_PREFIX)
    app.include_router(files.router, prefix=settings.API_PREFIX)
    app.include_router(metrics.router)

    @app.get("/")
    def root():
        return {"message": f"{settings.APP_NAME} backend"}

    return app


app = create_app()
