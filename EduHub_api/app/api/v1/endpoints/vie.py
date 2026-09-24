"""Vie étudiante : orientation, bourses, transport, logement, bibliothèque, apprentissage."""

import uuid
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.crud import creer_routeur_crud, obtenir_ou_404
from app.api.deps import ContexteDep, SessionDep
from app.core.enums import Action, StatutPaiement
from app.core.exceptions import BusinessRuleError, ConflictError
from app.engines import workflow
from app.engines.search import DescripteurChamp
from app.models.apprenant import Apprenant
from app.models.apprentissage import (
    CentreAlphabetisation,
    Cours,
    Lecon,
    ModuleCours,
    ParcoursAlphabetisation,
    ProgressionApprentissage,
    RessourcePedagogique,
)
from app.models.orientation import (
    CampagneOrientation,
    DossierOrientation,
    Formation,
    StatutVoeu,
    VoeuOrientation,
)
from app.models.projet import (
    CandidatureOffre,
    Chercheur,
    Entreprise,
    Laboratoire,
    MembreProjet,
    Offre,
    Projet,
    ProjetRecherche,
    Publication,
    Stage,
    StatutCandidature,
)
from app.models.vie_etudiante import (
    AbonnementTransport,
    AideSociale,
    ArretTransport,
    AttributionLogement,
    CampagneSante,
    CandidatureBourse,
    CentreSante,
    Chambre,
    Conducteur,
    Exemplaire,
    LigneTransport,
    Livre,
    Menu,
    Pret,
    ProgrammeBourse,
    RendezVousSante,
    Residence,
    StatutCandidatureBourse,
    Trajet,
    Vehicule,
)
from app.schemas.base import MessageReponse
from app.schemas.scolarite import TransitionDemande
from app.schemas.vie import (
    AbonnementCreation,
    AbonnementLecture,
    AdhesionProjet,
    AideSocialeLecture,
    ArretLecture,
    CampagneSanteLecture,
    CandidatureBourseCreation,
    CandidatureBourseLecture,
    CandidatureOffreCreation,
    CandidatureOffreLecture,
    CentreAlphabetisationLecture,
    CentreSanteEcriture,
    CentreSanteLecture,
    ChambreLecture,
    ChercheurLecture,
    CoursEcriture,
    CoursLecture,
    DemandeLogement,
    DossierOrientationCreation,
    DossierOrientationLecture,
    EntrepriseEcriture,
    EntrepriseLecture,
    FormationEcriture,
    FormationLecture,
    LaboratoireLecture,
    LigneTransportEcriture,
    LigneTransportLecture,
    LivreEcriture,
    LivreLecture,
    MenuLecture,
    OffreEcriture,
    OffreLecture,
    ParcoursAlphabetisationLecture,
    PretCreation,
    PretLecture,
    ProgrammeBourseEcriture,
    ProgrammeBourseLecture,
    ProgressionLecture,
    ProjetEcriture,
    ProjetLecture,
    ProjetRechercheLecture,
    PublicationLecture,
    RendezVousLecture,
    ResidenceLecture,
    RessourceLecture,
    StageLecture,
    TrajetTempsReel,
    VehiculeLecture,
)
from app.utils.codes import generer_reference

router = APIRouter()


# ------------------------------------------------------------------
#  Orientation
# ------------------------------------------------------------------

router.include_router(
    creer_routeur_crud(
        modele=Formation,
        schema_lecture=FormationLecture,
        schema_creation=FormationEcriture,
        schema_maj=FormationEcriture,
        prefixe="/formations",
        tag="Orientation",
        ressource="orientation",
        libelle_singulier="formation",
        libelle_pluriel="formations",
        champs_recherche=("code", "intitule", "debouches"),
        tri_defaut="intitule",
        champs_filtrables=(
            DescripteurChamp("code", "Code", Formation.code),
            DescripteurChamp("intitule", "Intitulé", Formation.intitule),
            DescripteurChamp(
                "etablissement_id", "Établissement", Formation.etablissement_id, "uuid"
            ),
            DescripteurChamp("filiere_id", "Filière", Formation.filiere_id, "uuid"),
            DescripteurChamp("places_offertes", "Places", Formation.places_offertes, "nombre"),
            DescripteurChamp(
                "moyenne_minimale", "Moyenne minimale", Formation.moyenne_minimale, "nombre"
            ),
            DescripteurChamp("ouverte", "Ouverte", Formation.ouverte, "booleen"),
        ),
    )
)

orientation = APIRouter(prefix="/orientation", tags=["Orientation"])


@orientation.get("/campagnes", summary="Campagnes d'orientation")
async def campagnes(session: SessionDep, contexte: ContexteDep) -> list[dict]:
    contexte.exiger("orientation", Action.READ)
    stmt = select(CampagneOrientation).order_by(CampagneOrientation.date_ouverture.desc())
    return [
        {
            "id": str(campagne.id),
            "code": campagne.code,
            "libelle": campagne.libelle,
            "date_ouverture": campagne.date_ouverture.isoformat(),
            "date_fermeture": campagne.date_fermeture.isoformat(),
            "nombre_voeux_max": campagne.nombre_voeux_max,
            "ouverte": campagne.ouverte,
        }
        for campagne in (await session.execute(stmt)).scalars()
    ]


@orientation.post(
    "/dossiers",
    response_model=DossierOrientationLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Déposer un dossier d'orientation",
    description="Enregistre les vœux d'un candidat, classés par ordre de préférence.",
)
async def deposer_dossier(
    donnees: DossierOrientationCreation,
    session: SessionDep,
    contexte: ContexteDep,
) -> DossierOrientation:
    contexte.exiger("orientation", Action.CREATE)
    campagne = await obtenir_ou_404(session, CampagneOrientation, donnees.campagne_id, "Campagne")
    if not campagne.ouverte:
        raise BusinessRuleError("Cette campagne d'orientation est close.")
    if len(donnees.voeux) > campagne.nombre_voeux_max:
        raise BusinessRuleError(
            f"La campagne autorise au plus {campagne.nombre_voeux_max} vœux.",
            details={"voeux_soumis": len(donnees.voeux)},
        )

    existant = (
        await session.execute(
            select(DossierOrientation).where(
                DossierOrientation.campagne_id == donnees.campagne_id,
                DossierOrientation.apprenant_id == donnees.apprenant_id,
            )
        )
    ).scalar_one_or_none()
    if existant is not None:
        raise ConflictError("Un dossier existe déjà pour cet apprenant sur cette campagne.")

    dossier = DossierOrientation(**donnees.model_dump(exclude={"voeux"}), statut=StatutVoeu.SOUMIS)
    session.add(dossier)
    await session.flush()

    for voeu in donnees.voeux:
        session.add(
            VoeuOrientation(
                dossier_id=dossier.id,
                formation_id=voeu.formation_id,
                rang=voeu.rang,
                statut=StatutVoeu.SOUMIS,
            )
        )

    await session.flush()
    return dossier


