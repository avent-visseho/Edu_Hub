"""Référentiels : découpage territorial et nomenclatures centralisées."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.crud import creer_routeur_crud, routeur_nomenclature
from app.api.deps import ContexteDep, SessionDep
from app.core.enums import Action
from app.core.pagination import Page, PageParamsDep, paginate
from app.engines.portee import Portee
from app.engines.search import DescripteurChamp
from app.models.referentiel import (
    Arrondissement,
    Commune,
    Cycle,
    Departement,
    Diplome,
    OrdreEnseignement,
    StatutEtablissement,
    TypeBourse,
    TypeDocument,
    TypeEtablissement,
    TypeExamen,
    TypeFormation,
    TypeHandicapRef,
    TypeSalle,
    Village,
)
from app.models.scolarite import Filiere, Matiere, MatiereNiveau, Niveau, Serie
from app.schemas.referentiel import (
    ArrondissementLecture,
    CommuneEcriture,
    CommuneLecture,
    DepartementEcriture,
    DepartementLecture,
    DiplomeReferentielLecture,
    FiliereLecture,
    MatiereEcriture,
    MatiereLecture,
    NiveauLecture,
    SerieLecture,
    TypeDocumentLecture,
    TypeExamenLecture,
    VillageLecture,
)

router = APIRouter()

# ------------------------------------------------------------------
#  Découpage territorial
# ------------------------------------------------------------------

router.include_router(
    creer_routeur_crud(
        modele=Departement,
        schema_lecture=DepartementLecture,
        schema_creation=DepartementEcriture,
        schema_maj=DepartementEcriture,
        prefixe="/departements",
        tag="Référentiels",
        ressource="referentiels",
        portee=Portee.ouverte(),
        libelle_singulier="département",
        libelle_pluriel="départements",
        champs_filtrables=(
            DescripteurChamp("code", "Code", Departement.code),
            DescripteurChamp("libelle", "Libellé", Departement.libelle),
            DescripteurChamp("population", "Population", Departement.population, "nombre"),
        ),
    )
)

router.include_router(
    creer_routeur_crud(
        modele=Commune,
        schema_lecture=CommuneLecture,
        schema_creation=CommuneEcriture,
        schema_maj=CommuneEcriture,
        prefixe="/communes",
        tag="Référentiels",
        ressource="referentiels",
        portee=Portee.ouverte(),
        libelle_singulier="commune",
        libelle_pluriel="communes",
        champs_filtrables=(
            DescripteurChamp("code", "Code", Commune.code),
            DescripteurChamp("libelle", "Libellé", Commune.libelle),
            DescripteurChamp("departement_id", "Département", Commune.departement_id, "uuid"),
            DescripteurChamp("population", "Population", Commune.population, "nombre"),
        ),
    )
)


@router.get(
    "/departements/{identifiant}/communes",
    response_model=list[CommuneLecture],
    tags=["Référentiels"],
    summary="Communes d'un département",
)
async def communes_du_departement(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[Commune]:
    contexte.exiger("referentiels", Action.READ)
    stmt = select(Commune).where(Commune.departement_id == identifiant).order_by(Commune.libelle)
    return list((await session.execute(stmt)).scalars())


@router.get(
    "/communes/{identifiant}/arrondissements",
    response_model=list[ArrondissementLecture],
    tags=["Référentiels"],
    summary="Arrondissements d'une commune",
)
async def arrondissements_de_la_commune(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[Arrondissement]:
    contexte.exiger("referentiels", Action.READ)
    stmt = (
        select(Arrondissement)
        .where(Arrondissement.commune_id == identifiant)
        .order_by(Arrondissement.ordre, Arrondissement.libelle)
    )
    return list((await session.execute(stmt)).scalars())


@router.get(
    "/villages",
    response_model=Page[VillageLecture],
    tags=["Référentiels"],
    summary="Lister les villages et quartiers",
)
async def lister_villages(
    session: SessionDep,
    params: PageParamsDep,
    contexte: ContexteDep,
    arrondissement_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Page:
    contexte.exiger("referentiels", Action.READ)
    stmt = select(Village).order_by(Village.libelle)
    if arrondissement_id:
        stmt = stmt.where(Village.arrondissement_id == arrondissement_id)
    lignes, total = await paginate(session, stmt, params)
    return Page.build([VillageLecture.model_validate(v) for v in lignes], total, params)


# ------------------------------------------------------------------
#  Nomenclatures simples
# ------------------------------------------------------------------

for modele, prefixe, singulier, pluriel in (
    (OrdreEnseignement, "/ordres-enseignement", "ordre d'enseignement", "ordres d'enseignement"),
    (Cycle, "/cycles", "cycle", "cycles"),
    (TypeEtablissement, "/types-etablissement", "type d'établissement", "types d'établissement"),
    (
        StatutEtablissement,
        "/statuts-etablissement",
        "statut d'établissement",
        "statuts d'établissement",
    ),
    (TypeSalle, "/types-salle", "type de salle", "types de salle"),
    (TypeBourse, "/types-bourse", "type de bourse", "types de bourse"),
    (TypeFormation, "/types-formation", "type de formation", "types de formation"),
    (TypeHandicapRef, "/types-handicap", "type de handicap", "types de handicap"),
):
    router.include_router(
        routeur_nomenclature(
            modele=modele,
            prefixe=prefixe,
            ressource="referentiels",
            libelle_singulier=singulier,
            libelle_pluriel=pluriel,
        )
    )


router.include_router(
    creer_routeur_crud(
        modele=TypeExamen,
        schema_lecture=TypeExamenLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/types-examen",
        tag="Référentiels",
        ressource="referentiels",
        portee=Portee.ouverte(),
        libelle_singulier="type d'examen",
        libelle_pluriel="types d'examen",
    )
)

router.include_router(
    creer_routeur_crud(
        modele=TypeDocument,
        schema_lecture=TypeDocumentLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/types-document",
        tag="Référentiels",
        ressource="referentiels",
        portee=Portee.ouverte(),
        libelle_singulier="type de document",
        libelle_pluriel="types de document",
    )
)

router.include_router(
    creer_routeur_crud(
        modele=Diplome,
        schema_lecture=DiplomeReferentielLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/diplomes-referentiel",
        tag="Référentiels",
        ressource="referentiels",
        portee=Portee.ouverte(),
        libelle_singulier="diplôme de référence",
        libelle_pluriel="diplômes de référence",
    )
)


# ------------------------------------------------------------------
#  Structure académique
# ------------------------------------------------------------------

router.include_router(
    creer_routeur_crud(
        modele=Niveau,
        schema_lecture=NiveauLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/niveaux",
        tag="Référentiels",
        ressource="referentiels",
        portee=Portee.ouverte(),
        libelle_singulier="niveau",
        libelle_pluriel="niveaux",
        tri_defaut="rang",
    )
)

router.include_router(
    creer_routeur_crud(
        modele=Serie,
        schema_lecture=SerieLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/series",
        tag="Référentiels",
        ressource="referentiels",
        portee=Portee.ouverte(),
        libelle_singulier="série",
        libelle_pluriel="séries",
    )
)

router.include_router(
    creer_routeur_crud(
        modele=Filiere,
        schema_lecture=FiliereLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/filieres",
        tag="Référentiels",
        ressource="referentiels",
        portee=Portee.ouverte(),
        libelle_singulier="filière",
        libelle_pluriel="filières",
    )
)

router.include_router(
    creer_routeur_crud(
        modele=Matiere,
        schema_lecture=MatiereLecture,
        schema_creation=MatiereEcriture,
        schema_maj=MatiereEcriture,
        prefixe="/matieres",
        tag="Référentiels",
        ressource="referentiels",
        portee=Portee.ouverte(),
        libelle_singulier="matière",
        libelle_pluriel="matières",
        champs_filtrables=(
            DescripteurChamp("code", "Code", Matiere.code),
            DescripteurChamp("libelle", "Libellé", Matiere.libelle),
            DescripteurChamp("domaine", "Domaine", Matiere.domaine),
            DescripteurChamp(
                "coefficient_defaut", "Coefficient", Matiere.coefficient_defaut, "nombre"
            ),
        ),
    )
)


@router.get(
    "/programmes",
    tags=["Référentiels"],
    summary="Programme d'un niveau ou d'une série",
    description="Matières enseignées, coefficients et volumes horaires applicables.",
)
async def programme(
    session: SessionDep,
    contexte: ContexteDep,
    niveau_id: Annotated[uuid.UUID | None, Query()] = None,
    serie_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[dict]:
    contexte.exiger("referentiels", Action.READ)
    stmt = (
        select(MatiereNiveau, Matiere, Niveau)
        .join(Matiere, Matiere.id == MatiereNiveau.matiere_id)
        .join(Niveau, Niveau.id == MatiereNiveau.niveau_id)
        .order_by(Matiere.libelle)
    )
    if niveau_id:
        stmt = stmt.where(MatiereNiveau.niveau_id == niveau_id)
    if serie_id:
        stmt = stmt.where(MatiereNiveau.serie_id == serie_id)

    return [
        {
            "matiere_id": str(matiere.id),
            "matiere_code": matiere.code,
            "matiere_libelle": matiere.libelle,
            "niveau_code": niveau.code,
            "niveau_libelle": niveau.libelle,
            "coefficient": lien.coefficient,
            "volume_horaire": lien.volume_horaire,
            "obligatoire": lien.obligatoire,
        }
        for lien, matiere, niveau in (await session.execute(stmt)).all()
    ]
