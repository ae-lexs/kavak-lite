from fastapi import FastAPI


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

    app.include_router(health_router, prefix="/v1")

    return app


app = build_app()
