"""Examens et concours : configuration, candidatures, composition, résultats."""

import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.crud import creer_routeur_crud, obtenir_ou_404
from app.api.deps import ContexteDep, MetadonneesDep, SessionDep
from app.core.enums import Action
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.engines import workflow
from app.engines.analytics import resultats_par_departement, resultats_par_etablissement
from app.engines.audit import journaliser
from app.engines.reporting import exporter_csv
from app.engines.search import DescripteurChamp
from app.models.apprenant import Apprenant
from app.models.examen import (
    AffectationSurveillance,
    BudgetExamen,
    Candidat,
    CentreComposition,
    Contentieux,
    Convocation,
    Copie,
    Correcteur,
    DecisionExamen,
    DocumentCandidat,
    EpreuveArchivee,
    EpreuveExamen,
    Examen,
    Jury,
    MembreJury,
    NoteExamen,
    PieceRequise,
    ResultatExamen,
    SalleComposition,
    SerieExamen,
    SessionExamen,
    StatutContentieux,
    StatutDossier,
    StatutNoteExamen,
    StatutSession,
)
from app.models.scolarite import Inscription, Matiere
from app.schemas.base import MessageReponse
from app.schemas.examen import (
    AffectationSurveillanceEcriture,
    AffectationSurveillanceLecture,
    ArchiveEpreuveLecture,
    BudgetLecture,
    CandidatCreation,
    CandidatLecture,
    CandidatMiseAJour,
    CentreEcriture,
    CentreLecture,
    ContentieuxCreation,
    ContentieuxInstruction,
    ContentieuxLecture,
    CopieLecture,
    CorrecteurLecture,
    DeliberationDemande,
    EpreuveEcriture,
    EpreuveLecture,
    ExamenEcriture,
    ExamenLecture,
    InscriptionMasse,
    JuryEcriture,
    JuryLecture,
    MembreJuryEcriture,
    NoteExamenLecture,
    RepartitionDemande,
    RepartitionResultat,
    ResultatLecture,
    SaisieNotesExamen,
    SalleCompositionEcriture,
    SalleCompositionLecture,
    SessionCreation,
    SessionLecture,
    SessionMiseAJour,
    TableauBordSession,
    ValidationPiece,
)
from app.schemas.scolarite import TransitionDemande
from app.services import examens as service
from app.utils.calculs import ramener_sur_20
from app.utils.codes import generer_numero_candidat, generer_reference

router = APIRouter()


# ------------------------------------------------------------------
#  Examens
# ------------------------------------------------------------------

router.include_router(
    creer_routeur_crud(
        modele=Examen,
        schema_lecture=ExamenLecture,
        schema_creation=ExamenEcriture,
        schema_maj=ExamenEcriture,
        prefixe="/examens",
        tag="Examens",
        ressource="examens",
        libelle_singulier="examen",
        libelle_pluriel="examens",
        champs_recherche=("code", "nom", "sigle"),
        tri_defaut="nom",
        champs_filtrables=(
            DescripteurChamp("code", "Code", Examen.code),
            DescripteurChamp("nom", "Nom", Examen.nom),
            DescripteurChamp("nature", "Nature", Examen.nature, "liste"),
            DescripteurChamp("ministere_id", "Ministère", Examen.ministere_id, "uuid"),
            DescripteurChamp(
                "direction_responsable_id", "Direction", Examen.direction_responsable_id, "uuid"
            ),
            DescripteurChamp("actif", "Actif", Examen.actif, "booleen"),
        ),
    )
)


# ------------------------------------------------------------------
#  Sessions
# ------------------------------------------------------------------

sessions = creer_routeur_crud(
    modele=SessionExamen,
    schema_lecture=SessionLecture,
    schema_creation=None,
    schema_maj=SessionMiseAJour,
    prefixe="/sessions",
    tag="Examens",
    ressource="sessions",
    libelle_singulier="session",
    libelle_pluriel="sessions",
    champs_recherche=("code", "libelle"),
    tri_defaut="annee",
    champs_filtrables=(
        DescripteurChamp("code", "Code", SessionExamen.code),
        DescripteurChamp("libelle", "Libellé", SessionExamen.libelle),
        DescripteurChamp("examen_id", "Examen", SessionExamen.examen_id, "uuid"),
        DescripteurChamp("annee", "Année", SessionExamen.annee, "nombre"),
        DescripteurChamp("statut", "Statut", SessionExamen.statut, "liste"),
        DescripteurChamp("type_session", "Type", SessionExamen.type_session, "liste"),
        DescripteurChamp(
            "taux_reussite", "Taux de réussite", SessionExamen.taux_reussite, "nombre"
        ),
        DescripteurChamp("nombre_inscrits", "Inscrits", SessionExamen.nombre_inscrits, "nombre"),
    ),
)


@sessions.post(
    "",
    response_model=SessionLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Ouvrir une session d'examen",
)
async def creer_session(
    donnees: SessionCreation,
    session: SessionDep,
    contexte: ContexteDep,
    metadonnees: MetadonneesDep,
) -> SessionExamen:
    contexte.exiger("sessions", Action.CREATE)
    await obtenir_ou_404(session, Examen, donnees.examen_id, "Examen")

    existante = (
        await session.execute(select(SessionExamen).where(SessionExamen.code == donnees.code))
    ).scalar_one_or_none()
    if existante is not None:
        raise ConflictError("Une session porte déjà ce code.")

    session_examen = SessionExamen(
        **donnees.model_dump(exclude={"series"}), statut=StatutSession.PREPARATION
    )
    session.add(session_examen)
    await session.flush()

    for serie_id in donnees.series:
        session.add(SerieExamen(session_id=session_examen.id, serie_id=serie_id))

    await journaliser(
        session,
        action=Action.CREATE,
        entite_type="sessions",
        entite_id=session_examen.id,
        entite_libelle=session_examen.libelle,
        utilisateur_id=contexte.id,
        utilisateur_email=contexte.email,
        adresse_ip=metadonnees["adresse_ip"],
    )
    return session_examen


