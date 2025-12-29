"""
Unit tests for FastAPI application setup and configuration.

This test suite verifies the application structure and wiring:
- build_app() creates properly configured FastAPI instance
- Application metadata (title, version, docs URLs)
- Router registration (health, cars with correct prefixes)
- OpenAPI schema generation
- Documentation endpoints availability

Tests verify the app follows the structure defined in the codebase without
requiring external dependencies.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from kavak_lite.entrypoints.http.app import build_app


# ==============================================================================
# Application Creation
# ==============================================================================


def test_build_app_returns_fastapi_instance() -> None:
    """build_app() returns a FastAPI application instance."""
    app = build_app()
    assert isinstance(app, FastAPI)


def test_build_app_creates_new_instance_each_call() -> None:
    """build_app() creates a new app instance for each call (not cached)."""
    app1 = build_app()
    app2 = build_app()

    # Different instances
    assert app1 is not app2


# ==============================================================================
# Application Metadata
# ==============================================================================


def test_app_has_correct_title() -> None:
    """Application has correct title."""
    app = build_app()
    assert app.title == "Kavak Lite API"


def test_app_has_correct_version() -> None:
    """Application has correct version."""
    app = build_app()
    assert app.version == "0.1.0"


def test_app_has_description() -> None:
    """Application has description."""
    app = build_app()
    assert app.description is not None
    assert len(app.description) > 0
    assert "Car marketplace API" in app.description


def test_app_has_contact_info() -> None:
    """Application has contact information."""
    app = build_app()
    assert app.contact is not None
    assert "name" in app.contact
    assert app.contact["name"] == "Kavak Lite Team"
    assert "email" in app.contact
    assert app.contact["email"] == "dev@kavak-lite.com"


def test_app_has_license_info() -> None:
    """Application has license information."""
    app = build_app()
    assert app.license_info is not None
    assert "name" in app.license_info
    assert app.license_info["name"] == "Proprietary"


# ==============================================================================
# Documentation URLs
# ==============================================================================


def test_app_has_swagger_ui_enabled() -> None:
    """Application has Swagger UI enabled at /docs."""
    app = build_app()
    assert app.docs_url == "/docs"


def test_app_has_redoc_enabled() -> None:
    """Application has ReDoc enabled at /redoc."""
    app = build_app()
    assert app.redoc_url == "/redoc"


def test_app_has_openapi_schema_endpoint() -> None:
    """Application has OpenAPI schema at /openapi.json."""
    app = build_app()
    assert app.openapi_url == "/openapi.json"


def test_app_documentation_endpoints_are_accessible() -> None:
    """Documentation endpoints are accessible."""
    app = build_app()
    client = TestClient(app)

    # Swagger UI
    response = client.get("/docs")
    assert response.status_code == 200

    # ReDoc
    response = client.get("/redoc")
    assert response.status_code == 200

    # OpenAPI schema
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


# ==============================================================================
# Router Registration
# ==============================================================================


def test_app_includes_health_router() -> None:
    """Application includes health router."""
    app = build_app()
    client = TestClient(app)

    # Health endpoint should be accessible
    response = client.get("/health")
    assert response.status_code == 200


def test_app_includes_cars_router_with_v1_prefix() -> None:
    """Application includes cars router with /v1 prefix."""
    app = build_app()

    # Verify via OpenAPI schema (doesn't trigger dependencies)
    openapi_schema = app.openapi()
    paths = openapi_schema["paths"]

    # Cars endpoint should NOT be at /cars
    assert "/cars" not in paths

    # Should be at /v1/cars
    assert "/v1/cars" in paths


def test_app_has_routes_registered() -> None:
    """Application has routes registered in OpenAPI schema."""
    app = build_app()

    # Get OpenAPI schema
    openapi_schema = app.openapi()

    # Verify paths are registered
    assert "paths" in openapi_schema
    paths = openapi_schema["paths"]

    # Health endpoint
    assert "/health" in paths

    # Cars endpoint with /v1 prefix
    assert "/v1/cars" in paths


# ==============================================================================
# OpenAPI Schema Structure
# ==============================================================================


def test_app_openapi_schema_has_required_fields() -> None:
    """OpenAPI schema has all required fields."""
    app = build_app()
    schema = app.openapi()

    # Required OpenAPI fields
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema

    # Info object
    assert "title" in schema["info"]
    assert "version" in schema["info"]
    assert schema["info"]["title"] == "Kavak Lite API"
    assert schema["info"]["version"] == "0.1.0"


def test_app_openapi_schema_includes_contact() -> None:
    """OpenAPI schema includes contact information."""
    app = build_app()
    schema = app.openapi()

    assert "info" in schema
    assert "contact" in schema["info"]
    assert schema["info"]["contact"]["name"] == "Kavak Lite Team"


def test_app_openapi_schema_includes_license() -> None:
    """OpenAPI schema includes license information."""
    app = build_app()
    schema = app.openapi()

    assert "info" in schema
    assert "license" in schema["info"]
    assert schema["info"]["license"]["name"] == "Proprietary"


def test_app_openapi_schema_documents_health_endpoint() -> None:
    """OpenAPI schema documents /health endpoint."""
    app = build_app()
    schema = app.openapi()

    assert "/health" in schema["paths"]
    health_path = schema["paths"]["/health"]

    # Should have GET method
    assert "get" in health_path

    # Should have tags
    assert "tags" in health_path["get"]
    assert "health" in health_path["get"]["tags"]


def test_app_openapi_schema_documents_cars_endpoint() -> None:
    """OpenAPI schema documents /v1/cars endpoint."""
    app = build_app()
    schema = app.openapi()

    assert "/v1/cars" in schema["paths"]
    cars_path = schema["paths"]["/v1/cars"]

    # Should have GET method
    assert "get" in cars_path

    # Should have tags
    assert "tags" in cars_path["get"]
    assert "Cars" in cars_path["get"]["tags"]

    # Should have summary
    assert "summary" in cars_path["get"]
    assert cars_path["get"]["summary"] == "Search car catalog"

    # Should have parameters (query params)
    assert "parameters" in cars_path["get"]
    params = cars_path["get"]["parameters"]
    param_names = [p["name"] for p in params]

    # Verify pagination params
    assert "offset" in param_names
    assert "limit" in param_names

    # Verify filter params
    assert "brand" in param_names
    assert "model" in param_names


# ==============================================================================
# Route Accessibility
# ==============================================================================


def test_health_endpoint_responds() -> None:
    """Health endpoint returns successful response."""
    app = build_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cars_endpoint_exists_at_correct_path() -> None:
    """Cars endpoint exists at /v1/cars (not at /cars)."""
    app = build_app()

    # Verify via OpenAPI schema (doesn't trigger dependencies)
    openapi_schema = app.openapi()
    paths = openapi_schema["paths"]

    # Should NOT exist at /cars
    assert "/cars" not in paths

    # Should exist at /v1/cars
    assert "/v1/cars" in paths


def test_app_returns_404_for_unknown_routes() -> None:
    """Application returns 404 for unknown routes."""
    app = build_app()
    client = TestClient(app)

    response = client.get("/unknown")
    assert response.status_code == 404

    response = client.get("/v1/unknown")
    assert response.status_code == 404


# ==============================================================================
# Application Structure
# ==============================================================================


def test_app_module_exports_app_instance() -> None:
    """App module exports 'app' instance at module level."""
    from kavak_lite.entrypoints.http.app import app

    assert isinstance(app, FastAPI)


def test_module_level_app_is_from_build_app() -> None:
    """Module-level app instance is created via build_app()."""
    from kavak_lite.entrypoints.http.app import app

    # Should have same configuration as build_app()
    assert app.title == "Kavak Lite API"
    assert app.version == "0.1.0"
    assert app.docs_url == "/docs"
