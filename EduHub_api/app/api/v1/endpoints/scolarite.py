"""Scolarité : années, classes, inscriptions, emploi du temps et assiduité."""

import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import selectinload

from app.api.crud import creer_routeur_crud, obtenir_ou_404
from app.api.deps import ContexteDep, MetadonneesDep, SessionDep
from app.core.enums import Action
from app.core.exceptions import BusinessRuleError, ConflictError
from app.engines import workflow
from app.engines.audit import journaliser
from app.engines.portee import (
    Portee,
    exiger_classe_dans_la_portee,
    exiger_pilotage,
    exiger_seance_dans_la_portee,
)
from app.engines.search import DescripteurChamp
from app.models.apprenant import Apprenant
from app.models.pedagogie import (
    CreneauEmploiDuTemps,
    Presence,
    Seance,
    StatutPresence,
    StatutSeance,
    SyntheseAssiduite,
)
from app.models.scolarite import (
    AnneeAcademique,
    Classe,
    Inscription,
    Periode,
    StatutInscription,
)
from app.schemas.base import MessageReponse
from app.schemas.scolarite import (
    AnneeEcriture,
    AnneeLecture,
    AppelDemande,
    ClasseEcriture,
    ClasseLecture,
    ClasseMiseAJour,
    CreneauEcriture,
    CreneauLecture,
    InscriptionCreation,
    InscriptionLecture,
    PresenceLecture,
    TransitionDemande,
)
from app.utils.calculs import taux

router = APIRouter()


# ------------------------------------------------------------------
#  Années académiques
# ------------------------------------------------------------------

annees = creer_routeur_crud(
    modele=AnneeAcademique,
    portee=Portee.ouverte(),
    schema_lecture=AnneeLecture,
    schema_creation=AnneeEcriture,
    schema_maj=AnneeEcriture,
    prefixe="/annees",
    tag="Scolarité",
    ressource="referentiels",
    libelle_singulier="année académique",
    libelle_pluriel="années académiques",
    tri_defaut="annee_debut",
    precharger=lambda stmt: stmt.options(selectinload(AnneeAcademique.periodes)),
)


