"""Fixtures partagées par les tests.

Les tests d'intégration supposent une base migrée et peuplée :
`make reseed` ou `python -m app.seed --echelle tiny`.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import engine
from app.main import app


@pytest.fixture(autouse=True)
async def _pool_isole():
    """Referme le pool entre deux tests.

    Chaque test s'exécute dans sa propre boucle d'événements ; une connexion
    ouverte dans la boucle précédente ne peut pas y être réutilisée.
    """
    yield
    await engine.dispose()


@pytest.fixture
async def client() -> AsyncClient:
    """Client HTTP branché directement sur l'application, sans serveur."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def jeton(client: AsyncClient) -> str:
    """Jeton d'accès du super administrateur du jeu de démonstration."""
    reponse = await client.post(
        "/api/v1/auth/connexion",
        json={"email": "super.admin@eduhub.bj", "mot_de_passe": "EduHub2026!"},
    )
    assert reponse.status_code == 200, reponse.text
    return reponse.json()["access_token"]


@pytest.fixture
def entetes(jeton: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton}"}