@orientation.post(
    "/campagnes/{identifiant}/affecter",
    response_model=MessageReponse,
    summary="Affecter les candidats aux formations",
    description=(
        "Parcourt les dossiers par mérite décroissant et attribue à chacun son vœu "
        "le mieux placé encore disponible."
    ),
)
async def affecter(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> MessageReponse:
    contexte.exiger("orientation", Action.ASSIGN)
    await obtenir_ou_404(session, CampagneOrientation, identifiant, "Campagne")

    stmt = (
        select(DossierOrientation)
        .where(DossierOrientation.campagne_id == identifiant)
        .options(selectinload(DossierOrientation.voeux))
        .order_by(DossierOrientation.moyenne_bac.desc().nullslast())
    )
    dossiers = list((await session.execute(stmt)).scalars().unique())

    formations = {
        formation.id: formation
        for formation in (await session.execute(select(Formation))).scalars()
    }

    affectes = 0
    en_attente = 0
    for dossier in dossiers:
        attribue = False
        for voeu in sorted(dossier.voeux, key=lambda item: item.rang):
            formation = formations.get(voeu.formation_id)
            if formation is None or not formation.ouverte:
                voeu.statut = StatutVoeu.REFUSE
                continue
            if formation.places_pourvues >= formation.places_offertes:
                voeu.statut = StatutVoeu.LISTE_ATTENTE
                continue
            if (
                formation.moyenne_minimale is not None
                and (dossier.moyenne_bac or 0) < formation.moyenne_minimale
            ):
                voeu.statut = StatutVoeu.REFUSE
                continue

            formation.places_pourvues += 1
            voeu.statut = StatutVoeu.ACCEPTE
            dossier.formation_affectee_id = formation.id
            dossier.date_affectation = date.today()
            dossier.statut = StatutVoeu.ACCEPTE
            attribue = True
            affectes += 1
            break

        if not attribue:
            dossier.statut = StatutVoeu.LISTE_ATTENTE
            en_attente += 1

    await session.flush()
    return MessageReponse(
        message="Affectation effectuée.",
        details={"affectes": affectes, "liste_attente": en_attente, "dossiers": len(dossiers)},
    )


router.include_router(orientation)


# ------------------------------------------------------------------
#  Bourses et aides sociales
# ------------------------------------------------------------------

router.include_router(
    creer_routeur_crud(
        modele=ProgrammeBourse,
        schema_lecture=ProgrammeBourseLecture,
        schema_creation=ProgrammeBourseEcriture,
        schema_maj=ProgrammeBourseEcriture,
        prefixe="/programmes-bourse",
        tag="Bourses",
        ressource="bourses",
        libelle_singulier="programme de bourses",
        libelle_pluriel="programmes de bourses",
        champs_recherche=("code", "intitule"),
        tri_defaut="intitule",
        champs_filtrables=(
            DescripteurChamp("code", "Code", ProgrammeBourse.code),
            DescripteurChamp("intitule", "Intitulé", ProgrammeBourse.intitule),
            DescripteurChamp("ouvert", "Ouvert", ProgrammeBourse.ouvert, "booleen"),
            DescripteurChamp(
                "montant_mensuel", "Montant mensuel", ProgrammeBourse.montant_mensuel, "nombre"
            ),
            DescripteurChamp(
                "reserve_handicap", "Réservé handicap", ProgrammeBourse.reserve_handicap, "booleen"
            ),
        ),
    )
)

bourses = creer_routeur_crud(
    modele=CandidatureBourse,
    schema_lecture=CandidatureBourseLecture,
    schema_creation=None,
    schema_maj=None,
    prefixe="/candidatures-bourse",
    tag="Bourses",
    ressource="bourses",
    libelle_singulier="candidature de bourse",
    libelle_pluriel="candidatures de bourses",
    champs_recherche=("numero",),
    tri_defaut="numero",
    contrainte_unicite=None,
    champs_filtrables=(
        DescripteurChamp("numero", "Numéro", CandidatureBourse.numero),
        DescripteurChamp("programme_id", "Programme", CandidatureBourse.programme_id, "uuid"),
        DescripteurChamp("apprenant_id", "Apprenant", CandidatureBourse.apprenant_id, "uuid"),
        DescripteurChamp("statut", "Statut", CandidatureBourse.statut, "liste"),
        DescripteurChamp(
            "moyenne_reference", "Moyenne", CandidatureBourse.moyenne_reference, "nombre"
        ),
    ),
)


@bourses.post(
    "",
    response_model=CandidatureBourseLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Candidater à une bourse",
)
async def candidater_bourse(
    donnees: CandidatureBourseCreation,
    session: SessionDep,
    contexte: ContexteDep,
) -> CandidatureBourse:
    contexte.exiger("bourses", Action.CREATE)
    programme = await obtenir_ou_404(
        session, ProgrammeBourse, donnees.programme_id, "Programme de bourses"
    )
    if not programme.ouvert or date.today() > programme.date_cloture:
        raise BusinessRuleError("Les candidatures à ce programme sont closes.")

    existante = (
        await session.execute(
            select(CandidatureBourse).where(
                CandidatureBourse.programme_id == donnees.programme_id,
                CandidatureBourse.apprenant_id == donnees.apprenant_id,
            )
        )
    ).scalar_one_or_none()
    if existante is not None:
        raise ConflictError("Une candidature a déjà été déposée pour ce programme.")

    candidature = CandidatureBourse(
        numero=generer_reference("BRS"),
        statut=StatutCandidatureBourse.SOUMISE,
        date_soumission=date.today(),
        **donnees.model_dump(),
    )
    session.add(candidature)
    await session.flush()
    return candidature


@bourses.post(
    "/{identifiant}/transition",
    response_model=CandidatureBourseLecture,
    summary="Faire avancer une candidature de bourse",
    description=(
        "Actions : soumettre, evaluer, declarer_incomplete, completer, "
        "preselectionner, attribuer, rejeter, suspendre, reactiver, cloturer."
    ),
)
async def transition_bourse(
    identifiant: uuid.UUID,
    demande: TransitionDemande,
    session: SessionDep,
    contexte: ContexteDep,
) -> CandidatureBourse:
    contexte.exiger("bourses", Action.VALIDATE)
    candidature = await obtenir_ou_404(
        session, CandidatureBourse, identifiant, "Candidature de bourse"
    )

    transition = await workflow.appliquer(
        session,
        workflow.WORKFLOW_BOURSE,
        entite_type="candidatures_bourse",
        entite_id=candidature.id,
        statut_actuel=candidature.statut.value,
        action=demande.action,
        acteur_id=contexte.id,
        acteur_nom=contexte.utilisateur.nom_complet,
        roles=contexte.roles,
        commentaire=demande.commentaire,
    )

    candidature.statut = StatutCandidatureBourse(transition.vers)
    candidature.date_decision = date.today()
    if candidature.statut is StatutCandidatureBourse.REJETEE:
        candidature.motif_rejet = demande.motif or demande.commentaire
    if candidature.statut is StatutCandidatureBourse.ATTRIBUEE:
        programme = await session.get(ProgrammeBourse, candidature.programme_id)
        if programme is not None:
            if programme.places_attribuees >= programme.places > 0:
                raise BusinessRuleError("Toutes les places du programme sont attribuées.")
            programme.places_attribuees += 1
            candidature.montant_attribue = programme.montant_mensuel
            candidature.date_debut_versement = date.today()
            candidature.date_fin_versement = date.today() + timedelta(
                days=30 * programme.duree_mois
            )

    await session.flush()
    return candidature


router.include_router(bourses)

router.include_router(
    creer_routeur_crud(
        modele=AideSociale,
        schema_lecture=AideSocialeLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/aides-sociales",
        tag="Bourses",
        ressource="bourses",
        libelle_singulier="aide sociale",
        libelle_pluriel="aides sociales",
        champs_recherche=("numero", "libelle"),
        tri_defaut="numero",
        contrainte_unicite=None,
        champs_filtrables=(
            DescripteurChamp("type_aide", "Type d'aide", AideSociale.type_aide, "liste"),
            DescripteurChamp("apprenant_id", "Apprenant", AideSociale.apprenant_id, "uuid"),
            DescripteurChamp("statut", "Statut", AideSociale.statut, "liste"),
            DescripteurChamp("montant", "Montant", AideSociale.montant, "nombre"),
        ),
    )
)


# ------------------------------------------------------------------
#  Transport
# ------------------------------------------------------------------

lignes_transport = creer_routeur_crud(
    modele=LigneTransport,
    schema_lecture=LigneTransportLecture,
    schema_creation=LigneTransportEcriture,
    schema_maj=LigneTransportEcriture,
    prefixe="/transport/lignes",
    tag="Transport",
    ressource="transport",
    libelle_singulier="ligne de transport",
    libelle_pluriel="lignes de transport",
    champs_recherche=("code", "libelle", "origine", "destination"),
    champs_filtrables=(
        DescripteurChamp("code", "Code", LigneTransport.code),
        DescripteurChamp("libelle", "Libellé", LigneTransport.libelle),
        DescripteurChamp(
            "etablissement_id", "Établissement", LigneTransport.etablissement_id, "uuid"
        ),
        DescripteurChamp("tarif", "Tarif", LigneTransport.tarif, "nombre"),
        DescripteurChamp("active", "Active", LigneTransport.active, "booleen"),
    ),
)


@lignes_transport.get(
    "/{identifiant}/arrets",
    response_model=list[ArretLecture],
    summary="Arrêts d'une ligne",
)
async def arrets_ligne(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[ArretTransport]:
    contexte.exiger("transport", Action.READ)
    stmt = (
        select(ArretTransport)
        .where(ArretTransport.ligne_id == identifiant)
        .order_by(ArretTransport.ordre)
    )
    return list((await session.execute(stmt)).scalars())


@lignes_transport.get(
    "/{identifiant}/temps-reel",
    response_model=list[TrajetTempsReel],
    summary="Suivi des trajets d'une ligne",
    description="Position simulée, prochain arrêt, temps d'attente et places disponibles.",
)
async def temps_reel(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[TrajetTempsReel]:
    contexte.exiger("transport", Action.READ)
    stmt = (
        select(Trajet, LigneTransport, Vehicule, Conducteur, ArretTransport)
        .join(LigneTransport, LigneTransport.id == Trajet.ligne_id)
        .outerjoin(Vehicule, Vehicule.id == Trajet.vehicule_id)
        .outerjoin(Conducteur, Conducteur.id == Trajet.conducteur_id)
        .outerjoin(ArretTransport, ArretTransport.id == Trajet.prochain_arret_id)
        .where(Trajet.ligne_id == identifiant, Trajet.date_trajet >= date.today())
        .order_by(Trajet.heure_depart_prevue)
    )

    return [
        TrajetTempsReel(
            id=trajet.id,
            ligne=ligne.libelle,
            ligne_code=ligne.code,
            vehicule=vehicule.code if vehicule else None,
            conducteur=conducteur.nom_complet if conducteur else None,
            sens=trajet.sens,
            statut=trajet.statut,
            heure_depart_prevue=trajet.heure_depart_prevue,
            prochain_arret=arret.nom if arret else None,
            minutes_avant_prochain_arret=trajet.minutes_avant_prochain_arret,
            places_occupees=trajet.places_occupees,
            places_disponibles=(vehicule.places - trajet.places_occupees) if vehicule else None,
            retard_minutes=trajet.retard_minutes,
            latitude=trajet.latitude_actuelle,
            longitude=trajet.longitude_actuelle,
        )
        for trajet, ligne, vehicule, conducteur, arret in (await session.execute(stmt)).all()
    ]


router.include_router(lignes_transport)

router.include_router(
    creer_routeur_crud(
        modele=Vehicule,
        schema_lecture=VehiculeLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/transport/vehicules",
        tag="Transport",
        ressource="transport",
        libelle_singulier="véhicule",
        libelle_pluriel="véhicules",
        champs_recherche=("immatriculation", "code", "marque"),
        tri_defaut="code",
        contrainte_unicite="immatriculation",
        champs_filtrables=(
            DescripteurChamp("immatriculation", "Immatriculation", Vehicule.immatriculation),
            DescripteurChamp("type_vehicule", "Type", Vehicule.type_vehicule, "liste"),
            DescripteurChamp("statut", "Statut", Vehicule.statut, "liste"),
            DescripteurChamp("places", "Places", Vehicule.places, "nombre"),
            DescripteurChamp("places_pmr", "Places PMR", Vehicule.places_pmr, "nombre"),
        ),
    )
)

abonnements = creer_routeur_crud(
    modele=AbonnementTransport,
    schema_lecture=AbonnementLecture,
    schema_creation=None,
    schema_maj=None,
    prefixe="/transport/abonnements",
    tag="Transport",
    ressource="transport",
    libelle_singulier="abonnement",
    libelle_pluriel="abonnements",
    champs_recherche=("numero_carte",),
    tri_defaut="numero_carte",
    contrainte_unicite="numero_carte",
    champs_filtrables=(
        DescripteurChamp("numero_carte", "Numéro de carte", AbonnementTransport.numero_carte),
        DescripteurChamp("apprenant_id", "Apprenant", AbonnementTransport.apprenant_id, "uuid"),
        DescripteurChamp("ligne_id", "Ligne", AbonnementTransport.ligne_id, "uuid"),
        DescripteurChamp("actif", "Actif", AbonnementTransport.actif, "booleen"),
    ),
)


@abonnements.post(
    "",
    response_model=AbonnementLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Souscrire un abonnement de transport",
)
async def souscrire_abonnement(
    donnees: AbonnementCreation,
    session: SessionDep,
    contexte: ContexteDep,
) -> AbonnementTransport:
    contexte.exiger("transport", Action.CREATE)
    ligne = await obtenir_ou_404(session, LigneTransport, donnees.ligne_id, "Ligne")
    await obtenir_ou_404(session, Apprenant, donnees.apprenant_id, "Apprenant")

    total = int(
        (await session.execute(select(func.count()).select_from(AbonnementTransport))).scalar_one()
    )
    abonnement = AbonnementTransport(
        numero_carte=f"TR{total + 1:08d}",
        montant=ligne.tarif_abonnement,
        statut_paiement=StatutPaiement.EN_ATTENTE,
        **donnees.model_dump(),
    )
    session.add(abonnement)
    await session.flush()
    return abonnement


router.include_router(abonnements)


# ------------------------------------------------------------------
#  Logement et restauration
# ------------------------------------------------------------------

residences = creer_routeur_crud(
    modele=Residence,
    schema_lecture=ResidenceLecture,
    schema_creation=None,
    schema_maj=None,
    prefixe="/residences",
    tag="Vie étudiante",
    ressource="logement",
    libelle_singulier="résidence",
    libelle_pluriel="résidences",
    champs_recherche=("code", "nom"),
    champs_filtrables=(
        DescripteurChamp("code", "Code", Residence.code),
        DescripteurChamp("nom", "Nom", Residence.nom),
        DescripteurChamp("capacite", "Capacité", Residence.capacite, "nombre"),
        DescripteurChamp(
            "accessible_handicap", "Accessible", Residence.accessible_handicap, "booleen"
        ),
    ),
)


@residences.get(
    "/{identifiant}/chambres",
    response_model=list[ChambreLecture],
    summary="Chambres d'une résidence",
)
async def chambres(
    identifiant: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
    disponibles_seulement: Annotated[bool, Query()] = False,
) -> list[Chambre]:
    contexte.exiger("logement", Action.READ)
    stmt = select(Chambre).where(Chambre.residence_id == identifiant).order_by(Chambre.numero)
    if disponibles_seulement:
        stmt = stmt.where(Chambre.lits_occupes < Chambre.nombre_lits)
    return list((await session.execute(stmt)).scalars())


@residences.post(
    "/attributions",
    response_model=MessageReponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attribuer un lit à un apprenant",
)
async def attribuer_logement(
    donnees: DemandeLogement,
    session: SessionDep,
    contexte: ContexteDep,
) -> MessageReponse:
    contexte.exiger("logement", Action.ASSIGN)
    chambre = await obtenir_ou_404(session, Chambre, donnees.chambre_id, "Chambre")
    if chambre.lits_occupes >= chambre.nombre_lits:
        raise BusinessRuleError("Cette chambre est complète.")

    chambre.lits_occupes += 1
    chambre.disponible = chambre.lits_occupes < chambre.nombre_lits

    residence = await session.get(Residence, chambre.residence_id)
    if residence is not None:
        residence.places_occupees += 1

    session.add(
        AttributionLogement(
            apprenant_id=donnees.apprenant_id,
            chambre_id=donnees.chambre_id,
            numero_lit=chambre.lits_occupes,
            date_debut=donnees.date_debut,
            date_fin=donnees.date_fin,
            statut=StatutCandidatureBourse.ATTRIBUEE,
            caution=chambre.tarif_mensuel,
        )
    )
    await session.flush()
    return MessageReponse(
        message="Logement attribué.",
        details={"chambre": chambre.numero, "lit": chambre.lits_occupes},
    )


router.include_router(residences)


@router.get(
    "/restauration/menus",
    response_model=list[MenuLecture],
    tags=["Vie étudiante"],
    summary="Menus de la restauration",
)
async def menus(
    session: SessionDep,
    contexte: ContexteDep,
    restaurant_id: Annotated[uuid.UUID | None, Query()] = None,
    depuis: Annotated[date | None, Query()] = None,
) -> list[Menu]:
    contexte.exiger("restauration", Action.READ)
    stmt = select(Menu).order_by(Menu.date_service).limit(60)
    if restaurant_id:
        stmt = stmt.where(Menu.restaurant_id == restaurant_id)
    stmt = stmt.where(Menu.date_service >= (depuis or date.today()))
    return list((await session.execute(stmt)).scalars())


# ------------------------------------------------------------------
#  Bibliothèque
# ------------------------------------------------------------------

router.include_router(
    creer_routeur_crud(
        modele=Livre,
        schema_lecture=LivreLecture,
        schema_creation=LivreEcriture,
        schema_maj=LivreEcriture,
        prefixe="/bibliotheque/livres",
        tag="Bibliothèque",
        ressource="bibliotheque",
        libelle_singulier="ouvrage",
        libelle_pluriel="ouvrages",
        champs_recherche=("titre", "auteur", "isbn"),
        tri_defaut="titre",
        contrainte_unicite=None,
        champs_filtrables=(
            DescripteurChamp("titre", "Titre", Livre.titre),
            DescripteurChamp("auteur", "Auteur", Livre.auteur),
            DescripteurChamp("categorie", "Catégorie", Livre.categorie, "liste"),
            DescripteurChamp("langue", "Langue", Livre.langue, "liste"),
            DescripteurChamp("annee_publication", "Année", Livre.annee_publication, "nombre"),
            DescripteurChamp(
                "format_accessible", "Format accessible", Livre.format_accessible, "booleen"
            ),
            DescripteurChamp("audio_disponible", "Audio", Livre.audio_disponible, "booleen"),
            DescripteurChamp("braille_disponible", "Braille", Livre.braille_disponible, "booleen"),
        ),
    )
)

prets = creer_routeur_crud(
    modele=Pret,
    schema_lecture=PretLecture,
    schema_creation=None,
    schema_maj=None,
    prefixe="/bibliotheque/prets",
    tag="Bibliothèque",
    ressource="bibliotheque",
    libelle_singulier="prêt",
    libelle_pluriel="prêts",
    champs_recherche=(),
    tri_defaut="date_retour_prevue",
    contrainte_unicite=None,
    champs_filtrables=(
        DescripteurChamp("apprenant_id", "Apprenant", Pret.apprenant_id, "uuid"),
        DescripteurChamp("rendu", "Rendu", Pret.rendu, "booleen"),
        DescripteurChamp("jours_retard", "Jours de retard", Pret.jours_retard, "nombre"),
        DescripteurChamp("date_pret", "Date de prêt", Pret.date_pret, "date"),
    ),
)


@prets.post(
    "",
    response_model=PretLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Enregistrer un prêt",
)
async def emprunter(donnees: PretCreation, session: SessionDep, contexte: ContexteDep) -> Pret:
    contexte.exiger("bibliotheque", Action.CREATE)
    exemplaire = await obtenir_ou_404(session, Exemplaire, donnees.exemplaire_id, "Exemplaire")
    if not exemplaire.disponible:
        raise BusinessRuleError("Cet exemplaire est déjà emprunté.")

    exemplaire.disponible = False
    pret = Pret(
        exemplaire_id=donnees.exemplaire_id,
        apprenant_id=donnees.apprenant_id,
        enseignant_id=donnees.enseignant_id,
        date_pret=date.today(),
        date_retour_prevue=date.today() + timedelta(days=donnees.duree_jours),
    )
    session.add(pret)
    await session.flush()
    return pret


@prets.post(
    "/{identifiant}/retour",
    response_model=PretLecture,
    summary="Enregistrer un retour",
    description="Calcule automatiquement le retard et la pénalité associée.",
)
async def retourner(identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep) -> Pret:
    contexte.exiger("bibliotheque", Action.UPDATE)
    pret = await obtenir_ou_404(session, Pret, identifiant, "Prêt")
    if pret.rendu:
        raise BusinessRuleError("Ce prêt a déjà été soldé.")

    pret.date_retour_effective = date.today()
    pret.jours_retard = max(0, (date.today() - pret.date_retour_prevue).days)
    pret.penalite = float(pret.jours_retard * 50)
    pret.rendu = True

    exemplaire = await session.get(Exemplaire, pret.exemplaire_id)
    if exemplaire is not None:
        exemplaire.disponible = True

    await session.flush()
    return pret


router.include_router(prets)


# ------------------------------------------------------------------
#  Apprentissage en ligne
# ------------------------------------------------------------------

cours = creer_routeur_crud(
    modele=Cours,
    schema_lecture=CoursLecture,
    schema_creation=CoursEcriture,
    schema_maj=CoursEcriture,
    prefixe="/cours",
    tag="Apprentissage",
    ressource="apprentissage",
    libelle_singulier="cours",
    libelle_pluriel="cours",
    champs_recherche=("code", "titre", "description"),
    tri_defaut="titre",
    champs_filtrables=(
        DescripteurChamp("code", "Code", Cours.code),
        DescripteurChamp("titre", "Titre", Cours.titre),
        DescripteurChamp("matiere_id", "Matière", Cours.matiere_id, "uuid"),
        DescripteurChamp("niveau_id", "Niveau", Cours.niveau_id, "uuid"),
        DescripteurChamp("langue", "Langue", Cours.langue, "liste"),
        DescripteurChamp("statut", "Statut", Cours.statut, "liste"),
        DescripteurChamp("version_audio", "Version audio", Cours.version_audio, "booleen"),
        DescripteurChamp(
            "disponible_hors_ligne", "Hors ligne", Cours.disponible_hors_ligne, "booleen"
        ),
    ),
)


@cours.get(
    "/{identifiant}/plan",
    summary="Plan d'un cours",
    description="Modules, leçons et ressources associées.",
)
async def plan_cours(identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep) -> dict:
    contexte.exiger("apprentissage", Action.READ)
    cours_objet = await obtenir_ou_404(session, Cours, identifiant, "Cours")

    stmt = (
        select(ModuleCours)
        .where(ModuleCours.cours_id == identifiant)
        .options(selectinload(ModuleCours.lecons).selectinload(Lecon.ressources))
        .order_by(ModuleCours.ordre)
    )
    modules = list((await session.execute(stmt)).scalars().unique())

    return {
        "cours": {
            "id": str(cours_objet.id),
            "titre": cours_objet.titre,
            "duree_heures": cours_objet.duree_heures,
            "accessibilite": {
                "version_audio": cours_objet.version_audio,
                "transcription": cours_objet.transcription_disponible,
                "sous_titres": cours_objet.sous_titres_disponibles,
                "hors_ligne": cours_objet.disponible_hors_ligne,
            },
        },
        "modules": [
            {
                "id": str(module.id),
                "titre": module.titre,
                "ordre": module.ordre,
                "duree_minutes": module.duree_minutes,
                "lecons": [
                    {
                        "id": str(lecon.id),
                        "titre": lecon.titre,
                        "ordre": lecon.ordre,
                        "duree_minutes": lecon.duree_minutes,
                        "audio_url": lecon.audio_url,
                        "contenu_simplifie": lecon.contenu_simplifie,
                        "ressources": [
                            {
                                "id": str(ressource.id),
                                "titre": ressource.titre,
                                "type": ressource.type_ressource.value,
                                "taille_ko": ressource.taille_ko,
                            }
                            for ressource in lecon.ressources
                        ],
                    }
                    for lecon in sorted(module.lecons, key=lambda item: item.ordre)
                ],
            }
            for module in modules
        ],
    }


@cours.get(
    "/{identifiant}/progression/{apprenant_id}",
    response_model=ProgressionLecture,
    summary="Progression d'un apprenant dans un cours",
)
async def progression(
    identifiant: uuid.UUID,
    apprenant_id: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
) -> ProgressionApprentissage:
    contexte.exiger("apprentissage", Action.READ)
    stmt = select(ProgressionApprentissage).where(
        ProgressionApprentissage.cours_id == identifiant,
        ProgressionApprentissage.apprenant_id == apprenant_id,
    )
    existante = (await session.execute(stmt)).scalar_one_or_none()
    if existante is not None:
        return existante

    total = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Lecon)
                .join(ModuleCours, ModuleCours.id == Lecon.module_id)
                .where(ModuleCours.cours_id == identifiant)
            )
        ).scalar_one()
    )
    nouvelle = ProgressionApprentissage(
        apprenant_id=apprenant_id, cours_id=identifiant, lecons_totales=total
    )
    session.add(nouvelle)
    await session.flush()
    return nouvelle