@annees.post(
    "/{identifiant}/definir-courante",
    response_model=MessageReponse,
    summary="Définir l'année courante",
)
async def definir_courante(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> MessageReponse:
    contexte.exiger("referentiels", Action.UPDATE)
    annee = await obtenir_ou_404(session, AnneeAcademique, identifiant, "Année académique")

    for autre in (await session.execute(select(AnneeAcademique))).scalars():
        autre.courante = autre.id == identifiant
    await session.flush()
    return MessageReponse(message=f"L'année {annee.code} est désormais l'année courante.")


router.include_router(annees)


# ------------------------------------------------------------------
#  Classes
# ------------------------------------------------------------------

classes = creer_routeur_crud(
    modele=Classe,
    portee=Portee(classe="id", etablissement="etablissement_id"),
    schema_lecture=ClasseLecture,
    schema_creation=ClasseEcriture,
    schema_maj=ClasseMiseAJour,
    prefixe="/classes",
    tag="Scolarité",
    ressource="classes",
    libelle_singulier="classe",
    libelle_pluriel="classes",
    champs_recherche=("code", "libelle"),
    contrainte_unicite=None,
    champs_filtrables=(
        DescripteurChamp("code", "Code", Classe.code),
        DescripteurChamp("libelle", "Libellé", Classe.libelle),
        DescripteurChamp("etablissement_id", "Établissement", Classe.etablissement_id, "uuid"),
        DescripteurChamp("annee_id", "Année", Classe.annee_id, "uuid"),
        DescripteurChamp("niveau_id", "Niveau", Classe.niveau_id, "uuid"),
        DescripteurChamp("serie_id", "Série", Classe.serie_id, "uuid"),
        DescripteurChamp("effectif", "Effectif", Classe.effectif, "nombre"),
        DescripteurChamp("moyenne_classe", "Moyenne", Classe.moyenne_classe, "nombre"),
    ),
)


@classes.get(
    "/{identifiant}/apprenants",
    summary="Effectif d'une classe",
    description="Liste nominative des apprenants inscrits, avec leur moyenne courante.",
)
async def effectif_classe(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[dict]:
    contexte.exiger("classes", Action.READ)
    stmt = (
        select(Apprenant, Inscription)
        .join(Inscription, Inscription.apprenant_id == Apprenant.id)
        .where(Inscription.classe_id == identifiant)
        .order_by(Apprenant.nom, Apprenant.prenoms)
    )
    return [
        {
            "id": str(apprenant.id),
            "identifiant_educatif": apprenant.identifiant_educatif,
            "nom_complet": apprenant.nom_complet,
            "sexe": apprenant.sexe.value,
            "date_naissance": apprenant.date_naissance.isoformat(),
            "type_handicap": apprenant.type_handicap.value,
            "tiers_temps": apprenant.tiers_temps,
            "numero_inscription": inscription.numero,
            "statut": inscription.statut.value,
            "redoublant": inscription.redoublant,
            "moyenne_annuelle": inscription.moyenne_annuelle,
        }
        for apprenant, inscription in (await session.execute(stmt)).all()
    ]


@classes.get(
    "/{identifiant}/emploi-du-temps",
    response_model=list[CreneauLecture],
    summary="Emploi du temps d'une classe",
)
async def emploi_du_temps(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[CreneauEmploiDuTemps]:
    contexte.exiger("emploi_du_temps", Action.READ)
    stmt = (
        select(CreneauEmploiDuTemps)
        .where(CreneauEmploiDuTemps.classe_id == identifiant)
        .order_by(CreneauEmploiDuTemps.jour, CreneauEmploiDuTemps.heure_debut)
    )
    return list((await session.execute(stmt)).scalars())


router.include_router(classes)


# ------------------------------------------------------------------
#  Inscriptions
# ------------------------------------------------------------------

inscriptions = creer_routeur_crud(
    modele=Inscription,
    portee=Portee(apprenant="apprenant_id", etablissement="etablissement_id"),
    schema_lecture=InscriptionLecture,
    schema_creation=None,
    schema_maj=None,
    prefixe="/inscriptions",
    tag="Scolarité",
    ressource="inscriptions",
    libelle_singulier="inscription",
    libelle_pluriel="inscriptions",
    champs_recherche=("numero",),
    tri_defaut="numero",
    champs_filtrables=(
        DescripteurChamp("numero", "Numéro", Inscription.numero),
        DescripteurChamp("statut", "Statut", Inscription.statut, "liste"),
        DescripteurChamp("regime", "Régime", Inscription.regime, "liste"),
        DescripteurChamp("etablissement_id", "Établissement", Inscription.etablissement_id, "uuid"),
        DescripteurChamp("annee_id", "Année", Inscription.annee_id, "uuid"),
        DescripteurChamp("classe_id", "Classe", Inscription.classe_id, "uuid"),
        DescripteurChamp("redoublant", "Redoublant", Inscription.redoublant, "booleen"),
        DescripteurChamp("boursier", "Boursier", Inscription.boursier, "booleen"),
        DescripteurChamp(
            "moyenne_annuelle", "Moyenne annuelle", Inscription.moyenne_annuelle, "nombre"
        ),
    ),
)


@inscriptions.post(
    "",
    response_model=InscriptionLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Déposer une demande d'inscription",
)
async def creer_inscription(
    donnees: InscriptionCreation,
    session: SessionDep,
    contexte: ContexteDep,
    metadonnees: MetadonneesDep,
) -> Inscription:
    contexte.exiger("inscriptions", Action.CREATE)
    await obtenir_ou_404(session, Apprenant, donnees.apprenant_id, "Apprenant")

    existante = (
        await session.execute(
            select(Inscription).where(
                Inscription.apprenant_id == donnees.apprenant_id,
                Inscription.annee_id == donnees.annee_id,
            )
        )
    ).scalar_one_or_none()
    if existante is not None:
        raise ConflictError(
            "Cet apprenant est déjà inscrit pour cette année académique.",
            details={"inscription_id": str(existante.id)},
        )

    annee = await obtenir_ou_404(session, AnneeAcademique, donnees.annee_id, "Année académique")
    total = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Inscription)
                .where(Inscription.annee_id == donnees.annee_id)
            )
        ).scalar_one()
    )

    inscription = Inscription(
        numero=f"INS-{annee.code}-{total + 1:07d}",
        date_demande=date.today(),
        statut=StatutInscription.DEMANDE,
        **donnees.model_dump(),
    )
    session.add(inscription)
    await session.flush()

    await journaliser(
        session,
        action=Action.CREATE,
        entite_type="inscriptions",
        entite_id=inscription.id,
        entite_libelle=inscription.numero,
        utilisateur_id=contexte.id,
        utilisateur_email=contexte.email,
        adresse_ip=metadonnees["adresse_ip"],
    )
    return inscription


