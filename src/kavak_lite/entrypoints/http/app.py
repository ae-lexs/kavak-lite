from fastapi import FastAPI

from kavak_lite.entrypoints.http.exception_handlers import register_exception_handlers
from kavak_lite.entrypoints.http.routes.cars import router as cars_router
from kavak_lite.entrypoints.http.routes.health import router as health_router


def build_app() -> FastAPI:
    app = FastAPI(
        title="Kavak Lite API",
        description="""
        Car marketplace API for browsing, searching, and financing vehicles.

        ## Features
        - Search car catalog with filters
        - Calculate financing plans
        - Get car details

        ## Authentication
        Currently no authentication required (development phase).

        ## Rate Limiting
        No rate limits currently enforced.

        ## Error Handling
        All errors return structured JSON responses with error codes.
        See the error response schemas in the API documentation.
        """,
        version="0.1.0",
        docs_url="/docs",  # Swagger UI
        redoc_url="/redoc",  # ReDoc alternative
        openapi_url="/openapi.json",  # OpenAPI schema
        contact={
            "name": "Kavak Lite Team",
            "email": "dev@kavak-lite.com",
        },
        license_info={
            "name": "Proprietary",
        },
    )

    # Register global exception handlers
    register_exception_handlers(app)

    # Register routers
    app.include_router(health_router)
    app.include_router(cars_router, prefix="/v1")

    return app


app = build_app()
