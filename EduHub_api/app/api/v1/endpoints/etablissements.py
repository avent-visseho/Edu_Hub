"""Établissements, structures institutionnelles et infrastructures."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.crud import creer_routeur_crud, obtenir_ou_404
from app.api.deps import ContexteDep, SessionDep
from app.core.enums import Action
from app.core.exceptions import PermissionDeniedError
from app.engines.analytics import statistiques_etablissement
from app.engines.search import DescripteurChamp
from app.models.etablissement import Batiment, Equipement, Etablissement, Salle
from app.models.organisation import Structure
from app.models.personnel import Enseignant
from app.models.referentiel import Commune, Departement, StatutEtablissement, TypeEtablissement
from app.models.scolarite import Classe
from app.schemas.etablissement import (
    BatimentEcriture,
    BatimentLecture,
    EquipementEcriture,
    EquipementLecture,
    EtablissementCreation,
    EtablissementDetail,
    EtablissementLecture,
    EtablissementMiseAJour,
    SalleEcriture,
    SalleLecture,
    StructureEcriture,
    StructureLecture,
    StructureNoeud,
)

router = APIRouter()


CHAMPS_ETABLISSEMENT = (
    DescripteurChamp("code", "Code", Etablissement.code),
    DescripteurChamp("nom", "Nom", Etablissement.nom),
    DescripteurChamp("type_etablissement_id", "Type", Etablissement.type_etablissement_id, "uuid"),
    DescripteurChamp(
        "statut_etablissement_id", "Statut", Etablissement.statut_etablissement_id, "uuid"
    ),
    DescripteurChamp("commune_id", "Commune", Etablissement.commune_id, "uuid"),
    DescripteurChamp("effectif_actuel", "Effectif", Etablissement.effectif_actuel, "nombre"),
    DescripteurChamp("capacite_accueil", "Capacité", Etablissement.capacite_accueil, "nombre"),
    DescripteurChamp("annee_creation", "Année de création", Etablissement.annee_creation, "nombre"),
    DescripteurChamp("zone_rurale", "Zone rurale", Etablissement.zone_rurale, "booleen"),
    DescripteurChamp(
        "est_centre_examen", "Centre d'examen", Etablissement.est_centre_examen, "booleen"
    ),
    DescripteurChamp("internat", "Internat", Etablissement.internat, "booleen"),
    DescripteurChamp("cantine", "Cantine", Etablissement.cantine, "booleen"),
    DescripteurChamp("electricite", "Électricité", Etablissement.electricite, "booleen"),
    DescripteurChamp("eau_potable", "Eau potable", Etablissement.eau_potable, "booleen"),
    DescripteurChamp(
        "connexion_internet", "Connexion internet", Etablissement.connexion_internet, "booleen"
    ),
    DescripteurChamp("accessibilite", "Accessibilité", Etablissement.accessibilite, "liste"),
)


# ------------------------------------------------------------------
#  Structures institutionnelles
# ------------------------------------------------------------------

structures = creer_routeur_crud(
    modele=Structure,
    schema_lecture=StructureLecture,
    schema_creation=StructureEcriture,
    schema_maj=StructureEcriture,
    prefixe="/structures",
    tag="Organisation",
    ressource="structures",
    libelle_singulier="structure",
    libelle_pluriel="structures",
    champs_filtrables=(
        DescripteurChamp("code", "Code", Structure.code),
        DescripteurChamp("libelle", "Libellé", Structure.libelle),
        DescripteurChamp("sigle", "Sigle", Structure.sigle),
        DescripteurChamp("categorie", "Catégorie", Structure.categorie, "liste"),
        DescripteurChamp("departement_id", "Département", Structure.departement_id, "uuid"),
    ),
)


@structures.get(
    "/arbre/complet",
    response_model=list[StructureNoeud],
    summary="Arbre institutionnel complet",
    description="Hiérarchie ministère → direction → direction départementale.",
)
async def arbre_institutionnel(session: SessionDep, contexte: ContexteDep) -> list[dict]:
    contexte.exiger("structures", Action.READ)
    stmt = select(Structure).where(Structure.supprime.is_(False)).order_by(Structure.ordre)
    noeuds = list((await session.execute(stmt)).scalars())

    par_id = {n.id: StructureNoeud.model_validate(n).model_dump() for n in noeuds}
    racines: list[dict] = []
    for noeud in noeuds:
        charge = par_id[noeud.id]
        parent = par_id.get(noeud.parent_id) if noeud.parent_id else None
        if parent is None:
            racines.append(charge)
        else:
            parent["enfants"].append(charge)
    return racines


router.include_router(structures)


# ------------------------------------------------------------------
#  Établissements
# ------------------------------------------------------------------

etablissements = creer_routeur_crud(
    modele=Etablissement,
    schema_lecture=EtablissementLecture,
    schema_creation=EtablissementCreation,
    schema_maj=EtablissementMiseAJour,
    prefixe="/etablissements",
    tag="Établissements",
    ressource="etablissements",
    libelle_singulier="établissement",
    libelle_pluriel="établissements",
    champs_recherche=("code", "nom", "sigle", "directeur_nom"),
    champs_filtrables=CHAMPS_ETABLISSEMENT,
    tri_defaut="nom",
)


@etablissements.get(
    "/{identifiant}/detail",
    response_model=EtablissementDetail,
    summary="Fiche détaillée d'un établissement",
)
async def detail_etablissement(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> EtablissementDetail:
    contexte.exiger("etablissements", Action.READ)
    stmt = (
        select(Etablissement)
        .where(Etablissement.id == identifiant)
        .options(
            selectinload(Etablissement.type_etablissement),
            selectinload(Etablissement.statut_etablissement),
            selectinload(Etablissement.commune).selectinload(Commune.departement),
        )
    )
    etablissement = (await session.execute(stmt)).scalar_one_or_none()
    if etablissement is None:
        await obtenir_ou_404(session, Etablissement, identifiant, "Établissement")

    async def compter(modele, condition) -> int:
        return int(
            (
                await session.execute(select(func.count()).select_from(modele).where(condition))
            ).scalar_one()
        )

    detail = EtablissementDetail.model_validate(etablissement)
    detail.type_libelle = (
        etablissement.type_etablissement.libelle if etablissement.type_etablissement else None
    )
    detail.statut_libelle = (
        etablissement.statut_etablissement.libelle if etablissement.statut_etablissement else None
    )
    detail.commune_libelle = etablissement.commune.libelle if etablissement.commune else None
    detail.departement_libelle = (
        etablissement.commune.departement.libelle
        if etablissement.commune and etablissement.commune.departement
        else None
    )
    detail.nombre_salles = await compter(Salle, Salle.etablissement_id == identifiant)
    detail.nombre_batiments = await compter(Batiment, Batiment.etablissement_id == identifiant)
    detail.nombre_classes = await compter(Classe, Classe.etablissement_id == identifiant)
    detail.nombre_enseignants = await compter(
        Enseignant, Enseignant.etablissement_principal_id == identifiant
    )
    return detail


@etablissements.get(
    "/{identifiant}/tableau-de-bord",
    summary="Tableau de bord d'un établissement",
    description="Effectifs, encadrement, infrastructures et résultats.",
)
async def tableau_de_bord(
    identifiant: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
    annee_id: Annotated[uuid.UUID | None, Query()] = None,
) -> dict:
    contexte.exiger("etablissements", Action.READ)
    if not contexte.peut_acceder_etablissement(identifiant):
        raise PermissionDeniedError("Cet établissement n'entre pas dans votre périmètre.")

    etablissement = await obtenir_ou_404(session, Etablissement, identifiant, "Établissement")
    statistiques = await statistiques_etablissement(session, identifiant, annee_id)
    return {
        "etablissement": {
            "id": str(etablissement.id),
            "code": etablissement.code,
            "nom": etablissement.nom,
        },
        "indicateurs": statistiques,
    }


@etablissements.get(
    "/{identifiant}/classes",
    summary="Classes d'un établissement",
)
async def classes_etablissement(
    identifiant: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
    annee_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[dict]:
    contexte.exiger("classes", Action.READ)
    stmt = (
        select(Classe)
        .where(Classe.etablissement_id == identifiant)
        .options(selectinload(Classe.niveau), selectinload(Classe.serie))
        .order_by(Classe.code)
    )
    if annee_id:
        stmt = stmt.where(Classe.annee_id == annee_id)

    return [
        {
            "id": str(classe.id),
            "code": classe.code,
            "libelle": classe.libelle,
            "niveau": classe.niveau.libelle if classe.niveau else None,
            "serie": classe.serie.code if classe.serie else None,
            "effectif": classe.effectif,
            "effectif_max": classe.effectif_max,
            "moyenne_classe": classe.moyenne_classe,
        }
        for classe in (await session.execute(stmt)).scalars()
    ]


router.include_router(etablissements)


# ------------------------------------------------------------------
#  Infrastructures
# ------------------------------------------------------------------

router.include_router(
    creer_routeur_crud(
        modele=Batiment,
        schema_lecture=BatimentLecture,
        schema_creation=BatimentEcriture,
        schema_maj=BatimentEcriture,
        prefixe="/batiments",
        tag="Infrastructures",
        ressource="infrastructures",
        libelle_singulier="bâtiment",
        libelle_pluriel="bâtiments",
        champs_recherche=("code", "nom"),
        contrainte_unicite=None,
        champs_filtrables=(
            DescripteurChamp("code", "Code", Batiment.code),
            DescripteurChamp("nom", "Nom", Batiment.nom),
            DescripteurChamp(
                "etablissement_id", "Établissement", Batiment.etablissement_id, "uuid"
            ),
            DescripteurChamp("etat", "État", Batiment.etat, "liste"),
        ),
    )
)

salles = creer_routeur_crud(
    modele=Salle,
    schema_lecture=SalleLecture,
    schema_creation=SalleEcriture,
    schema_maj=SalleEcriture,
    prefixe="/salles",
    tag="Infrastructures",
    ressource="infrastructures",
    libelle_singulier="salle",
    libelle_pluriel="salles",
    champs_recherche=("code", "nom"),
    contrainte_unicite=None,
    champs_filtrables=(
        DescripteurChamp("code", "Code", Salle.code),
        DescripteurChamp("nom", "Nom", Salle.nom),
        DescripteurChamp("etablissement_id", "Établissement", Salle.etablissement_id, "uuid"),
        DescripteurChamp("type_salle_id", "Type", Salle.type_salle_id, "uuid"),
        DescripteurChamp("capacite", "Capacité", Salle.capacite, "nombre"),
        DescripteurChamp("disponible", "Disponible", Salle.disponible, "booleen"),
        DescripteurChamp("accessibilite", "Accessibilité", Salle.accessibilite, "liste"),
    ),
)
router.include_router(salles)

router.include_router(
    creer_routeur_crud(
        modele=Equipement,
        schema_lecture=EquipementLecture,
        schema_creation=EquipementEcriture,
        schema_maj=EquipementEcriture,
        prefixe="/equipements",
        tag="Infrastructures",
        ressource="infrastructures",
        libelle_singulier="équipement",
        libelle_pluriel="équipements",
        champs_recherche=("reference", "designation"),
        contrainte_unicite=None,
        tri_defaut="reference",
        champs_filtrables=(
            DescripteurChamp("reference", "Référence", Equipement.reference),
            DescripteurChamp("designation", "Désignation", Equipement.designation),
            DescripteurChamp(
                "etablissement_id", "Établissement", Equipement.etablissement_id, "uuid"
            ),
            DescripteurChamp("type_equipement", "Type", Equipement.type_equipement, "liste"),
            DescripteurChamp("etat", "État", Equipement.etat, "liste"),
            DescripteurChamp("quantite", "Quantité", Equipement.quantite, "nombre"),
        ),
    )
)


@router.get(
    "/etablissements-carte/points",
    tags=["Établissements"],
    summary="Points cartographiques des établissements",
    description="Alimente la carte nationale : position, type, effectif, accessibilité.",
)
async def points_carte(
    session: SessionDep,
    contexte: ContexteDep,
    departement_id: Annotated[uuid.UUID | None, Query()] = None,
    type_etablissement_id: Annotated[uuid.UUID | None, Query()] = None,
    limite: Annotated[int, Query(ge=1, le=5000)] = 1500,
) -> list[dict]:
    contexte.exiger("etablissements", Action.READ)
    stmt = (
        select(
            Etablissement.id,
            Etablissement.nom,
            Etablissement.latitude,
            Etablissement.longitude,
            Etablissement.effectif_actuel,
            Etablissement.accessibilite,
            TypeEtablissement.code,
            StatutEtablissement.libelle,
            Commune.libelle,
            Departement.libelle,
        )
        .outerjoin(TypeEtablissement, TypeEtablissement.id == Etablissement.type_etablissement_id)
        .outerjoin(
            StatutEtablissement, StatutEtablissement.id == Etablissement.statut_etablissement_id
        )
        .outerjoin(Commune, Commune.id == Etablissement.commune_id)
        .outerjoin(Departement, Departement.id == Commune.departement_id)
        .where(
            Etablissement.supprime.is_(False),
            Etablissement.latitude.isnot(None),
            Etablissement.longitude.isnot(None),
        )
        .limit(limite)
    )
    if departement_id:
        stmt = stmt.where(Commune.departement_id == departement_id)
    if type_etablissement_id:
        stmt = stmt.where(Etablissement.type_etablissement_id == type_etablissement_id)

    return [
        {
            "id": str(ident),
            "libelle": nom,
            "latitude": latitude,
            "longitude": longitude,
            "effectif": effectif,
            "accessibilite": accessibilite.value if accessibilite else None,
            "type": type_code,
            "statut": statut,
            "commune": commune,
            "departement": departement,
        }
        for (
            ident,
            nom,
            latitude,
            longitude,
            effectif,
            accessibilite,
            type_code,
            statut,
            commune,
            departement,
        ) in (await session.execute(stmt)).all()
    ]