@inscriptions.post(
    "/{identifiant}/transition",
    response_model=InscriptionLecture,
    summary="Faire avancer une inscription dans son workflow",
    description=(
        "Actions : deposer_dossier, verifier, valider, rejeter, affecter_classe, "
        "transferer, abandonner, exclure."
    ),
)
async def transition_inscription(
    identifiant: uuid.UUID,
    demande: TransitionDemande,
    session: SessionDep,
    contexte: ContexteDep,
) -> Inscription:
    contexte.exiger("inscriptions", Action.VALIDATE)
    inscription = await obtenir_ou_404(session, Inscription, identifiant, "Inscription")

    transition = await workflow.appliquer(
        session,
        workflow.WORKFLOW_INSCRIPTION,
        entite_type="inscriptions",
        entite_id=inscription.id,
        statut_actuel=inscription.statut.value,
        action=demande.action,
        acteur_id=contexte.id,
        acteur_nom=contexte.utilisateur.nom_complet,
        roles=contexte.roles,
        commentaire=demande.commentaire,
    )

    inscription.statut = StatutInscription(transition.vers)
    if transition.vers == StatutInscription.VALIDEE.value:
        inscription.date_validation = date.today()
    if transition.vers == StatutInscription.REJETEE.value:
        inscription.motif_rejet = demande.motif
    if transition.vers == StatutInscription.INSCRIT.value:
        if inscription.classe_id is None:
            raise BusinessRuleError(
                "Une classe doit être affectée avant de finaliser l'inscription."
            )
        classe = await session.get(Classe, inscription.classe_id)
        if classe is not None:
            classe.effectif = int(
                (
                    await session.execute(
                        select(func.count())
                        .select_from(Inscription)
                        .where(Inscription.classe_id == classe.id)
                    )
                ).scalar_one()
            )

    await session.flush()
    return inscription


