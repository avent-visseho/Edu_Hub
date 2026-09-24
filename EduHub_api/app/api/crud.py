"""Fabrique de routeurs CRUD génériques.

Les modules métiers qui n'ont pas de logique propre déclarent leur routeur ici
plutôt que de réécrire cinq fois les mêmes opérations. Chaque routeur produit
respecte le même contrat : liste paginée et filtrable, détail, création, mise à
jour partielle, suppression, le tout sous contrôle de permissions et journalisé.
"""

# Ce module construit des signatures de fonctions à partir de types passés en
# paramètre : les annotations doivent donc rester évaluées à la définition.
import inspect
import uuid
from collections.abc import Callable, Sequence
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ContexteDep, MetadonneesDep, SessionDep
from app.core.database import Base
from app.core.enums import Action
from app.core.exceptions import ConflictError, NotFoundError
from app.core.pagination import Page, PageParams, PageParamsDep, paginate
from app.engines.audit import journaliser
from app.engines.identity import ContexteUtilisateur
from app.engines.search import (
    Conjonction,
    ConstructeurRequete,
    Critere,
    DescripteurChamp,
    criteres_depuis_dict,
)
from app.schemas.base import MessageReponse


class FiltreAvance(BaseModel):
    """Charge utile du constructeur de requêtes."""

    criteres: list[dict[str, Any]] = []
    conjonction: Conjonction = Conjonction.ET
    tri: str | None = None
    sens: str = "asc"


async def obtenir_ou_404(
    session: AsyncSession, modele: type[Base], identifiant: uuid.UUID, libelle: str
):
    """Charge une entité ou lève une erreur 404 explicite."""
    objet = await session.get(modele, identifiant)
    if objet is None:
        raise NotFoundError(f"{libelle} introuvable.", details={"id": str(identifiant)})
    return objet


def appliquer_recherche(statement: Select, modele: type[Base], champs: Sequence[str], terme: str):
    """Recherche plein texte simple sur une liste de colonnes."""
    clauses = [
        getattr(modele, champ).ilike(f"%{terme}%") for champ in champs if hasattr(modele, champ)
    ]
    return statement.where(or_(*clauses)) if clauses else statement


# Paramètres de pagination déjà consommés par la liste : un champ déclaré qui
# porterait l'un de ces noms ne peut pas devenir un filtre de requête.
NOMS_RESERVES = frozenset({"page", "size", "sort_by", "sort_dir", "q"})

_TYPES_FILTRE: dict[str, type] = {
    "uuid": uuid.UUID,
    "nombre": float,
    "booleen": bool,
    "date": date,
}


def construire_dependance_filtres(
    champs: Sequence[DescripteurChamp],
) -> Callable[..., dict[str, Any]]:
    """Expose chaque champ déclaré comme paramètre de requête d'égalité.

    Le filtrage direct se limite volontairement à l'égalité, seule opération
    dont la sémantique est évidente dans une URL ; les comparaisons riches
    passent par `/recherche`, qui valide opérateurs et valeurs. Comme pour le
    constructeur de requêtes, un champ non déclaré n'est pas filtrable.
    """
    parametres = [
        inspect.Parameter(
            champ.cle,
            inspect.Parameter.KEYWORD_ONLY,
            default=Query(default=None, description=f"Filtrer sur « {champ.libelle} »"),
            annotation=_TYPES_FILTRE.get(champ.type_valeur, str) | None,
        )
        for champ in champs
        if champ.cle not in NOMS_RESERVES
    ]

    def dependance(**valeurs: Any) -> dict[str, Any]:
        return {cle: valeur for cle, valeur in valeurs.items() if valeur is not None}

    dependance.__signature__ = inspect.Signature(parametres)  # type: ignore[attr-defined]
    return dependance