router.include_router(cours)

router.include_router(
    creer_routeur_crud(
        modele=RessourcePedagogique,
        schema_lecture=RessourceLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/ressources",
        tag="Apprentissage",
        ressource="apprentissage",
        libelle_singulier="ressource pédagogique",
        libelle_pluriel="ressources pédagogiques",
        champs_recherche=("code", "titre", "mots_cles"),
        tri_defaut="titre",
        champs_filtrables=(
            DescripteurChamp("titre", "Titre", RessourcePedagogique.titre),
            DescripteurChamp(
                "type_ressource", "Type", RessourcePedagogique.type_ressource, "liste"
            ),
            DescripteurChamp("matiere_id", "Matière", RessourcePedagogique.matiere_id, "uuid"),
            DescripteurChamp("niveau_id", "Niveau", RessourcePedagogique.niveau_id, "uuid"),
            DescripteurChamp("langue", "Langue", RessourcePedagogique.langue, "liste"),
            DescripteurChamp(
                "poids_leger",
                "Adapté connexion faible",
                RessourcePedagogique.poids_leger,
                "booleen",
            ),
        ),
    )
)


# ------------------------------------------------------------------
#  Projets, entreprises, offres et stages
# ------------------------------------------------------------------

projets = creer_routeur_crud(
    modele=Projet,
    schema_lecture=ProjetLecture,
    schema_creation=ProjetEcriture,
    schema_maj=ProjetEcriture,
    prefixe="/projets",
    tag="Projets",
    ressource="projets",
    libelle_singulier="projet",
    libelle_pluriel="projets",
    champs_recherche=("code", "titre", "domaine"),
    tri_defaut="titre",
    champs_filtrables=(
        DescripteurChamp("code", "Code", Projet.code),
        DescripteurChamp("titre", "Titre", Projet.titre),
        DescripteurChamp("domaine", "Domaine", Projet.domaine, "liste"),
        DescripteurChamp("statut", "Statut", Projet.statut, "liste"),
        DescripteurChamp("etablissement_id", "Établissement", Projet.etablissement_id, "uuid"),
        DescripteurChamp(
            "ouvert_candidatures", "Ouvert aux candidatures", Projet.ouvert_candidatures, "booleen"
        ),
        DescripteurChamp(
            "avancement_pourcentage", "Avancement", Projet.avancement_pourcentage, "nombre"
        ),
    ),
)


