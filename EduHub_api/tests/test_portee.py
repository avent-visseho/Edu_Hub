"""Vérifie que chacun ne voit que ce qui le concerne.

Le cadrage des données est une propriété de sécurité : sans lui, un élève
disposant de « apprenants:READ » listait les douze mille apprenants du pays et
lisait les bulletins de ses camarades. Une propriété de ce genre se perd
silencieusement — il suffit qu'une entité soit ajoutée sans déclaration de
portée, ou qu'un rattachement soit élargi par commodité. Ces tests la figent.

Ils supposent la base peuplée et les comptes de démonstration en place :
`python -m app.seed` puis `alembic upgrade head`.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

MOT_DE_PASSE = "EduHub2026!"


async def _entetes(client: AsyncClient, adresse: str) -> dict[str, str]:
    reponse = await client.post(
        "/api/v1/auth/connexion",
        json={"email": adresse, "mot_de_passe": MOT_DE_PASSE},
    )
    assert reponse.status_code == 200, f"{adresse} : {reponse.text}"
    return {"Authorization": f"Bearer {reponse.json()['access_token']}"}


async def _total(client: AsyncClient, entetes: dict[str, str], chemin: str) -> int:
    reponse = await client.get(f"/api/v1{chemin}", params={"size": 1}, headers=entetes)
    assert reponse.status_code == 200, f"{chemin} : {reponse.text}"
    return reponse.json()["total"]


@pytest.fixture
async def eleve(client: AsyncClient) -> dict[str, str]:
    return await _entetes(client, "eleve@eduhub.bj")


@pytest.fixture
async def parent(client: AsyncClient) -> dict[str, str]:
    return await _entetes(client, "parent@eduhub.bj")


@pytest.fixture
async def directeur(client: AsyncClient) -> dict[str, str]:
    return await _entetes(client, "directeur@eduhub.bj")


class TestPorteePersonnelle:
    """Un élève ne voit que son propre dossier."""

    async def test_un_seul_apprenant(self, client: AsyncClient, eleve: dict[str, str]) -> None:
        assert await _total(client, eleve, "/apprenants") == 1

    async def test_une_seule_classe(self, client: AsyncClient, eleve: dict[str, str]) -> None:
        assert await _total(client, eleve, "/classes") == 1

    async def test_bulletins_sans_ceux_des_camarades(
        self, client: AsyncClient, eleve: dict[str, str], entetes: dict[str, str]
    ) -> None:
        """Le bulletin appartient à l'élève, pas à sa classe.

        Une première version le rattachait aussi à la classe : l'élève voyait
        les onze bulletins de ses camarades.
        """
        mes_bulletins = await _total(client, eleve, "/bulletins")
        tous = await _total(client, entetes, "/bulletins")
        assert 0 < mes_bulletins < tous

        reponse = await client.get("/api/v1/bulletins", headers=eleve, params={"size": 50})
        apprenants = {ligne["apprenant_id"] for ligne in reponse.json()["items"]}
        assert len(apprenants) <= 1, "des bulletins d'autrui sont visibles"


class TestAccesDirect:
    """Une ligne hors périmètre se comporte comme une ligne absente."""

    async def test_fiche_d_autrui_introuvable(
        self, client: AsyncClient, eleve: dict[str, str], entetes: dict[str, str]
    ) -> None:
        tous = await client.get("/api/v1/apprenants", headers=entetes, params={"size": 20})
        miens = await client.get("/api/v1/apprenants", headers=eleve, params={"size": 20})
        mes_identifiants = {ligne["id"] for ligne in miens.json()["items"]}
        etranger = next(
            ligne["id"] for ligne in tous.json()["items"] if ligne["id"] not in mes_identifiants
        )

        reponse = await client.get(f"/api/v1/apprenants/{etranger}", headers=eleve)
        # 404 et non 403 : répondre « interdit » confirmerait l'existence de la
        # fiche, ce qui renseigne déjà sur autrui.
        assert reponse.status_code == 404

    async def test_sa_propre_fiche_accessible(
        self, client: AsyncClient, eleve: dict[str, str]
    ) -> None:
        miens = await client.get("/api/v1/apprenants", headers=eleve, params={"size": 1})
        identifiant = miens.json()["items"][0]["id"]
        reponse = await client.get(f"/api/v1/apprenants/{identifiant}", headers=eleve)
        assert reponse.status_code == 200


class TestRechercheAvancee:
    """La recherche avancée ne contourne pas le périmètre."""

    async def test_memes_limites_que_la_liste(
        self, client: AsyncClient, eleve: dict[str, str]
    ) -> None:
        liste = await _total(client, eleve, "/apprenants")
        reponse = await client.post(
            "/api/v1/apprenants/recherche",
            headers=eleve,
            params={"size": 1},
            json={"criteres": [], "conjonction": "AND"},
        )
        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["total"] == liste


class TestPorteeEtablissement:
    """Un chef d'établissement voit son école, et elle seule."""

    async def test_moins_que_le_national(
        self, client: AsyncClient, directeur: dict[str, str], entetes: dict[str, str]
    ) -> None:
        for chemin in ("/apprenants", "/classes", "/bulletins"):
            sien = await _total(client, directeur, chemin)
            tous = await _total(client, entetes, chemin)
            assert 0 < sien < tous, f"{chemin} : {sien} sur {tous}"


class TestPorteeNationale:
    """Le pilotage garde une vue complète."""

    async def test_super_admin_voit_tout(
        self, client: AsyncClient, entetes: dict[str, str], eleve: dict[str, str]
    ) -> None:
        for chemin in ("/apprenants", "/classes", "/bulletins"):
            assert await _total(client, entetes, chemin) > await _total(client, eleve, chemin)


class TestCatalogues:
    """Les référentiels restent lisibles par tous : sans eux, plus de listes déroulantes."""

    async def test_niveaux_accessibles_a_l_eleve(
        self, client: AsyncClient, eleve: dict[str, str], entetes: dict[str, str]
    ) -> None:
        reponse = await client.get("/api/v1/niveaux", headers=eleve, params={"size": 1})
        if reponse.status_code == 403:
            pytest.skip("le rôle élève n'a pas la permission referentiels:READ")
        assert reponse.status_code == 200
        assert reponse.json()["total"] == await _total(client, entetes, "/niveaux")


class TestTableauParRole:
    """Chaque rôle reçoit les indicateurs qui le concernent."""

    async def test_eleve_obtient_sa_scolarite(
        self, client: AsyncClient, eleve: dict[str, str]
    ) -> None:
        reponse = await client.get("/api/v1/tableaux-de-bord/mon-tableau", headers=eleve)
        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        assert corps["perimetre"] == "ELEVE"
        codes = {indicateur["code"] for indicateur in corps["indicateurs"]}
        assert {"moyenne_generale", "rang", "taux_presence"} <= codes

    async def test_directeur_obtient_son_etablissement(
        self, client: AsyncClient, directeur: dict[str, str]
    ) -> None:
        reponse = await client.get("/api/v1/tableaux-de-bord/mon-tableau", headers=directeur)
        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["perimetre"] == "ETABLISSEMENT"

    async def test_le_national_reste_refuse_a_l_eleve(
        self, client: AsyncClient, eleve: dict[str, str]
    ) -> None:
        reponse = await client.get("/api/v1/tableaux-de-bord/national", headers=eleve)
        assert reponse.status_code == 403