@inscriptions.get(
    "/{identifiant}/transitions",
    summary="Actions possibles sur une inscription",
)
async def transitions_possibles(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[dict]:
    contexte.exiger("inscriptions", Action.READ)
    inscription = await obtenir_ou_404(session, Inscription, identifiant, "Inscription")
    return [
        {"action": t.action, "libelle": t.libelle, "vers": t.vers}
        for t in workflow.WORKFLOW_INSCRIPTION.transitions_possibles(inscription.statut.value)
    ]


router.include_router(inscriptions)


# ------------------------------------------------------------------
#  Emploi du temps et assiduité
# ------------------------------------------------------------------

creneaux = creer_routeur_crud(
    modele=CreneauEmploiDuTemps,
    portee=Portee(classe="classe_id", enseignant="enseignant_id"),
    schema_lecture=CreneauLecture,
    schema_creation=CreneauEcriture,
    schema_maj=CreneauEcriture,
    prefixe="/creneaux",
    tag="Pédagogie",
    ressource="emploi_du_temps",
    libelle_singulier="créneau",
    libelle_pluriel="créneaux",
    champs_recherche=(),
    contrainte_unicite=None,
    tri_defaut="jour",
    champs_filtrables=(
        DescripteurChamp("classe_id", "Classe", CreneauEmploiDuTemps.classe_id, "uuid"),
        DescripteurChamp("matiere_id", "Matière", CreneauEmploiDuTemps.matiere_id, "uuid"),
        DescripteurChamp("enseignant_id", "Enseignant", CreneauEmploiDuTemps.enseignant_id, "uuid"),
        DescripteurChamp("salle_id", "Salle", CreneauEmploiDuTemps.salle_id, "uuid"),
        DescripteurChamp("jour", "Jour", CreneauEmploiDuTemps.jour, "liste"),
    ),
)


@creneaux.post(
    "/verifier-conflits",
    summary="Détecter les conflits d'emploi du temps",
    description="Vérifie qu'un créneau ne chevauche ni l'enseignant, ni la salle, ni la classe.",
)
async def verifier_conflits(
    donnees: CreneauEcriture, session: SessionDep, contexte: ContexteDep
) -> dict:
    contexte.exiger("emploi_du_temps", Action.READ)

    def chevauche(colonne_id, valeur, libelle: str):
        if valeur is None:
            return None
        return (
            select(CreneauEmploiDuTemps).where(
                colonne_id == valeur,
                CreneauEmploiDuTemps.jour == donnees.jour,
                CreneauEmploiDuTemps.heure_debut < donnees.heure_fin,
                CreneauEmploiDuTemps.heure_fin > donnees.heure_debut,
            ),
            libelle,
        )

    verifications = [
        chevauche(CreneauEmploiDuTemps.enseignant_id, donnees.enseignant_id, "Enseignant"),
        chevauche(CreneauEmploiDuTemps.salle_id, donnees.salle_id, "Salle"),
        chevauche(CreneauEmploiDuTemps.classe_id, donnees.classe_id, "Classe"),
    ]

    conflits = []
    for verification in verifications:
        if verification is None:
            continue
        requete, libelle = verification
        existants = list((await session.execute(requete)).scalars())
        for creneau in existants:
            conflits.append(
                {
                    "type": libelle,
                    "creneau_id": str(creneau.id),
                    "jour": creneau.jour.value,
                    "heure_debut": creneau.heure_debut.isoformat(),
                    "heure_fin": creneau.heure_fin.isoformat(),
                    "message": f"{libelle} déjà occupé sur ce créneau.",
                }
            )

    return {"conflit": bool(conflits), "conflits": conflits}


router.include_router(creneaux)


@router.post(
    "/seances/{identifiant}/appel",
    response_model=MessageReponse,
    tags=["Pédagogie"],
    summary="Saisir l'appel d'une séance",
)
async def saisir_appel(
    identifiant: uuid.UUID,
    demande: AppelDemande,
    session: SessionDep,
    contexte: ContexteDep,
) -> MessageReponse:
    contexte.exiger("presences", Action.CREATE)
    seance = await obtenir_ou_404(session, Seance, identifiant, "Séance")

    existantes = {
        presence.apprenant_id: presence
        for presence in (
            await session.execute(select(Presence).where(Presence.seance_id == identifiant))
        ).scalars()
    }

    for ligne in demande.lignes:
        presence = existantes.get(ligne.apprenant_id)
        if presence is None:
            presence = Presence(seance_id=identifiant, apprenant_id=ligne.apprenant_id)
            session.add(presence)
        presence.statut = ligne.statut
        presence.minutes_retard = ligne.minutes_retard
        presence.justification = ligne.justification
        presence.saisi_par_id = contexte.id

    seance.appel_fait = True
    seance.statut = StatutSeance.TENUE
    await session.flush()

    return MessageReponse(message="Appel enregistré.", details={"lignes": len(demande.lignes)})


@router.get(
    "/seances/{identifiant}/presences",
    response_model=list[PresenceLecture],
    tags=["Pédagogie"],
    summary="Présences d'une séance",
)
async def presences_seance(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[Presence]:
    contexte.exiger("presences", Action.READ)
    await exiger_seance_dans_la_portee(session, contexte, identifiant)
    stmt = select(Presence).where(Presence.seance_id == identifiant)
    return list((await session.execute(stmt)).scalars())


@router.get(
    "/classes/{identifiant}/seances",
    tags=["Pédagogie"],
    summary="Séances programmées d'une classe",
    description="Séances triées de la plus récente à la plus ancienne, avec l'état de l'appel.",
)
async def seances_classe(
    identifiant: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
    depuis: Annotated[date | None, Query()] = None,
    jusqua: Annotated[date | None, Query()] = None,
    appel_fait: Annotated[bool | None, Query()] = None,
    limite: Annotated[int, Query(ge=1, le=200)] = 60,
) -> list[dict]:
    contexte.exiger("presences", Action.READ)
    await exiger_classe_dans_la_portee(session, contexte, identifiant)

    # Comptages de présences agrégés en sous-requête : une seule requête suffit.
    saisies = (
        select(
            Presence.seance_id.label("seance_id"),
            func.count().label("saisies"),
            func.sum(case((Presence.statut == StatutPresence.PRESENT, 1), else_=0)).label(
                "presents"
            ),
            func.sum(
                case(
                    (
                        Presence.statut.in_(
                            (
                                StatutPresence.ABSENT,
                                StatutPresence.ABSENCE_JUSTIFIEE,
                                StatutPresence.ABSENCE_INJUSTIFIEE,
                            )
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("absents"),
            func.sum(case((Presence.statut == StatutPresence.RETARD, 1), else_=0)).label("retards"),
        )
        .group_by(Presence.seance_id)
        .subquery()
    )

    stmt = (
        select(Seance, saisies.c.saisies, saisies.c.presents, saisies.c.absents, saisies.c.retards)
        .outerjoin(saisies, saisies.c.seance_id == Seance.id)
        .where(Seance.classe_id == identifiant)
        .order_by(Seance.date_seance.desc(), Seance.heure_debut.desc())
        .limit(limite)
    )
    if depuis:
        stmt = stmt.where(Seance.date_seance >= depuis)
    if jusqua:
        stmt = stmt.where(Seance.date_seance <= jusqua)
    if appel_fait is not None:
        stmt = stmt.where(Seance.appel_fait.is_(appel_fait))

    return [
        {
            "id": str(seance.id),
            "date_seance": seance.date_seance.isoformat(),
            "heure_debut": seance.heure_debut.strftime("%H:%M"),
            "heure_fin": seance.heure_fin.strftime("%H:%M"),
            "matiere_libelle": seance.matiere.libelle if seance.matiere else None,
            "enseignant_nom": seance.enseignant.nom_complet if seance.enseignant else None,
            "statut": seance.statut.value,
            "appel_fait": seance.appel_fait,
            "contenu_seance": seance.contenu_seance,
            "saisies": int(saisies_nombre or 0),
            "presents": int(presents or 0),
            "absents": int(absents or 0),
            "retards": int(retards or 0),
        }
        for seance, saisies_nombre, presents, absents, retards in (
            await session.execute(stmt)
        ).all()
    ]


@router.get(
    "/classes/{identifiant}/assiduite",
    tags=["Pédagogie"],
    summary="Assiduité d'une classe",
    description="Taux de présence par apprenant sur une période.",
)
async def assiduite_classe(
    identifiant: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
    periode_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[dict]:
    contexte.exiger("presences", Action.READ)
    await exiger_classe_dans_la_portee(session, contexte, identifiant)
    stmt = (
        select(SyntheseAssiduite, Apprenant)
        .join(Apprenant, Apprenant.id == SyntheseAssiduite.apprenant_id)
        .where(SyntheseAssiduite.classe_id == identifiant)
        .order_by(SyntheseAssiduite.taux_presence)
    )
    if periode_id:
        stmt = stmt.where(SyntheseAssiduite.periode_id == periode_id)

    return [
        {
            "apprenant_id": str(apprenant.id),
            "nom_complet": apprenant.nom_complet,
            "seances": synthese.seances_totales,
            "presences": synthese.presences,
            "absences_justifiees": synthese.absences_justifiees,
            "absences_injustifiees": synthese.absences_injustifiees,
            "retards": synthese.retards,
            "taux_presence": synthese.taux_presence,
            "alerte": synthese.taux_presence < 80,
        }
        for synthese, apprenant in (await session.execute(stmt)).all()
    ]


@router.post(
    "/classes/{identifiant}/seances",
    tags=["Pédagogie"],
    status_code=status.HTTP_201_CREATED,
    summary="Programmer une séance à partir d'un créneau",
)
async def programmer_seance(
    identifiant: uuid.UUID,
    creneau_id: Annotated[uuid.UUID, Query()],
    date_seance: Annotated[date, Query()],
    session: SessionDep,
    contexte: ContexteDep,
) -> dict:
    contexte.exiger("emploi_du_temps", Action.CREATE)
    creneau = await obtenir_ou_404(session, CreneauEmploiDuTemps, creneau_id, "Créneau")
    if creneau.classe_id != identifiant:
        raise BusinessRuleError("Ce créneau n'appartient pas à la classe indiquée.")

    periode = (
        await session.execute(
            select(Periode)
            .where(Periode.date_debut <= date_seance, Periode.date_fin >= date_seance)
            .limit(1)
        )
    ).scalar_one_or_none()

    seance = Seance(
        creneau_id=creneau.id,
        classe_id=identifiant,
        matiere_id=creneau.matiere_id,
        enseignant_id=creneau.enseignant_id,
        salle_id=creneau.salle_id,
        periode_id=periode.id if periode else None,
        date_seance=date_seance,
        heure_debut=creneau.heure_debut,
        heure_fin=creneau.heure_fin,
    )
    session.add(seance)
    await session.flush()
    return {"id": str(seance.id), "date_seance": date_seance.isoformat()}


@router.get(
    "/statistiques/scolarite",
    tags=["Scolarité"],
    summary="Statistiques de scolarisation",
)
async def statistiques_scolarite(
    session: SessionDep,
    contexte: ContexteDep,
    annee_id: Annotated[uuid.UUID | None, Query()] = None,
) -> dict:
    contexte.exiger("analytics", Action.READ)
    exiger_pilotage(contexte)

    stmt = select(func.count()).select_from(Inscription)
    if annee_id:
        stmt = stmt.where(Inscription.annee_id == annee_id)
    total = int((await session.execute(stmt)).scalar_one())

    stmt = (
        select(Apprenant.sexe, func.count())
        .join(Inscription, Inscription.apprenant_id == Apprenant.id)
        .group_by(Apprenant.sexe)
    )
    if annee_id:
        stmt = stmt.where(Inscription.annee_id == annee_id)
    par_sexe = {sexe.value: nombre for sexe, nombre in (await session.execute(stmt)).all()}

    stmt = select(Inscription.statut, func.count()).group_by(Inscription.statut)
    if annee_id:
        stmt = stmt.where(Inscription.annee_id == annee_id)
    par_statut = {statut.value: nombre for statut, nombre in (await session.execute(stmt)).all()}

    filles = par_sexe.get("FEMININ", 0)
    return {
        "inscriptions": total,
        "par_sexe": par_sexe,
        "taux_filles": taux(filles, total),
        "par_statut": par_statut,
        "calcule_le": datetime.now(UTC).isoformat(),
    }