@sessions.get(
    "/{identifiant}/tableau-de-bord",
    response_model=TableauBordSession,
    summary="Tableau de bord d'une session",
    description="Pilotage complet : dossiers, centres, surveillance, correction, résultats.",
)
async def tableau_de_bord_session(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> TableauBordSession:
    contexte.exiger("sessions", Action.READ)
    session_examen = await service.charger_session(session, identifiant)

    async def compter(modele, *conditions) -> int:
        stmt = select(func.count()).select_from(modele)
        for condition in conditions:
            stmt = stmt.where(condition)
        return int((await session.execute(stmt)).scalar_one())

    stmt = (
        select(Candidat.statut_dossier, func.count())
        .where(Candidat.session_id == identifiant)
        .group_by(Candidat.statut_dossier)
    )
    dossiers = {statut.value: total for statut, total in (await session.execute(stmt)).all()}

    stmt = (
        select(Contentieux.statut, func.count())
        .where(Contentieux.session_id == identifiant)
        .group_by(Contentieux.statut)
    )
    contentieux = {statut.value: total for statut, total in (await session.execute(stmt)).all()}

    budget = (
        await session.execute(select(BudgetExamen).where(BudgetExamen.session_id == identifiant))
    ).scalar_one_or_none()

    return TableauBordSession(
        session=SessionLecture.model_validate(session_examen),
        dossiers=dossiers,
        centres=await compter(CentreComposition, CentreComposition.session_id == identifiant),
        salles=await compter(
            SalleComposition,
            SalleComposition.centre_id.in_(
                select(CentreComposition.id).where(CentreComposition.session_id == identifiant)
            ),
        ),
        surveillants=await compter(
            AffectationSurveillance, AffectationSurveillance.session_id == identifiant
        ),
        correcteurs=await compter(Correcteur, Correcteur.session_id == identifiant),
        copies_totales=await compter(Copie, Copie.session_id == identifiant),
        copies_corrigees=await compter(
            Copie, Copie.session_id == identifiant, Copie.corrigee.is_(True)
        ),
        jurys=await compter(Jury, Jury.session_id == identifiant),
        contentieux=contentieux,
        budget={
            "prevu": budget.montant_prevu if budget else 0.0,
            "engage": budget.montant_engage if budget else 0.0,
            "paye": budget.montant_paye if budget else 0.0,
            "recettes": budget.recettes_inscriptions if budget else 0.0,
        },
        resultats_par_departement=await resultats_par_departement(session, identifiant),
    )


@sessions.post(
    "/{identifiant}/repartir-candidats",
    response_model=RepartitionResultat,
    summary="Répartir les candidats par centre et par salle",
    description=(
        "Affecte chaque candidat validé à un centre, une salle et une place. "
        "Les candidats bénéficiant d'aménagements sont placés en priorité."
    ),
)
async def repartir(
    identifiant: uuid.UUID,
    demande: RepartitionDemande,
    session: SessionDep,
    contexte: ContexteDep,
    metadonnees: MetadonneesDep,
) -> RepartitionResultat:
    contexte.exiger("centres", Action.ASSIGN)
    resultat = await service.repartir_candidats(
        session,
        identifiant,
        par_departement=demande.par_departement,
        prioriser_amenagements=demande.prioriser_amenagements,
        melanger_etablissements=demande.melanger_etablissements,
    )
    await journaliser(
        session,
        action=Action.ASSIGN,
        entite_type="sessions",
        entite_id=identifiant,
        entite_libelle="Répartition des candidats",
        utilisateur_id=contexte.id,
        utilisateur_email=contexte.email,
        valeurs_apres={"affectes": resultat["candidats_affectes"]},
        adresse_ip=metadonnees["adresse_ip"],
    )
    return RepartitionResultat(**resultat)


@sessions.post(
    "/{identifiant}/convocations",
    response_model=MessageReponse,
    summary="Générer les convocations des candidats",
)
async def generer_convocations(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> MessageReponse:
    contexte.exiger("candidats", Action.PUBLISH)
    resultat = await service.generer_convocations(session, identifiant)
    return MessageReponse(message="Convocations générées.", details=resultat)


@sessions.post(
    "/{identifiant}/copies",
    response_model=MessageReponse,
    summary="Générer les copies anonymées",
)
async def generer_copies(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> MessageReponse:
    contexte.exiger("copies", Action.CREATE)
    resultat = await service.generer_copies(session, identifiant)
    return MessageReponse(message="Copies créées.", details=resultat)


@sessions.post(
    "/{identifiant}/deliberer",
    response_model=MessageReponse,
    summary="Délibérer une session",
    description=(
        "Calcule les moyennes pondérées, applique les notes éliminatoires, "
        "accorde les points de jury, arrête les décisions et les rangs."
    ),
)
async def deliberer(
    identifiant: uuid.UUID,
    demande: DeliberationDemande,
    session: SessionDep,
    contexte: ContexteDep,
    metadonnees: MetadonneesDep,
) -> MessageReponse:
    contexte.exiger("resultats", Action.VALIDATE)
    resultat = await service.deliberer(
        session,
        identifiant,
        moyenne_admission=demande.moyenne_admission,
        repechage_maximum=demande.repechage_maximum,
        appliquer_note_eliminatoire=demande.appliquer_note_eliminatoire,
        publier=demande.publier,
    )
    await journaliser(
        session,
        action=Action.VALIDATE,
        entite_type="sessions",
        entite_id=identifiant,
        entite_libelle="Délibération",
        utilisateur_id=contexte.id,
        utilisateur_email=contexte.email,
        valeurs_apres=resultat,
        adresse_ip=metadonnees["adresse_ip"],
    )
    return MessageReponse(message="Délibération effectuée.", details=resultat)


@sessions.post(
    "/{identifiant}/publier-resultats",
    response_model=MessageReponse,
    summary="Publier les résultats d'une session",
)
async def publier_resultats(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> MessageReponse:
    contexte.exiger("resultats", Action.PUBLISH)
    session_examen = await service.charger_session(session, identifiant)
    horodatage = datetime.now(UTC)

    resultats = list(
        (
            await session.execute(
                select(ResultatExamen).where(ResultatExamen.session_id == identifiant)
            )
        ).scalars()
    )
    if not resultats:
        raise BusinessRuleError("Aucun résultat à publier : délibérez d'abord la session.")

    for resultat in resultats:
        resultat.publie = True
        resultat.publie_le = horodatage

    session_examen.statut = StatutSession.RESULTATS_PUBLIES
    session_examen.resultats_publies_le = horodatage
    session_examen.date_publication_resultats = date.today()
    await session.flush()

    return MessageReponse(message="Résultats publiés.", details={"resultats": len(resultats)})


@sessions.post(
    "/{identifiant}/diplomes",
    response_model=MessageReponse,
    summary="Délivrer les diplômes aux lauréats",
)
async def delivrer_diplomes(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> MessageReponse:
    contexte.exiger("diplomes", Action.CREATE)
    resultat = await service.delivrer_diplomes(session, identifiant)
    return MessageReponse(message="Diplômes délivrés.", details=resultat)


@sessions.get(
    "/{identifiant}/resultats-etablissements",
    summary="Palmarès des établissements",
)
async def palmares(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[dict]:
    contexte.exiger("resultats", Action.READ)
    return await resultats_par_etablissement(session, identifiant)


@sessions.get(
    "/{identifiant}/resultats-departements",
    summary="Résultats par département",
)
async def resultats_departements(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[dict]:
    contexte.exiger("resultats", Action.READ)
    return await resultats_par_departement(session, identifiant)


@sessions.get(
    "/{identifiant}/epreuves",
    response_model=list[EpreuveLecture],
    summary="Épreuves d'une session",
)
async def epreuves_session(
    identifiant: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
    serie_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[EpreuveExamen]:
    contexte.exiger("sessions", Action.READ)
    stmt = (
        select(EpreuveExamen)
        .where(EpreuveExamen.session_id == identifiant)
        .order_by(EpreuveExamen.date_epreuve, EpreuveExamen.heure_debut)
    )
    if serie_id:
        stmt = stmt.where(EpreuveExamen.serie_id == serie_id)
    return list((await session.execute(stmt)).scalars())


router.include_router(sessions)


router.include_router(
    creer_routeur_crud(
        modele=EpreuveExamen,
        schema_lecture=EpreuveLecture,
        schema_creation=EpreuveEcriture,
        schema_maj=EpreuveEcriture,
        prefixe="/epreuves",
        tag="Examens",
        ressource="sessions",
        libelle_singulier="épreuve",
        libelle_pluriel="épreuves",
        champs_recherche=("code", "libelle"),
        contrainte_unicite=None,
        tri_defaut="date_epreuve",
        champs_filtrables=(
            DescripteurChamp("session_id", "Session", EpreuveExamen.session_id, "uuid"),
            DescripteurChamp("matiere_id", "Matière", EpreuveExamen.matiere_id, "uuid"),
            DescripteurChamp("serie_id", "Série", EpreuveExamen.serie_id, "uuid"),
            DescripteurChamp("date_epreuve", "Date", EpreuveExamen.date_epreuve, "date"),
            DescripteurChamp("coefficient", "Coefficient", EpreuveExamen.coefficient, "nombre"),
        ),
    )
)


# ------------------------------------------------------------------
#  Candidatures
# ------------------------------------------------------------------

candidats = creer_routeur_crud(
    modele=Candidat,
    schema_lecture=CandidatLecture,
    schema_creation=None,
    schema_maj=CandidatMiseAJour,
    prefixe="/candidats",
    tag="Candidats",
    ressource="candidats",
    libelle_singulier="candidat",
    libelle_pluriel="candidats",
    champs_recherche=("numero_candidat", "numero_table", "nom", "prenoms"),
    tri_defaut="nom",
    contrainte_unicite=None,
    champs_filtrables=(
        DescripteurChamp("numero_candidat", "Numéro", Candidat.numero_candidat),
        DescripteurChamp("numero_table", "Numéro de table", Candidat.numero_table),
        DescripteurChamp("nom", "Nom", Candidat.nom),
        DescripteurChamp("prenoms", "Prénoms", Candidat.prenoms),
        DescripteurChamp("sexe", "Sexe", Candidat.sexe, "liste"),
        DescripteurChamp("session_id", "Session", Candidat.session_id, "uuid"),
        DescripteurChamp("serie_id", "Série", Candidat.serie_id, "uuid"),
        DescripteurChamp("etablissement_id", "Établissement", Candidat.etablissement_id, "uuid"),
        DescripteurChamp("departement_id", "Département", Candidat.departement_id, "uuid"),
        DescripteurChamp("centre_id", "Centre", Candidat.centre_id, "uuid"),
        DescripteurChamp("statut_dossier", "Statut du dossier", Candidat.statut_dossier, "liste"),
        DescripteurChamp(
            "type_candidature", "Type de candidature", Candidat.type_candidature, "liste"
        ),
        DescripteurChamp("type_handicap", "Besoin spécifique", Candidat.type_handicap, "liste"),
        DescripteurChamp("statut_paiement", "Paiement", Candidat.statut_paiement, "liste"),
    ),
)


@candidats.post(
    "",
    response_model=CandidatLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Inscrire un candidat",
    description="Candidat officiel présenté par un établissement, ou candidat libre.",
)
async def creer_candidat(
    donnees: CandidatCreation,
    session: SessionDep,
    contexte: ContexteDep,
    metadonnees: MetadonneesDep,
) -> Candidat:
    contexte.exiger("candidats", Action.CREATE)
    session_examen = await service.charger_session(session, donnees.session_id)

    if session_examen.statut not in {
        StatutSession.PREPARATION,
        StatutSession.INSCRIPTIONS_OUVERTES,
    }:
        raise BusinessRuleError(
            "Les inscriptions ne sont pas ouvertes pour cette session.",
            details={"statut": session_examen.statut.value},
        )

    total = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Candidat)
                .where(Candidat.session_id == donnees.session_id)
            )
        ).scalar_one()
    )
    examen = session_examen.examen
    numero = generer_numero_candidat(
        examen.code if examen else "EXA", session_examen.annee, total + 1
    )

    frais = 0.0
    if examen is not None:
        frais = (
            examen.frais_candidat_libre
            if donnees.type_candidature.value == "LIBRE"
            else examen.frais_officiel
        )

    candidat = Candidat(
        numero_candidat=numero,
        statut_dossier=StatutDossier.BROUILLON,
        montant_frais=frais,
        **donnees.model_dump(),
    )
    session.add(candidat)
    await session.flush()

    await journaliser(
        session,
        action=Action.CREATE,
        entite_type="candidats",
        entite_id=candidat.id,
        entite_libelle=candidat.numero_candidat,
        utilisateur_id=contexte.id,
        utilisateur_email=contexte.email,
        adresse_ip=metadonnees["adresse_ip"],
    )
    return candidat


@candidats.post(
    "/inscription-classe",
    response_model=MessageReponse,
    summary="Inscrire une classe entière à une session",
    description="Présente automatiquement tous les élèves d'une classe à l'examen.",
)
async def inscrire_classe(
    demande: InscriptionMasse,
    session: SessionDep,
    contexte: ContexteDep,
) -> MessageReponse:
    contexte.exiger("candidats", Action.CREATE)
    session_examen = await service.charger_session(session, demande.session_id)
    examen = session_examen.examen

    stmt = (
        select(Apprenant, Inscription)
        .join(Inscription, Inscription.apprenant_id == Apprenant.id)
        .where(Inscription.classe_id == demande.classe_id)
    )
    eleves = (await session.execute(stmt)).all()
    if not eleves:
        raise BusinessRuleError("Cette classe ne compte aucun élève inscrit.")

    deja = {
        candidat.apprenant_id
        for candidat in (
            await session.execute(select(Candidat).where(Candidat.session_id == demande.session_id))
        ).scalars()
    }

    total = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Candidat)
                .where(Candidat.session_id == demande.session_id)
            )
        ).scalar_one()
    )

    inscrits = 0
    for apprenant, inscription in eleves:
        if apprenant.id in deja:
            continue
        total += 1
        inscrits += 1
        session.add(
            Candidat(
                numero_candidat=generer_numero_candidat(
                    examen.code if examen else "EXA", session_examen.annee, total
                ),
                session_id=demande.session_id,
                serie_id=demande.serie_id,
                apprenant_id=apprenant.id,
                utilisateur_id=apprenant.utilisateur_id,
                etablissement_id=inscription.etablissement_id,
                nom=apprenant.nom,
                prenoms=apprenant.prenoms,
                sexe=apprenant.sexe,
                date_naissance=apprenant.date_naissance,
                lieu_naissance=apprenant.lieu_naissance,
                telephone=apprenant.telephone,
                statut_dossier=StatutDossier.SOUMIS,
                date_soumission=datetime.now(UTC),
                type_handicap=apprenant.type_handicap,
                tiers_temps=apprenant.tiers_temps,
                amenagements_demandes=apprenant.amenagements_examen,
            )
        )

    session_examen.nombre_inscrits = total
    await session.flush()
    return MessageReponse(
        message="Classe inscrite à la session.",
        details={"inscrits": inscrits, "deja_inscrits": len(eleves) - inscrits},
    )