@projets.get(
    "/{identifiant}/equipe",
    summary="Équipe d'un projet",
)
async def equipe_projet(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[dict]:
    contexte.exiger("projets", Action.READ)
    stmt = select(MembreProjet).where(MembreProjet.projet_id == identifiant)
    return [
        {
            "id": str(membre.id),
            "nom_complet": membre.nom_complet,
            "role": membre.role.value,
            "competences": membre.competences,
            "actif": membre.actif,
        }
        for membre in (await session.execute(stmt)).scalars()
    ]


@projets.post(
    "/{identifiant}/rejoindre",
    response_model=MessageReponse,
    summary="Rejoindre un projet",
)
async def rejoindre_projet(
    identifiant: uuid.UUID,
    donnees: AdhesionProjet,
    session: SessionDep,
    contexte: ContexteDep,
) -> MessageReponse:
    contexte.exiger("projets", Action.CREATE)
    projet = await obtenir_ou_404(session, Projet, identifiant, "Projet")
    if not projet.ouvert_candidatures:
        raise BusinessRuleError("Ce projet n'accepte plus de nouveaux membres.")
    if projet.places_disponibles <= 0:
        raise BusinessRuleError("Toutes les places de l'équipe sont pourvues.")

    projet.places_disponibles -= 1
    session.add(
        MembreProjet(projet_id=identifiant, date_adhesion=date.today(), **donnees.model_dump())
    )
    await session.flush()
    return MessageReponse(message="Adhésion enregistrée.")


router.include_router(projets)

router.include_router(
    creer_routeur_crud(
        modele=Entreprise,
        schema_lecture=EntrepriseLecture,
        schema_creation=EntrepriseEcriture,
        schema_maj=EntrepriseEcriture,
        prefixe="/entreprises",
        tag="Emploi",
        ressource="entreprises",
        libelle_singulier="entreprise",
        libelle_pluriel="entreprises",
        champs_recherche=("code", "raison_sociale", "secteur_activite"),
        tri_defaut="raison_sociale",
        champs_filtrables=(
            DescripteurChamp("raison_sociale", "Raison sociale", Entreprise.raison_sociale),
            DescripteurChamp("secteur_activite", "Secteur", Entreprise.secteur_activite, "liste"),
            DescripteurChamp("commune_id", "Commune", Entreprise.commune_id, "uuid"),
            DescripteurChamp(
                "partenaire_officiel", "Partenaire", Entreprise.partenaire_officiel, "booleen"
            ),
            DescripteurChamp(
                "accueille_handicap", "Accueille handicap", Entreprise.accueille_handicap, "booleen"
            ),
        ),
    )
)

offres = creer_routeur_crud(
    modele=Offre,
    schema_lecture=OffreLecture,
    schema_creation=None,
    schema_maj=OffreEcriture,
    prefixe="/offres",
    tag="Emploi",
    ressource="emploi",
    libelle_singulier="offre",
    libelle_pluriel="offres",
    champs_recherche=("reference", "intitule", "domaine"),
    tri_defaut="date_publication",
    contrainte_unicite=None,
    champs_filtrables=(
        DescripteurChamp("intitule", "Intitulé", Offre.intitule),
        DescripteurChamp("entreprise_id", "Entreprise", Offre.entreprise_id, "uuid"),
        DescripteurChamp("type_contrat", "Type de contrat", Offre.type_contrat, "liste"),
        DescripteurChamp("domaine", "Domaine", Offre.domaine, "liste"),
        DescripteurChamp("commune_id", "Commune", Offre.commune_id, "uuid"),
        DescripteurChamp("gratification", "Gratification", Offre.gratification, "nombre"),
        DescripteurChamp("ouverte", "Ouverte", Offre.ouverte, "booleen"),
        DescripteurChamp("accessible_handicap", "Accessible", Offre.accessible_handicap, "booleen"),
    ),
)


@offres.post(
    "",
    response_model=OffreLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Publier une offre",
)
async def publier_offre(
    donnees: OffreEcriture, session: SessionDep, contexte: ContexteDep
) -> Offre:
    contexte.exiger("emploi", Action.CREATE)
    await obtenir_ou_404(session, Entreprise, donnees.entreprise_id, "Entreprise")
    valeurs = donnees.model_dump(exclude={"reference"})
    offre = Offre(
        reference=donnees.reference or generer_reference("OFF"),
        date_publication=date.today(),
        **valeurs,
    )
    session.add(offre)
    await session.flush()
    return offre


router.include_router(offres)

candidatures_offre = creer_routeur_crud(
    modele=CandidatureOffre,
    schema_lecture=CandidatureOffreLecture,
    schema_creation=None,
    schema_maj=None,
    prefixe="/candidatures-offre",
    tag="Emploi",
    ressource="emploi",
    libelle_singulier="candidature",
    libelle_pluriel="candidatures",
    champs_recherche=(),
    tri_defaut="date_candidature",
    contrainte_unicite=None,
    champs_filtrables=(
        DescripteurChamp("offre_id", "Offre", CandidatureOffre.offre_id, "uuid"),
        DescripteurChamp("apprenant_id", "Apprenant", CandidatureOffre.apprenant_id, "uuid"),
        DescripteurChamp("statut", "Statut", CandidatureOffre.statut, "liste"),
    ),
)


@candidatures_offre.post(
    "",
    response_model=CandidatureOffreLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Postuler à une offre",
)
async def postuler(
    donnees: CandidatureOffreCreation, session: SessionDep, contexte: ContexteDep
) -> CandidatureOffre:
    contexte.exiger("emploi", Action.CREATE)
    offre = await obtenir_ou_404(session, Offre, donnees.offre_id, "Offre")
    if not offre.ouverte:
        raise BusinessRuleError("Cette offre n'est plus ouverte.")
    if offre.date_limite and date.today() > offre.date_limite:
        raise BusinessRuleError("La date limite de candidature est dépassée.")

    existante = (
        await session.execute(
            select(CandidatureOffre).where(
                CandidatureOffre.offre_id == donnees.offre_id,
                CandidatureOffre.apprenant_id == donnees.apprenant_id,
            )
        )
    ).scalar_one_or_none()
    if existante is not None:
        raise ConflictError("Vous avez déjà postulé à cette offre.")

    candidature = CandidatureOffre(
        statut=StatutCandidature.ENVOYEE,
        date_candidature=date.today(),
        **donnees.model_dump(),
    )
    session.add(candidature)
    await session.flush()
    return candidature


router.include_router(candidatures_offre)

router.include_router(
    creer_routeur_crud(
        modele=Stage,
        schema_lecture=StageLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/stages",
        tag="Emploi",
        ressource="stages",
        libelle_singulier="stage",
        libelle_pluriel="stages",
        champs_recherche=("reference", "sujet"),
        tri_defaut="date_debut",
        contrainte_unicite=None,
        champs_filtrables=(
            DescripteurChamp("apprenant_id", "Apprenant", Stage.apprenant_id, "uuid"),
            DescripteurChamp("entreprise_id", "Entreprise", Stage.entreprise_id, "uuid"),
            DescripteurChamp("note_finale", "Note finale", Stage.note_finale, "nombre"),
            DescripteurChamp("valide", "Validé", Stage.valide, "booleen"),
        ),
    )
)


# ------------------------------------------------------------------
#  Santé scolaire
# ------------------------------------------------------------------

centres_sante = creer_routeur_crud(
    modele=CentreSante,
    schema_lecture=CentreSanteLecture,
    schema_creation=CentreSanteEcriture,
    schema_maj=CentreSanteEcriture,
    prefixe="/sante/centres",
    tag="Santé",
    ressource="sante",
    libelle_singulier="centre de santé",
    libelle_pluriel="centres de santé",
    champs_recherche=("code", "nom", "services"),
    tri_defaut="nom",
    champs_filtrables=(
        DescripteurChamp("code", "Code", CentreSante.code),
        DescripteurChamp("nom", "Nom", CentreSante.nom),
        DescripteurChamp("etablissement_id", "Établissement", CentreSante.etablissement_id, "uuid"),
        DescripteurChamp("nombre_agents", "Agents", CentreSante.nombre_agents, "nombre"),
        DescripteurChamp("actif", "Actif", CentreSante.actif, "booleen"),
    ),
)


@centres_sante.get(
    "/{identifiant}/rendez-vous",
    response_model=list[RendezVousLecture],
    summary="Rendez-vous d'un centre de santé",
    description="Les données médicales détaillées restent hors du système.",
)
async def rendez_vous_centre(
    identifiant: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
    limite: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[RendezVousSante]:
    contexte.exiger("sante", Action.READ)
    stmt = (
        select(RendezVousSante)
        .where(RendezVousSante.centre_sante_id == identifiant)
        .order_by(RendezVousSante.date_rdv.desc())
        .limit(limite)
    )
    return list((await session.execute(stmt)).scalars())


router.include_router(centres_sante)


@router.get(
    "/sante/campagnes",
    response_model=list[CampagneSanteLecture],
    tags=["Santé"],
    summary="Campagnes de santé scolaire",
    description="Vaccination, dépistage, hygiène, nutrition et sensibilisation.",
)
async def campagnes_sante(session: SessionDep, contexte: ContexteDep) -> list[CampagneSante]:
    contexte.exiger("sante", Action.READ)
    stmt = select(CampagneSante).order_by(CampagneSante.date_debut.desc())
    return list((await session.execute(stmt)).scalars())


# ------------------------------------------------------------------
#  Alphabétisation
# ------------------------------------------------------------------

centres_alphabetisation = creer_routeur_crud(
    modele=CentreAlphabetisation,
    schema_lecture=CentreAlphabetisationLecture,
    schema_creation=None,
    schema_maj=None,
    prefixe="/alphabetisation/centres",
    tag="Alphabétisation",
    ressource="apprentissage",
    libelle_singulier="centre d'alphabétisation",
    libelle_pluriel="centres d'alphabétisation",
    champs_recherche=("code", "nom", "responsable"),
    tri_defaut="nom",
    champs_filtrables=(
        DescripteurChamp("code", "Code", CentreAlphabetisation.code),
        DescripteurChamp("nom", "Nom", CentreAlphabetisation.nom),
        DescripteurChamp("commune_id", "Commune", CentreAlphabetisation.commune_id, "uuid"),
        DescripteurChamp(
            "langue_enseignement", "Langue", CentreAlphabetisation.langue_enseignement, "liste"
        ),
        DescripteurChamp(
            "nombre_apprenants", "Apprenants", CentreAlphabetisation.nombre_apprenants, "nombre"
        ),
    ),
)


@centres_alphabetisation.get(
    "/{identifiant}/parcours",
    response_model=list[ParcoursAlphabetisationLecture],
    summary="Parcours des apprenants d'un centre",
)
async def parcours_centre(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[ParcoursAlphabetisation]:
    contexte.exiger("apprentissage", Action.READ)
    stmt = (
        select(ParcoursAlphabetisation)
        .where(ParcoursAlphabetisation.centre_id == identifiant)
        .order_by(ParcoursAlphabetisation.progression_pourcentage.desc())
    )
    return list((await session.execute(stmt)).scalars())


router.include_router(centres_alphabetisation)


@router.get(
    "/alphabetisation/statistiques",
    tags=["Alphabétisation"],
    summary="Statistiques de l'alphabétisation",
    description="Répartition par langue nationale et taux de certification.",
)
async def statistiques_alphabetisation(session: SessionDep, contexte: ContexteDep) -> dict:
    contexte.exiger("apprentissage", Action.READ)

    stmt = (
        select(
            ParcoursAlphabetisation.langue,
            func.count(ParcoursAlphabetisation.id),
            func.avg(ParcoursAlphabetisation.progression_pourcentage),
            func.count(ParcoursAlphabetisation.id).filter(
                ParcoursAlphabetisation.certifie.is_(True)
            ),
        )
        .group_by(ParcoursAlphabetisation.langue)
        .order_by(func.count(ParcoursAlphabetisation.id).desc())
    )

    par_langue = [
        {
            "langue": langue.value,
            "apprenants": total,
            "progression_moyenne": round(float(progression), 1) if progression else 0.0,
            "certifies": certifies,
        }
        for langue, total, progression, certifies in (await session.execute(stmt)).all()
    ]

    centres = int(
        (
            await session.execute(select(func.count()).select_from(CentreAlphabetisation))
        ).scalar_one()
    )
    total = sum(ligne["apprenants"] for ligne in par_langue)
    certifies = sum(ligne["certifies"] for ligne in par_langue)

    return {
        "centres": centres,
        "apprenants": total,
        "certifies": certifies,
        "taux_certification": round(certifies * 100 / total, 2) if total else 0.0,
        "par_langue": par_langue,
    }


# ------------------------------------------------------------------
#  Recherche scientifique
# ------------------------------------------------------------------

laboratoires = creer_routeur_crud(
    modele=Laboratoire,
    schema_lecture=LaboratoireLecture,
    schema_creation=None,
    schema_maj=None,
    prefixe="/recherche-scientifique/laboratoires",
    tag="Recherche scientifique",
    ressource="recherche",
    libelle_singulier="laboratoire",
    libelle_pluriel="laboratoires",
    champs_recherche=("code", "nom", "domaines"),
    tri_defaut="nom",
    champs_filtrables=(
        DescripteurChamp("nom", "Nom", Laboratoire.nom),
        DescripteurChamp("domaines", "Domaines", Laboratoire.domaines),
        DescripteurChamp("etablissement_id", "Établissement", Laboratoire.etablissement_id, "uuid"),
        DescripteurChamp(
            "nombre_chercheurs", "Chercheurs", Laboratoire.nombre_chercheurs, "nombre"
        ),
    ),
)


@laboratoires.get(
    "/{identifiant}/equipe",
    response_model=list[ChercheurLecture],
    summary="Chercheurs d'un laboratoire",
)
async def equipe_laboratoire(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[Chercheur]:
    contexte.exiger("recherche", Action.READ)
    stmt = (
        select(Chercheur)
        .where(Chercheur.laboratoire_id == identifiant)
        .order_by(Chercheur.indice_h.desc())
    )
    return list((await session.execute(stmt)).scalars())


router.include_router(laboratoires)

router.include_router(
    creer_routeur_crud(
        modele=Chercheur,
        schema_lecture=ChercheurLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/recherche-scientifique/chercheurs",
        tag="Recherche scientifique",
        ressource="recherche",
        libelle_singulier="chercheur",
        libelle_pluriel="chercheurs",
        champs_recherche=("nom_complet", "specialite", "orcid"),
        tri_defaut="nom_complet",
        contrainte_unicite=None,
        champs_filtrables=(
            DescripteurChamp("nom_complet", "Nom", Chercheur.nom_complet),
            DescripteurChamp("grade", "Grade", Chercheur.grade, "liste"),
            DescripteurChamp("specialite", "Spécialité", Chercheur.specialite),
            DescripteurChamp("laboratoire_id", "Laboratoire", Chercheur.laboratoire_id, "uuid"),
            DescripteurChamp("indice_h", "Indice h", Chercheur.indice_h, "nombre"),
            DescripteurChamp(
                "nombre_publications", "Publications", Chercheur.nombre_publications, "nombre"
            ),
        ),
    )
)

router.include_router(
    creer_routeur_crud(
        modele=Publication,
        schema_lecture=PublicationLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/recherche-scientifique/publications",
        tag="Recherche scientifique",
        ressource="recherche",
        libelle_singulier="publication",
        libelle_pluriel="publications",
        champs_recherche=("titre", "revue", "doi", "mots_cles"),
        tri_defaut="annee",
        contrainte_unicite=None,
        champs_filtrables=(
            DescripteurChamp("titre", "Titre", Publication.titre),
            DescripteurChamp("type_publication", "Type", Publication.type_publication, "liste"),
            DescripteurChamp("revue", "Revue", Publication.revue),
            DescripteurChamp("annee", "Année", Publication.annee, "nombre"),
            DescripteurChamp("acces_libre", "Accès libre", Publication.acces_libre, "booleen"),
            DescripteurChamp(
                "nombre_citations", "Citations", Publication.nombre_citations, "nombre"
            ),
        ),
    )
)

router.include_router(
    creer_routeur_crud(
        modele=ProjetRecherche,
        schema_lecture=ProjetRechercheLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/recherche-scientifique/projets",
        tag="Recherche scientifique",
        ressource="recherche",
        libelle_singulier="projet de recherche",
        libelle_pluriel="projets de recherche",
        champs_recherche=("code", "titre", "domaine", "bailleur"),
        tri_defaut="titre",
        champs_filtrables=(
            DescripteurChamp("titre", "Titre", ProjetRecherche.titre),
            DescripteurChamp("domaine", "Domaine", ProjetRecherche.domaine, "liste"),
            DescripteurChamp(
                "laboratoire_id", "Laboratoire", ProjetRecherche.laboratoire_id, "uuid"
            ),
            DescripteurChamp("statut", "Statut", ProjetRecherche.statut, "liste"),
            DescripteurChamp("financement", "Financement", ProjetRecherche.financement, "nombre"),
        ),
    )
)