def creer_routeur_crud(
    *,
    modele: type[Base],
    schema_lecture: type[BaseModel],
    schema_creation: type[BaseModel] | None,
    schema_maj: type[BaseModel] | None,
    prefixe: str,
    tag: str,
    ressource: str,
    libelle_singulier: str,
    libelle_pluriel: str,
    champs_recherche: Sequence[str] = ("code", "libelle"),
    champs_filtrables: Sequence[DescripteurChamp] = (),
    tri_defaut: str | None = "code",
    contrainte_unicite: str | None = "code",
    precharger: Callable[[Select], Select] | None = None,
    lecture_publique: bool = False,
) -> APIRouter:
    """Construit un routeur REST complet pour une entité.

    `champs_filtrables` alimente à la fois le point d'entrée `/champs` — que
    l'interface utilise pour bâtir son constructeur de requêtes — et le filtrage
    avancé exposé sur `/recherche`.
    """
    routeur = APIRouter(prefix=prefixe, tags=[tag])
    constructeur = ConstructeurRequete(ressource, champs_filtrables)
    dependance_filtres = construire_dependance_filtres(champs_filtrables)

    def _base_statement() -> Select:
        statement = select(modele)
        if hasattr(modele, "supprime"):
            statement = statement.where(modele.supprime.is_(False))
        return precharger(statement) if precharger else statement

    def _filtrer(statement: Select, filtres: dict[str, Any]) -> Select:
        for cle, valeur in filtres.items():
            statement = statement.where(constructeur.champs[cle].colonne == valeur)
        return statement

    def _trier(statement: Select, params: PageParams) -> Select:
        champ = params.sort_by or tri_defaut
        if champ and hasattr(modele, champ):
            colonne = getattr(modele, champ)
            return statement.order_by(colonne.desc() if params.sort_dir == "desc" else colonne)
        return statement

    # ---------- Liste ----------

    @routeur.get(
        "",
        response_model=Page[schema_lecture],
        summary=f"Lister les {libelle_pluriel}",
    )
    async def lister(
        session: SessionDep,
        params: PageParamsDep,
        contexte: ContexteDep,
        filtres: Annotated[dict[str, Any], Depends(dependance_filtres)],
        q: Annotated[str | None, Query(description="Recherche libre")] = None,
    ) -> Page:
        if not lecture_publique:
            contexte.exiger(ressource, Action.READ)
        statement = _base_statement()
        if q:
            statement = appliquer_recherche(statement, modele, champs_recherche, q)
        statement = _filtrer(statement, filtres)
        statement = _trier(statement, params)
        lignes, total = await paginate(session, statement, params)
        return Page.build([schema_lecture.model_validate(ligne) for ligne in lignes], total, params)

    # ---------- Champs interrogeables ----------

    if champs_filtrables:

        @routeur.get(
            "/champs",
            summary=f"Variables interrogeables sur les {libelle_pluriel}",
            description="Alimente le constructeur visuel de requêtes.",
        )
        async def champs(contexte: ContexteDep) -> dict[str, Any]:
            contexte.exiger(ressource, Action.READ)
            return {"entite": ressource, "champs": constructeur.decrire()}

        @routeur.post(
            "/recherche",
            response_model=Page[schema_lecture],
            summary=f"Recherche avancée sur les {libelle_pluriel}",
        )
        async def rechercher(
            filtre: FiltreAvance,
            session: SessionDep,
            params: PageParamsDep,
            contexte: ContexteDep,
        ) -> Page:
            contexte.exiger(ressource, Action.READ)
            criteres: list[Critere] = criteres_depuis_dict(filtre.criteres)
            statement = constructeur.appliquer(_base_statement(), criteres, filtre.conjonction)
            statement = constructeur.trier(statement, filtre.tri, filtre.sens)
            lignes, total = await paginate(session, statement, params)
            return Page.build(
                [schema_lecture.model_validate(ligne) for ligne in lignes], total, params
            )

    # ---------- Détail ----------

    @routeur.get(
        "/{identifiant}",
        response_model=schema_lecture,
        summary=f"Consulter un {libelle_singulier}",
    )
    async def detail(identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep) -> Any:
        if not lecture_publique:
            contexte.exiger(ressource, Action.READ)
        return await obtenir_ou_404(session, modele, identifiant, libelle_singulier.capitalize())

    # ---------- Création ----------

    if schema_creation is not None:

        @routeur.post(
            "",
            response_model=schema_lecture,
            status_code=status.HTTP_201_CREATED,
            summary=f"Créer un {libelle_singulier}",
        )
        async def creer(
            donnees: schema_creation,
            session: SessionDep,
            contexte: ContexteDep,
            metadonnees: MetadonneesDep,
        ) -> Any:
            contexte.exiger(ressource, Action.CREATE)
            valeurs = donnees.model_dump(exclude_unset=True)

            if contrainte_unicite and contrainte_unicite in valeurs:
                colonne = getattr(modele, contrainte_unicite)
                existant = (
                    await session.execute(
                        select(modele).where(colonne == valeurs[contrainte_unicite]).limit(1)
                    )
                ).scalar_one_or_none()
                if existant is not None:
                    raise ConflictError(
                        f"Un {libelle_singulier} portant ce {contrainte_unicite} existe déjà.",
                        details={contrainte_unicite: valeurs[contrainte_unicite]},
                    )

            objet = modele(**valeurs)
            session.add(objet)
            await session.flush()
            await journaliser(
                session,
                action=Action.CREATE,
                entite_type=ressource,
                entite_id=objet.id,
                entite_libelle=str(valeurs.get("libelle") or valeurs.get("nom") or objet.id),
                utilisateur_id=contexte.id,
                utilisateur_email=contexte.email,
                valeurs_apres=valeurs,
                adresse_ip=metadonnees["adresse_ip"],
            )
            return objet

    # ---------- Mise à jour ----------

    if schema_maj is not None:

        @routeur.patch(
            "/{identifiant}",
            response_model=schema_lecture,
            summary=f"Modifier un {libelle_singulier}",
        )
        async def modifier(
            identifiant: uuid.UUID,
            donnees: schema_maj,
            session: SessionDep,
            contexte: ContexteDep,
            metadonnees: MetadonneesDep,
        ) -> Any:
            contexte.exiger(ressource, Action.UPDATE)
            objet = await obtenir_ou_404(
                session, modele, identifiant, libelle_singulier.capitalize()
            )
            valeurs = donnees.model_dump(exclude_unset=True)
            avant = {champ: getattr(objet, champ, None) for champ in valeurs}
            for champ, valeur in valeurs.items():
                setattr(objet, champ, valeur)
            await session.flush()
            await journaliser(
                session,
                action=Action.UPDATE,
                entite_type=ressource,
                entite_id=objet.id,
                utilisateur_id=contexte.id,
                utilisateur_email=contexte.email,
                valeurs_avant=avant,
                valeurs_apres=valeurs,
                adresse_ip=metadonnees["adresse_ip"],
            )
            return objet

    # ---------- Suppression ----------

    @routeur.delete(
        "/{identifiant}",
        response_model=MessageReponse,
        summary=f"Supprimer un {libelle_singulier}",
        description="Archive l'entité lorsqu'elle est archivable, la supprime sinon.",
    )
    async def supprimer(
        identifiant: uuid.UUID,
        session: SessionDep,
        contexte: ContexteDep,
        metadonnees: MetadonneesDep,
    ) -> MessageReponse:
        contexte.exiger(ressource, Action.DELETE)
        objet = await obtenir_ou_404(session, modele, identifiant, libelle_singulier.capitalize())

        if hasattr(objet, "supprime"):
            from datetime import UTC, datetime

            objet.supprime = True
            objet.supprime_le = datetime.now(UTC)
            message = f"{libelle_singulier.capitalize()} archivé."
        else:
            await session.delete(objet)
            message = f"{libelle_singulier.capitalize()} supprimé."

        await journaliser(
            session,
            action=Action.DELETE,
            entite_type=ressource,
            entite_id=identifiant,
            utilisateur_id=contexte.id,
            utilisateur_email=contexte.email,
            adresse_ip=metadonnees["adresse_ip"],
        )
        return MessageReponse(message=message)

    return routeur


def routeur_nomenclature(
    *,
    modele: type[Base],
    prefixe: str,
    ressource: str,
    libelle_singulier: str,
    libelle_pluriel: str,
) -> APIRouter:
    """Raccourci pour les référentiels code/libellé."""
    from app.schemas.base import NomenclatureEcriture, NomenclatureLecture

    return creer_routeur_crud(
        modele=modele,
        schema_lecture=NomenclatureLecture,
        schema_creation=NomenclatureEcriture,
        schema_maj=NomenclatureEcriture,
        prefixe=prefixe,
        tag="Référentiels",
        ressource=ressource,
        libelle_singulier=libelle_singulier,
        libelle_pluriel=libelle_pluriel,
        tri_defaut="ordre",
    )


def sans_droits(contexte: ContexteUtilisateur) -> ContexteUtilisateur:
    """Marqueur explicite pour les routes ouvertes à tout utilisateur connecté."""
    return contexte


__all__ = [
    "Depends",
    "FiltreAvance",
    "appliquer_recherche",
    "creer_routeur_crud",
    "obtenir_ou_404",
    "routeur_nomenclature",
    "sans_droits",
]