@candidats.post(
    "/{identifiant}/transition",
    response_model=CandidatLecture,
    summary="Faire avancer un dossier de candidature",
    description=(
        "Actions : soumettre, instruire, declarer_incomplet, completer, valider, "
        "rejeter, convoquer, marquer_compose, marquer_corrige, admettre, ajourner."
    ),
)
async def transition_candidat(
    identifiant: uuid.UUID,
    demande: TransitionDemande,
    session: SessionDep,
    contexte: ContexteDep,
) -> Candidat:
    contexte.exiger("candidats", Action.VALIDATE)
    candidat = await obtenir_ou_404(session, Candidat, identifiant, "Candidat")

    transition = await workflow.appliquer(
        session,
        workflow.WORKFLOW_DOSSIER_EXAMEN,
        entite_type="candidats",
        entite_id=candidat.id,
        statut_actuel=candidat.statut_dossier.value,
        action=demande.action,
        acteur_id=contexte.id,
        acteur_nom=contexte.utilisateur.nom_complet,
        roles=contexte.roles,
        commentaire=demande.commentaire,
    )

    candidat.statut_dossier = StatutDossier(transition.vers)
    horodatage = datetime.now(UTC)
    if transition.vers == StatutDossier.SOUMIS.value:
        candidat.date_soumission = horodatage
    elif transition.vers == StatutDossier.VALIDE.value:
        candidat.date_validation = horodatage
        candidat.valide_par_id = contexte.id
    elif transition.vers in {StatutDossier.REJETE.value, StatutDossier.INCOMPLET.value}:
        candidat.motif_rejet = demande.motif or demande.commentaire

    await session.flush()
    return candidat


