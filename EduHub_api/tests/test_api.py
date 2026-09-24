"""Tests d'intégration de l'API.

Ils supposent une base migrée et peuplée : `make reseed` ou
`python -m app.seed --echelle tiny`.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_sonde_de_sante(client: AsyncClient):
    reponse = await client.get("/health")
    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok"}


async def test_connexion_refuse_un_mot_de_passe_errone(client: AsyncClient):
    reponse = await client.post(
        "/api/v1/auth/connexion",
        json={"email": "super.admin@eduhub.bj", "mot_de_passe": "mauvais"},
    )
    assert reponse.status_code == 401
    assert reponse.json()["error"]["code"] == "identifiants_invalides"


async def test_route_protegee_sans_jeton(client: AsyncClient):
    reponse = await client.get("/api/v1/apprenants")
    assert reponse.status_code == 401


async def test_profil_expose_roles_et_permissions(client: AsyncClient, entetes: dict[str, str]):
    reponse = await client.get("/api/v1/auth/moi", headers=entetes)
    assert reponse.status_code == 200
    charge = reponse.json()
    assert "SUPER_ADMIN" in charge["roles"]
    assert len(charge["permissions"]) > 100
    assert charge["niveau_scope"] == "NATIONAL"


async def test_liste_paginee(client: AsyncClient, entetes: dict[str, str]):
    reponse = await client.get("/api/v1/apprenants?size=5", headers=entetes)
    assert reponse.status_code == 200
    charge = reponse.json()
    assert len(charge["items"]) <= 5
    assert charge["total"] >= len(charge["items"])
    assert charge["page"] == 1


async def test_recherche_avancee_filtre_reellement(client: AsyncClient, entetes: dict[str, str]):
    reponse = await client.post(
        "/api/v1/recherche/avancee",
        headers=entetes,
        json={
            "entite": "apprenants",
            "criteres": [{"champ": "sexe", "operateur": "eq", "valeur": "FEMININ"}],
            "taille": 5,
        },
    )
    assert reponse.status_code == 200
    charge = reponse.json()
    assert all(ligne["sexe"] == "FEMININ" for ligne in charge["lignes"])


async def test_recherche_avancee_rejette_un_champ_inconnu(
    client: AsyncClient, entetes: dict[str, str]
):
    reponse = await client.post(
        "/api/v1/recherche/avancee",
        headers=entetes,
        json={
            "entite": "apprenants",
            "criteres": [{"champ": "champ_inexistant", "operateur": "eq", "valeur": 1}],
        },
    )
    assert reponse.status_code == 422


async def test_langage_naturel_produit_des_filtres(client: AsyncClient, entetes: dict[str, str]):
    reponse = await client.post(
        "/api/v1/recherche/langage-naturel",
        headers=entetes,
        json={
            "question": "Élèves ayant une moyenne générale supérieure ou égale à 15",
            "taille": 3,
        },
    )
    assert reponse.status_code == 200
    charge = reponse.json()
    assert charge["entite"] == "apprenants"
    assert any(filtre["champ"] == "moyenne_generale" for filtre in charge["filtres"])
    assert charge["resultat"] is not None


async def test_tableau_de_bord_national(client: AsyncClient, entetes: dict[str, str]):
    reponse = await client.get("/api/v1/tableaux-de-bord/national", headers=entetes)
    assert reponse.status_code == 200
    charge = reponse.json()
    codes = {indicateur["code"] for indicateur in charge["indicateurs"]}
    assert {"apprenants", "enseignants", "etablissements", "taux_reussite"} <= codes


async def test_verification_document_inconnu(client: AsyncClient):
    reponse = await client.get("/api/v1/public/verification/CODEINEXISTANT00")
    assert reponse.status_code == 200
    assert reponse.json()["valide"] is False


async def test_resultat_public_introuvable(client: AsyncClient):
    reponse = await client.get("/api/v1/public/resultats", params={"numero": "INEXISTANT"})
    assert reponse.status_code == 404
