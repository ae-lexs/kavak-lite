from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from kavak_lite.entrypoints.http.routes.health import router


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with the health router."""
    test_app = FastAPI()
    test_app.include_router(router)

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


def test_health_endpoint(client: TestClient) -> None:
    reponse = client.get("/health")

    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok"}