@candidats.get(
    "/{identifiant}/transitions",
    summary="Actions possibles sur un dossier",
)
async def transitions_candidat(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[dict]:
    contexte.exiger("candidats", Action.READ)
    candidat = await obtenir_ou_404(session, Candidat, identifiant, "Candidat")
    return [
        {"action": t.action, "libelle": t.libelle, "vers": t.vers}
        for t in workflow.WORKFLOW_DOSSIER_EXAMEN.transitions_possibles(
            candidat.statut_dossier.value
        )
    ]


@candidats.get(
    "/{identifiant}/dossier",
    summary="Dossier d'un candidat",
    description="Pièces jointes, affectation, notes et résultat.",
)
async def dossier_candidat(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> dict:
    contexte.exiger("candidats", Action.READ)
    stmt = (
        select(Candidat)
        .where(Candidat.id == identifiant)
        .options(
            selectinload(Candidat.documents),
            selectinload(Candidat.centre),
            selectinload(Candidat.salle_composition),
            selectinload(Candidat.resultat),
            selectinload(Candidat.session),
        )
    )
    candidat = (await session.execute(stmt)).scalar_one_or_none()
    if candidat is None:
        raise NotFoundError("Candidat introuvable.")

    stmt = (
        select(NoteExamen, EpreuveExamen, Matiere)
        .join(EpreuveExamen, EpreuveExamen.id == NoteExamen.epreuve_id)
        .join(Matiere, Matiere.id == EpreuveExamen.matiere_id)
        .where(NoteExamen.candidat_id == identifiant)
        .order_by(Matiere.libelle)
    )
    notes = [
        {
            "epreuve": epreuve.libelle,
            "matiere": matiere.libelle,
            "note": note.valeur,
            "coefficient": note.coefficient,
            "points": note.points,
            "statut": note.statut.value,
        }
        for note, epreuve, matiere in (await session.execute(stmt)).all()
    ]

    pieces_requises = list(
        (
            await session.execute(
                select(PieceRequise).where(PieceRequise.session_id == candidat.session_id)
            )
        ).scalars()
    )
    fournies = {document.type_document_id for document in candidat.documents}
    manquantes = [
        str(piece.type_document_id)
        for piece in pieces_requises
        if piece.obligatoire
        and piece.type_document_id not in fournies
        # Une pièce ciblant un autre type de candidature ne concerne pas ce candidat.
        and piece.type_candidature in (None, candidat.type_candidature)
    ]

    return {
        "candidat": CandidatLecture.model_validate(candidat).model_dump(mode="json"),
        "session": candidat.session.libelle if candidat.session else None,
        "affectation": {
            "centre": candidat.centre.nom if candidat.centre else None,
            "salle": candidat.salle_composition.nom if candidat.salle_composition else None,
            "place": candidat.numero_place,
            "numero_table": candidat.numero_table,
        },
        "pieces": [
            {
                "id": str(document.id),
                "nom_fichier": document.nom_fichier,
                "statut": document.statut.value,
                "motif_rejet": document.motif_rejet.value if document.motif_rejet else None,
                "version": document.version,
            }
            for document in candidat.documents
        ],
        "pieces_manquantes": manquantes,
        "dossier_complet": not manquantes,
        "notes": notes,
        "resultat": {
            "moyenne": candidat.resultat.moyenne,
            "mention": candidat.resultat.mention,
            "decision": candidat.resultat.decision.value,
            "rang_national": candidat.resultat.rang_national,
            "publie": candidat.resultat.publie,
        }
        if candidat.resultat
        else None,
    }


@candidats.post(
    "/{identifiant}/pieces/{piece_id}/validation",
    response_model=MessageReponse,
    summary="Valider ou rejeter une pièce jointe",
)
async def valider_piece(
    identifiant: uuid.UUID,
    piece_id: uuid.UUID,
    donnees: ValidationPiece,
    session: SessionDep,
    contexte: ContexteDep,
) -> MessageReponse:
    contexte.exiger("documents", Action.VALIDATE)
    document = await obtenir_ou_404(session, DocumentCandidat, piece_id, "Pièce jointe")
    if document.candidat_id != identifiant:
        raise BusinessRuleError("Cette pièce n'appartient pas au candidat indiqué.")

    document.statut = donnees.statut
    document.motif_rejet = donnees.motif_rejet
    document.commentaire = donnees.commentaire
    document.verifie_par_id = contexte.id
    document.verifie_le = datetime.now(UTC)
    await session.flush()

    return MessageReponse(
        message=f"Pièce marquée « {donnees.statut.value} ».",
    )


@candidats.get(
    "/{identifiant}/convocation",
    summary="Télécharger la convocation d'un candidat",
    response_class=Response,
)
async def convocation_pdf(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> Response:
    contexte.exiger("candidats", Action.PRINT)
    candidat = await obtenir_ou_404(session, Candidat, identifiant, "Candidat")
    convocation = (
        await session.execute(
            select(Convocation).where(Convocation.candidat_id == identifiant).limit(1)
        )
    ).scalar_one_or_none()
    if convocation is None:
        raise NotFoundError(
            "Aucune convocation n'a été émise pour ce candidat.",
            details={"candidat": candidat.numero_candidat},
        )

    session_examen = await service.charger_session(session, candidat.session_id)
    contenu = service.composer_pdf_convocation(convocation, session_examen)
    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="convocation-{convocation.numero}.pdf"'},
    )


router.include_router(candidats)


# ------------------------------------------------------------------
#  Centres, salles et surveillance
# ------------------------------------------------------------------

centres = creer_routeur_crud(
    modele=CentreComposition,
    schema_lecture=CentreLecture,
    schema_creation=CentreEcriture,
    schema_maj=CentreEcriture,
    prefixe="/centres",
    tag="Centres de composition",
    ressource="centres",
    libelle_singulier="centre de composition",
    libelle_pluriel="centres de composition",
    champs_recherche=("code", "nom", "chef_centre_nom"),
    contrainte_unicite=None,
    tri_defaut="code",
    champs_filtrables=(
        DescripteurChamp("code", "Code", CentreComposition.code),
        DescripteurChamp("nom", "Nom", CentreComposition.nom),
        DescripteurChamp("session_id", "Session", CentreComposition.session_id, "uuid"),
        DescripteurChamp("departement_id", "Département", CentreComposition.departement_id, "uuid"),
        DescripteurChamp(
            "nombre_candidats", "Candidats", CentreComposition.nombre_candidats, "nombre"
        ),
        DescripteurChamp("capacite", "Capacité", CentreComposition.capacite, "nombre"),
        DescripteurChamp(
            "accessible_handicap",
            "Accessible",
            CentreComposition.accessible_handicap,
            "booleen",
        ),
    ),
)


@centres.get(
    "/{identifiant}/salles",
    response_model=list[SalleCompositionLecture],
    summary="Salles d'un centre",
)
async def salles_du_centre(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[SalleComposition]:
    contexte.exiger("centres", Action.READ)
    stmt = (
        select(SalleComposition)
        .where(SalleComposition.centre_id == identifiant)
        .order_by(SalleComposition.code)
    )
    return list((await session.execute(stmt)).scalars())


@centres.get(
    "/{identifiant}/liste-emargement",
    summary="Liste d'émargement d'un centre",
    description="Export CSV des candidats affectés, par salle et par place.",
    response_class=Response,
)
async def liste_emargement(
    identifiant: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
    salle_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Response:
    contexte.exiger("candidats", Action.EXPORT)
    stmt = (
        select(Candidat, SalleComposition)
        .join(SalleComposition, SalleComposition.id == Candidat.salle_composition_id)
        .where(Candidat.centre_id == identifiant)
        .order_by(SalleComposition.code, Candidat.numero_place)
    )
    if salle_id:
        stmt = stmt.where(Candidat.salle_composition_id == salle_id)

    lignes = [
        [
            salle.nom,
            candidat.numero_place,
            candidat.numero_table,
            candidat.numero_candidat,
            candidat.nom,
            candidat.prenoms,
            candidat.sexe.value,
            candidat.date_naissance.strftime("%d/%m/%Y"),
            "Oui" if candidat.tiers_temps else "Non",
        ]
        for candidat, salle in (await session.execute(stmt)).all()
    ]

    contenu = exporter_csv(
        [
            "Salle",
            "Place",
            "Numéro de table",
            "Numéro de candidat",
            "Nom",
            "Prénoms",
            "Sexe",
            "Date de naissance",
            "Aménagement",
        ],
        lignes,
    )
    return Response(
        content=contenu,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="liste-emargement.csv"'},
    )


router.include_router(centres)

router.include_router(
    creer_routeur_crud(
        modele=SalleComposition,
        schema_lecture=SalleCompositionLecture,
        schema_creation=SalleCompositionEcriture,
        schema_maj=SalleCompositionEcriture,
        prefixe="/salles-composition",
        tag="Centres de composition",
        ressource="centres",
        libelle_singulier="salle de composition",
        libelle_pluriel="salles de composition",
        champs_recherche=("code", "nom"),
        contrainte_unicite=None,
        champs_filtrables=(
            DescripteurChamp("centre_id", "Centre", SalleComposition.centre_id, "uuid"),
            DescripteurChamp("capacite", "Capacité", SalleComposition.capacite, "nombre"),
            DescripteurChamp(
                "salle_amenagee", "Salle aménagée", SalleComposition.salle_amenagee, "booleen"
            ),
        ),
    )
)

router.include_router(
    creer_routeur_crud(
        modele=AffectationSurveillance,
        schema_lecture=AffectationSurveillanceLecture,
        schema_creation=AffectationSurveillanceEcriture,
        schema_maj=AffectationSurveillanceEcriture,
        prefixe="/surveillance",
        tag="Centres de composition",
        ressource="surveillance",
        libelle_singulier="affectation de surveillance",
        libelle_pluriel="affectations de surveillance",
        champs_recherche=("nom_complet",),
        contrainte_unicite=None,
        tri_defaut="nom_complet",
        champs_filtrables=(
            DescripteurChamp("session_id", "Session", AffectationSurveillance.session_id, "uuid"),
            DescripteurChamp("centre_id", "Centre", AffectationSurveillance.centre_id, "uuid"),
            DescripteurChamp("role", "Rôle", AffectationSurveillance.role, "liste"),
            DescripteurChamp(
                "enseignant_id", "Enseignant", AffectationSurveillance.enseignant_id, "uuid"
            ),
        ),
    )
)


# ------------------------------------------------------------------
#  Correction et notes
# ------------------------------------------------------------------

router.include_router(
    creer_routeur_crud(
        modele=Correcteur,
        schema_lecture=CorrecteurLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/correcteurs",
        tag="Correction",
        ressource="correcteurs",
        libelle_singulier="correcteur",
        libelle_pluriel="correcteurs",
        champs_recherche=("code_correcteur", "nom_complet"),
        tri_defaut="code_correcteur",
        contrainte_unicite=None,
        champs_filtrables=(
            DescripteurChamp("session_id", "Session", Correcteur.session_id, "uuid"),
            DescripteurChamp("epreuve_id", "Épreuve", Correcteur.epreuve_id, "uuid"),
            DescripteurChamp("matiere_id", "Matière", Correcteur.matiere_id, "uuid"),
            DescripteurChamp(
                "est_chef_correcteur", "Chef correcteur", Correcteur.est_chef_correcteur, "booleen"
            ),
            DescripteurChamp(
                "copies_corrigees", "Copies corrigées", Correcteur.copies_corrigees, "nombre"
            ),
        ),
    )
)

copies = creer_routeur_crud(
    modele=Copie,
    schema_lecture=CopieLecture,
    schema_creation=None,
    schema_maj=None,
    prefixe="/copies",
    tag="Correction",
    ressource="copies",
    libelle_singulier="copie",
    libelle_pluriel="copies",
    champs_recherche=("code_anonymat", "lot"),
    tri_defaut="code_anonymat",
    contrainte_unicite=None,
    champs_filtrables=(
        DescripteurChamp("code_anonymat", "Code d'anonymat", Copie.code_anonymat),
        DescripteurChamp("session_id", "Session", Copie.session_id, "uuid"),
        DescripteurChamp("epreuve_id", "Épreuve", Copie.epreuve_id, "uuid"),
        DescripteurChamp("correcteur_id", "Correcteur", Copie.correcteur_id, "uuid"),
        DescripteurChamp("corrigee", "Corrigée", Copie.corrigee, "booleen"),
        DescripteurChamp("note_finale", "Note finale", Copie.note_finale, "nombre"),
        DescripteurChamp(
            "ecart_significatif", "Écart significatif", Copie.ecart_significatif, "booleen"
        ),
    ),
)


@copies.post(
    "/{identifiant}/corriger",
    response_model=CopieLecture,
    summary="Enregistrer la correction d'une copie",
    description="La seconde correction est déclenchée lorsque l'écart dépasse trois points.",
)
async def corriger_copie(
    identifiant: uuid.UUID,
    note: Annotated[float, Query(ge=0, le=100)],
    session: SessionDep,
    contexte: ContexteDep,
    second_correcteur: Annotated[bool, Query()] = False,
) -> Copie:
    contexte.exiger("copies", Action.UPDATE)
    copie = await obtenir_ou_404(session, Copie, identifiant, "Copie")
    epreuve = await session.get(EpreuveExamen, copie.epreuve_id)
    if epreuve is not None and note > epreuve.bareme:
        raise BusinessRuleError(f"La note dépasse le barème de l'épreuve ({epreuve.bareme:g}).")

    if second_correcteur:
        copie.note_second_correcteur = note
        copie.double_correction = True
    else:
        copie.note_correcteur = note

    if copie.note_second_correcteur is not None and copie.note_correcteur is not None:
        copie.ecart_significatif = abs(copie.note_second_correcteur - copie.note_correcteur) >= 3
        copie.note_finale = round((copie.note_correcteur + copie.note_second_correcteur) / 2, 2)
    else:
        copie.note_finale = copie.note_correcteur

    copie.corrigee = True
    copie.corrigee_le = datetime.now(UTC)

    if copie.correcteur_id:
        correcteur = await session.get(Correcteur, copie.correcteur_id)
        if correcteur is not None:
            correcteur.copies_corrigees = int(
                (
                    await session.execute(
                        select(func.count())
                        .select_from(Copie)
                        .where(Copie.correcteur_id == correcteur.id, Copie.corrigee.is_(True))
                    )
                ).scalar_one()
            )

    await session.flush()
    return copie


router.include_router(copies)


@router.post(
    "/notes-examen/saisie",
    response_model=MessageReponse,
    tags=["Correction"],
    summary="Saisir les notes d'une épreuve",
    description="Saisie par le centre de correction ou l'opérateur de saisie.",
)
async def saisir_notes_examen(
    demande: SaisieNotesExamen,
    session: SessionDep,
    contexte: ContexteDep,
    metadonnees: MetadonneesDep,
) -> MessageReponse:
    contexte.exiger("copies", Action.UPDATE)
    epreuve = await obtenir_ou_404(session, EpreuveExamen, demande.epreuve_id, "Épreuve")

    existantes = {
        note.candidat_id: note
        for note in (
            await session.execute(
                select(NoteExamen).where(NoteExamen.epreuve_id == demande.epreuve_id)
            )
        ).scalars()
    }

    saisies = 0
    for ligne in demande.notes:
        if ligne.valeur is not None and ligne.valeur > epreuve.bareme:
            raise BusinessRuleError(
                f"La note {ligne.valeur} dépasse le barème ({epreuve.bareme:g}).",
                details={"candidat_id": str(ligne.candidat_id)},
            )

        note = existantes.get(ligne.candidat_id)
        if note is None:
            note = NoteExamen(
                session_id=epreuve.session_id,
                candidat_id=ligne.candidat_id,
                epreuve_id=epreuve.id,
                coefficient=epreuve.coefficient,
            )
            session.add(note)
        elif note.valeur != ligne.valeur:
            note.ancienne_valeur = note.valeur

        note.valeur = ligne.valeur
        note.valeur_sur_20 = (
            ramener_sur_20(ligne.valeur, epreuve.bareme) if ligne.valeur is not None else None
        )
        note.points = (
            round(note.valeur_sur_20 * epreuve.coefficient, 2)
            if note.valeur_sur_20 is not None
            else None
        )
        note.statut = ligne.statut
        note.saisie_par_id = contexte.id

        if (
            epreuve.note_eliminatoire is not None
            and note.valeur_sur_20 is not None
            and note.valeur_sur_20 < epreuve.note_eliminatoire
        ):
            note.statut = StatutNoteExamen.NOTE_ELIMINATOIRE

        saisies += 1

    await session.flush()
    await journaliser(
        session,
        action=Action.UPDATE,
        entite_type="notes_examen",
        entite_id=epreuve.id,
        entite_libelle=epreuve.libelle,
        utilisateur_id=contexte.id,
        utilisateur_email=contexte.email,
        valeurs_apres={"notes": saisies},
        adresse_ip=metadonnees["adresse_ip"],
    )
    return MessageReponse(message="Notes enregistrées.", details={"notes": saisies})


@router.get(
    "/epreuves/{identifiant}/notes",
    response_model=list[NoteExamenLecture],
    tags=["Correction"],
    summary="Notes d'une épreuve",
)
async def notes_epreuve(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[NoteExamen]:
    contexte.exiger("copies", Action.READ)
    stmt = select(NoteExamen).where(NoteExamen.epreuve_id == identifiant)
    return list((await session.execute(stmt)).scalars())


# ------------------------------------------------------------------
#  Jurys et résultats
# ------------------------------------------------------------------

jurys = creer_routeur_crud(
    modele=Jury,
    schema_lecture=JuryLecture,
    schema_creation=JuryEcriture,
    schema_maj=JuryEcriture,
    prefixe="/jurys",
    tag="Jurys",
    ressource="jurys",
    libelle_singulier="jury",
    libelle_pluriel="jurys",
    champs_recherche=("code", "libelle", "president_nom"),
    contrainte_unicite=None,
    champs_filtrables=(
        DescripteurChamp("code", "Code", Jury.code),
        DescripteurChamp("session_id", "Session", Jury.session_id, "uuid"),
        DescripteurChamp("centre_id", "Centre", Jury.centre_id, "uuid"),
        DescripteurChamp("cloture", "Clôturé", Jury.cloture, "booleen"),
    ),
)


@jurys.post(
    "/{identifiant}/membres",
    response_model=MessageReponse,
    summary="Ajouter un membre à un jury",
)
async def ajouter_membre(
    identifiant: uuid.UUID,
    donnees: MembreJuryEcriture,
    session: SessionDep,
    contexte: ContexteDep,
) -> MessageReponse:
    contexte.exiger("jurys", Action.UPDATE)
    await obtenir_ou_404(session, Jury, identifiant, "Jury")
    session.add(MembreJury(jury_id=identifiant, **donnees.model_dump()))
    await session.flush()
    return MessageReponse(message="Membre ajouté au jury.")


@jurys.get(
    "/{identifiant}/membres",
    summary="Composition d'un jury",
)
async def membres_jury(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[dict]:
    contexte.exiger("jurys", Action.READ)
    stmt = select(MembreJury).where(MembreJury.jury_id == identifiant)
    return [
        {
            "id": str(membre.id),
            "nom_complet": membre.nom_complet,
            "qualite": membre.qualite,
            "est_president": membre.est_president,
            "est_rapporteur": membre.est_rapporteur,
            "present": membre.present,
        }
        for membre in (await session.execute(stmt)).scalars()
    ]


router.include_router(jurys)

resultats = creer_routeur_crud(
    modele=ResultatExamen,
    schema_lecture=ResultatLecture,
    schema_creation=None,
    schema_maj=None,
    prefixe="/resultats",
    tag="Résultats",
    ressource="resultats",
    libelle_singulier="résultat",
    libelle_pluriel="résultats",
    champs_recherche=(),
    tri_defaut="rang_national",
    contrainte_unicite=None,
    champs_filtrables=(
        DescripteurChamp("session_id", "Session", ResultatExamen.session_id, "uuid"),
        DescripteurChamp("serie_id", "Série", ResultatExamen.serie_id, "uuid"),
        DescripteurChamp(
            "etablissement_id", "Établissement", ResultatExamen.etablissement_id, "uuid"
        ),
        DescripteurChamp("departement_id", "Département", ResultatExamen.departement_id, "uuid"),
        DescripteurChamp("moyenne", "Moyenne", ResultatExamen.moyenne, "nombre"),
        DescripteurChamp("mention", "Mention", ResultatExamen.mention, "liste"),
        DescripteurChamp("decision", "Décision", ResultatExamen.decision, "liste"),
        DescripteurChamp("repeche", "Repêché", ResultatExamen.repeche, "booleen"),
        DescripteurChamp("publie", "Publié", ResultatExamen.publie, "booleen"),
    ),
)


@resultats.get(
    "/{identifiant}/releve",
    summary="Relevé de notes d'un candidat",
    response_class=Response,
)
async def releve_notes(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> Response:
    contexte.exiger("resultats", Action.PRINT)
    resultat = await obtenir_ou_404(session, ResultatExamen, identifiant, "Résultat")
    candidat = await obtenir_ou_404(session, Candidat, resultat.candidat_id, "Candidat")
    session_examen = await service.charger_session(session, resultat.session_id)

    stmt = (
        select(NoteExamen, EpreuveExamen, Matiere)
        .join(EpreuveExamen, EpreuveExamen.id == NoteExamen.epreuve_id)
        .join(Matiere, Matiere.id == EpreuveExamen.matiere_id)
        .where(NoteExamen.candidat_id == candidat.id)
        .order_by(Matiere.libelle)
    )
    notes = [
        (note, epreuve, matiere.libelle)
        for note, epreuve, matiere in (await session.execute(stmt)).all()
    ]

    contenu = service.composer_pdf_releve(resultat, candidat, session_examen, notes)
    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="releve-{candidat.numero_candidat}.pdf"'
        },
    )


@resultats.get(
    "/session/{session_id}/export",
    summary="Exporter les résultats d'une session",
    response_class=Response,
)
async def exporter_resultats(
    session_id: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
    decision: Annotated[str | None, Query()] = None,
) -> Response:
    contexte.exiger("resultats", Action.EXPORT)
    stmt = (
        select(ResultatExamen, Candidat)
        .join(Candidat, Candidat.id == ResultatExamen.candidat_id)
        .where(ResultatExamen.session_id == session_id)
        .order_by(ResultatExamen.rang_national)
    )
    if decision:
        stmt = stmt.where(ResultatExamen.decision == DecisionExamen(decision))

    lignes = [
        [
            resultat.rang_national,
            candidat.numero_table,
            candidat.numero_candidat,
            candidat.nom,
            candidat.prenoms,
            candidat.sexe.value,
            candidat.date_naissance.strftime("%d/%m/%Y"),
            resultat.moyenne,
            resultat.mention,
            resultat.decision.value,
            "Oui" if resultat.repeche else "Non",
        ]
        for resultat, candidat in (await session.execute(stmt)).all()
    ]

    contenu = exporter_csv(
        [
            "Rang",
            "Numéro de table",
            "Numéro de candidat",
            "Nom",
            "Prénoms",
            "Sexe",
            "Date de naissance",
            "Moyenne",
            "Mention",
            "Décision",
            "Repêché",
        ],
        lignes,
    )
    return Response(
        content=contenu,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="resultats-session.csv"'},
    )


router.include_router(resultats)


# ------------------------------------------------------------------
#  Contentieux
# ------------------------------------------------------------------

contentieux = creer_routeur_crud(
    modele=Contentieux,
    schema_lecture=ContentieuxLecture,
    schema_creation=None,
    schema_maj=None,
    prefixe="/contentieux",
    tag="Contentieux",
    ressource="contentieux",
    libelle_singulier="contentieux",
    libelle_pluriel="contentieux",
    champs_recherche=("numero", "objet"),
    tri_defaut="numero",
    contrainte_unicite=None,
    champs_filtrables=(
        DescripteurChamp("numero", "Numéro", Contentieux.numero),
        DescripteurChamp("session_id", "Session", Contentieux.session_id, "uuid"),
        DescripteurChamp("candidat_id", "Candidat", Contentieux.candidat_id, "uuid"),
        DescripteurChamp("type_contentieux", "Type", Contentieux.type_contentieux, "liste"),
        DescripteurChamp("statut", "Statut", Contentieux.statut, "liste"),
        DescripteurChamp("date_depot", "Date de dépôt", Contentieux.date_depot, "date"),
    ),
)


@contentieux.post(
    "",
    response_model=ContentieuxLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Déposer une réclamation",
)
async def deposer_contentieux(
    donnees: ContentieuxCreation,
    session: SessionDep,
    contexte: ContexteDep,
) -> Contentieux:
    contexte.exiger("contentieux", Action.CREATE)
    await obtenir_ou_404(session, Candidat, donnees.candidat_id, "Candidat")
    session_examen = await service.charger_session(session, donnees.session_id)

    if (
        session_examen.date_limite_contentieux
        and date.today() > session_examen.date_limite_contentieux
    ):
        raise BusinessRuleError(
            "Le délai de dépôt des réclamations est expiré pour cette session.",
            details={"date_limite": session_examen.date_limite_contentieux.isoformat()},
        )

    dossier = Contentieux(
        numero=generer_reference("CONT"),
        date_depot=date.today(),
        statut=StatutContentieux.DEPOSEE,
        **donnees.model_dump(),
    )
    session.add(dossier)
    await session.flush()
    return dossier


@contentieux.post(
    "/{identifiant}/instruire",
    response_model=ContentieuxLecture,
    summary="Instruire une réclamation",
    description="Enregistre la décision et, le cas échéant, révise la note et le résultat.",
)
async def instruire_contentieux(
    identifiant: uuid.UUID,
    donnees: ContentieuxInstruction,
    session: SessionDep,
    contexte: ContexteDep,
) -> Contentieux:
    contexte.exiger("contentieux", Action.VALIDATE)
    dossier = await obtenir_ou_404(session, Contentieux, identifiant, "Contentieux")

    dossier.statut = donnees.statut
    dossier.conclusion = donnees.conclusion
    dossier.instructeur_nom = donnees.instructeur_nom or contexte.utilisateur.nom_complet
    dossier.instruit_par_id = contexte.id
    dossier.date_instruction = dossier.date_instruction or date.today()
    dossier.date_decision = date.today()
    dossier.notifie_le = datetime.now(UTC)

    if donnees.statut is StatutContentieux.TRANCHEE_FAVORABLE and donnees.note_apres is not None:
        resultat = (
            await session.execute(
                select(ResultatExamen).where(ResultatExamen.candidat_id == dossier.candidat_id)
            )
        ).scalar_one_or_none()
        if resultat is not None:
            dossier.note_avant = resultat.moyenne
            dossier.note_apres = donnees.note_apres
            resultat.moyenne = donnees.note_apres
            if donnees.decision_revisee is not None:
                resultat.decision = donnees.decision_revisee
                dossier.decision_revisee = donnees.decision_revisee

        if dossier.epreuve_id:
            note = (
                await session.execute(
                    select(NoteExamen).where(
                        NoteExamen.candidat_id == dossier.candidat_id,
                        NoteExamen.epreuve_id == dossier.epreuve_id,
                    )
                )
            ).scalar_one_or_none()
            if note is not None:
                note.ancienne_valeur = note.valeur
                note.valeur = donnees.note_apres
                note.modifiee_apres_contentieux = True

    await session.flush()
    return dossier


router.include_router(contentieux)


# ------------------------------------------------------------------
#  Banque d'épreuves et budget
# ------------------------------------------------------------------

router.include_router(
    creer_routeur_crud(
        modele=EpreuveArchivee,
        schema_lecture=ArchiveEpreuveLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/banque-epreuves",
        tag="Archives",
        ressource="archives",
        libelle_singulier="épreuve archivée",
        libelle_pluriel="épreuves archivées",
        champs_recherche=("reference", "titre", "mots_cles"),
        tri_defaut="annee",
        contrainte_unicite=None,
        lecture_publique=False,
        champs_filtrables=(
            DescripteurChamp("reference", "Référence", EpreuveArchivee.reference),
            DescripteurChamp("titre", "Titre", EpreuveArchivee.titre),
            DescripteurChamp("examen_id", "Examen", EpreuveArchivee.examen_id, "uuid"),
            DescripteurChamp("matiere_id", "Matière", EpreuveArchivee.matiere_id, "uuid"),
            DescripteurChamp("serie_id", "Série", EpreuveArchivee.serie_id, "uuid"),
            DescripteurChamp("filiere_id", "Filière", EpreuveArchivee.filiere_id, "uuid"),
            DescripteurChamp("niveau_id", "Niveau", EpreuveArchivee.niveau_id, "uuid"),
            DescripteurChamp("annee", "Année", EpreuveArchivee.annee, "nombre"),
            DescripteurChamp("nature", "Nature", EpreuveArchivee.nature, "liste"),
        ),
    )
)

router.include_router(
    creer_routeur_crud(
        modele=BudgetExamen,
        schema_lecture=BudgetLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/budgets-examen",
        tag="Budget",
        ressource="budget",
        libelle_singulier="budget d'examen",
        libelle_pluriel="budgets d'examen",
        champs_recherche=("code", "libelle"),
        champs_filtrables=(
            DescripteurChamp("code", "Code", BudgetExamen.code),
            DescripteurChamp("session_id", "Session", BudgetExamen.session_id, "uuid"),
            DescripteurChamp(
                "montant_prevu", "Montant prévu", BudgetExamen.montant_prevu, "nombre"
            ),
            DescripteurChamp("valide", "Validé", BudgetExamen.valide, "booleen"),
        ),
    )
)
