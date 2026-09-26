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


class TestSousRessources:
    """Les points d'entrée qui prolongent une fiche héritent du même cadrage.

    Ils ne passent pas par la fabrique CRUD et n'héritent donc d'aucune portée :
    chacun doit vérifier le périmètre lui-même. « notes:READ » ouvrait les
    moyennes de n'importe quel élève du pays, et « presences:READ » l'assiduité
    de n'importe quelle classe.
    """

    async def test_moyennes_d_un_autre_eleve_introuvables(
        self, client: AsyncClient, eleve: dict[str, str], entetes: dict[str, str]
    ) -> None:
        tous = await client.get("/api/v1/apprenants", headers=entetes, params={"size": 20})
        miens = await client.get("/api/v1/apprenants", headers=eleve, params={"size": 20})
        identifiants = {ligne["id"] for ligne in miens.json()["items"]}
        etranger = next(
            ligne["id"] for ligne in tous.json()["items"] if ligne["id"] not in identifiants
        )
        sien = next(iter(identifiants))

        assert (
            await client.get(f"/api/v1/apprenants/{sien}/moyennes", headers=eleve)
        ).status_code == 200
        assert (
            await client.get(f"/api/v1/apprenants/{etranger}/moyennes", headers=eleve)
        ).status_code == 404

    async def test_assiduite_d_une_classe_etrangere_introuvable(
        self, client: AsyncClient, directeur: dict[str, str], entetes: dict[str, str]
    ) -> None:
        toutes = await client.get("/api/v1/classes", headers=entetes, params={"size": 20})
        siennes = await client.get("/api/v1/classes", headers=directeur, params={"size": 20})
        identifiants = {ligne["id"] for ligne in siennes.json()["items"]}
        etrangere = next(
            ligne["id"] for ligne in toutes.json()["items"] if ligne["id"] not in identifiants
        )
        sienne = next(iter(identifiants))

        for suffixe in ("assiduite", "seances"):
            assert (
                await client.get(f"/api/v1/classes/{sienne}/{suffixe}", headers=directeur)
            ).status_code == 200
            assert (
                await client.get(f"/api/v1/classes/{etrangere}/{suffixe}", headers=directeur)
            ).status_code == 404


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

    async def test_vues_nationales_reservees_au_pilotage(
        self,
        client: AsyncClient,
        eleve: dict[str, str],
        directeur: dict[str, str],
        entetes: dict[str, str],
    ) -> None:
        """Le périmètre décide, pas la seule permission.

        Un chef d'établissement porte « analytics:READ » parce qu'il lui faut
        les statistiques de ses classes ; cela ne lui donne pas vocation à
        consulter les chiffres du pays.
        """
        for vue in ("/national", "/territoires"):
            chemin = f"/api/v1/tableaux-de-bord{vue}"
            assert (await client.get(chemin, headers=entetes)).status_code == 200
            assert (await client.get(chemin, headers=directeur)).status_code == 403
            assert (await client.get(chemin, headers=eleve)).status_code == 403

    async def test_statistiques_d_une_classe_etrangere_introuvables(
        self, client: AsyncClient, directeur: dict[str, str], entetes: dict[str, str]
    ) -> None:
        """La permission ouvre la fonction, elle ne désigne pas les classes.

        Sans cette vérification, un chef d'établissement lisait les
        statistiques de n'importe quelle classe du pays.
        """
        bulletins = await client.get("/api/v1/bulletins", headers=entetes, params={"size": 1})
        periode = bulletins.json()["items"][0]["periode_id"]

        toutes = await client.get("/api/v1/classes", headers=entetes, params={"size": 20})
        siennes = await client.get("/api/v1/classes", headers=directeur, params={"size": 20})
        identifiants = {ligne["id"] for ligne in siennes.json()["items"]}
        etrangere = next(
            ligne["id"] for ligne in toutes.json()["items"] if ligne["id"] not in identifiants
        )

        sienne = next(iter(identifiants))
        parametres = {"periode_id": periode}
        assert (
            await client.get(
                f"/api/v1/classes/{sienne}/statistiques", headers=directeur, params=parametres
            )
        ).status_code == 200
        assert (
            await client.get(
                f"/api/v1/classes/{etrangere}/statistiques", headers=directeur, params=parametres
            )
        ).status_code == 404

    async def test_graphiques_propres_a_chaque_portee(
        self, client: AsyncClient, eleve: dict[str, str], directeur: dict[str, str]
    ) -> None:
        """Les graphiques diffèrent autant que les indicateurs.

        L'élève suit sa progression, l'établissement observe sa répartition :
        rien ne justifierait de leur servir les mêmes courbes.
        """
        sien = await client.get("/api/v1/tableaux-de-bord/mon-tableau", headers=eleve)
        ecole = await client.get("/api/v1/tableaux-de-bord/mon-tableau", headers=directeur)

        assert "evolution_moyennes" in sien.json()["graphiques"]
        graphiques_ecole = ecole.json()["graphiques"]
        assert {"effectifs_par_niveau", "moyennes_par_classe"} <= set(graphiques_ecole)
        assert "evolution_moyennes" not in graphiques_ecole

    async def test_moyennes_par_classe_restent_dans_l_etablissement(
        self, client: AsyncClient, directeur: dict[str, str], entetes: dict[str, str]
    ) -> None:
        """Le graphique ne doit pas déborder sur les classes des autres écoles."""
        reponse = await client.get("/api/v1/tableaux-de-bord/mon-tableau", headers=directeur)
        classes_du_graphique = {
            point["classe"] for point in reponse.json()["graphiques"]["moyennes_par_classe"]
        }

        siennes = await client.get("/api/v1/classes", headers=directeur, params={"size": 200})
        libelles = {ligne["libelle"] for ligne in siennes.json()["items"]}
        assert classes_du_graphique <= libelles, "des classes d'un autre établissement apparaissent"


class TestRapports:
    """Un rapport porte un périmètre : le télécharger doit le respecter."""

    async def test_rapport_national_refuse_au_directeur(
        self, client: AsyncClient, directeur: dict[str, str], entetes: dict[str, str]
    ) -> None:
        """« rapports:PRINT » ne suffit pas à sortir les chiffres du pays.

        Le chef d'établissement dispose de la permission parce qu'il imprime le
        rapport de son école ; un rapport sans établissement est d'un niveau
        supérieur et doit lui rester fermé.
        """
        cree = await client.post(
            "/api/v1/rapports",
            headers=entetes,
            json={"type_rapport": "NATIONAL", "titre": "Rapport national de contrôle"},
        )
        assert cree.status_code in (200, 201), cree.text
        identifiant = cree.json()["id"]

        assert (
            await client.get(f"/api/v1/rapports/{identifiant}/pdf", headers=entetes)
        ).status_code == 200
        assert (
            await client.get(f"/api/v1/rapports/{identifiant}/pdf", headers=directeur)
        ).status_code == 404

