"""Évaluations, saisie des notes, bulletins et conseils de classe."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import func, select

from app.api.crud import creer_routeur_crud, obtenir_ou_404
from app.api.deps import ContexteDep, MetadonneesDep, SessionDep
from app.core.enums import Action
from app.core.exceptions import BusinessRuleError
from app.engines.audit import journaliser
from app.engines.portee import (
    Portee,
    exiger_apprenant_dans_la_portee,
    exiger_classe_dans_la_portee,
    exiger_evaluation_dans_la_portee,
)
from app.engines.reporting import exporter_csv
from app.engines.search import DescripteurChamp
from app.models.apprenant import Apprenant
from app.models.evaluation import (
    Bulletin,
    ConseilClasse,
    Evaluation,
    MoyenneMatiere,
    Note,
    StatutEvaluation,
    StatutNote,
)
from app.models.scolarite import Classe, Matiere, Periode
from app.schemas.base import MessageReponse
from app.schemas.evaluation import (
    BulletinDetail,
    BulletinLecture,
    BulletinLigne,
    ConseilClasseLecture,
    EvaluationCreation,
    EvaluationLecture,
    EvaluationMiseAJour,
    GenerationBulletins,
    MoyenneMatiereLecture,
    NoteLecture,
    SaisieNotesDemande,
    StatistiquesClasse,
)
from app.services import bulletins as service_bulletins
from app.utils.calculs import (
    ElementNote,
    calculer_rangs,
    determiner_appreciation,
    ecart_type,
    moyenne_ponderee,
    ramener_sur_20,
    taux,
)

router = APIRouter()


# ------------------------------------------------------------------
#  Évaluations
# ------------------------------------------------------------------

evaluations = creer_routeur_crud(
    modele=Evaluation,
    portee=Portee(classe="classe_id", enseignant="enseignant_id"),
    schema_lecture=EvaluationLecture,
    schema_creation=EvaluationCreation,
    schema_maj=EvaluationMiseAJour,
    prefixe="/evaluations",
    tag="Évaluations",
    ressource="evaluations",
    libelle_singulier="évaluation",
    libelle_pluriel="évaluations",
    champs_recherche=("code", "intitule"),
    contrainte_unicite=None,
    tri_defaut="date_evaluation",
    champs_filtrables=(
        DescripteurChamp("code", "Code", Evaluation.code),
        DescripteurChamp("intitule", "Intitulé", Evaluation.intitule),
        DescripteurChamp("classe_id", "Classe", Evaluation.classe_id, "uuid"),
        DescripteurChamp("matiere_id", "Matière", Evaluation.matiere_id, "uuid"),
        DescripteurChamp("periode_id", "Période", Evaluation.periode_id, "uuid"),
        DescripteurChamp("enseignant_id", "Enseignant", Evaluation.enseignant_id, "uuid"),
        DescripteurChamp("type_evaluation", "Type", Evaluation.type_evaluation, "liste"),
        DescripteurChamp("statut", "Statut", Evaluation.statut, "liste"),
        DescripteurChamp("date_evaluation", "Date", Evaluation.date_evaluation, "date"),
        DescripteurChamp("moyenne", "Moyenne", Evaluation.moyenne, "nombre"),
    ),
)


async def _recalculer_statistiques(session, evaluation: Evaluation) -> None:
    """Met à jour les statistiques d'une évaluation après saisie."""
    stmt = select(Note).where(Note.evaluation_id == evaluation.id, Note.statut == StatutNote.SAISIE)
    valeurs = [
        note.valeur for note in (await session.execute(stmt)).scalars() if note.valeur is not None
    ]
    evaluation.nombre_notes = len(valeurs)
    evaluation.moyenne = moyenne_ponderee([ElementNote(v, 1.0) for v in valeurs])
    evaluation.note_min = min(valeurs) if valeurs else None
    evaluation.note_max = max(valeurs) if valeurs else None
    evaluation.ecart_type = ecart_type(valeurs)


@evaluations.post(
    "/{identifiant}/notes",
    response_model=MessageReponse,
    summary="Saisir les notes d'une évaluation",
    description="Saisie groupée : crée ou met à jour la note de chaque apprenant.",
)
async def saisir_notes(
    identifiant: uuid.UUID,
    demande: SaisieNotesDemande,
    session: SessionDep,
    contexte: ContexteDep,
    metadonnees: MetadonneesDep,
) -> MessageReponse:
    contexte.exiger("notes", Action.CREATE)
    evaluation = await obtenir_ou_404(session, Evaluation, identifiant, "Évaluation")

    if evaluation.statut in {StatutEvaluation.VALIDEE_ETABLISSEMENT, StatutEvaluation.PUBLIEE}:
        raise BusinessRuleError(
            "Les notes de cette évaluation sont validées : elles ne sont plus modifiables."
        )

    periode = await session.get(Periode, evaluation.periode_id)
    if periode is not None and not periode.saisie_ouverte:
        raise BusinessRuleError("La saisie est fermée pour cette période.")

    existantes = {
        note.apprenant_id: note
        for note in (
            await session.execute(select(Note).where(Note.evaluation_id == identifiant))
        ).scalars()
    }

    modifiees = 0
    for ligne in demande.notes:
        if ligne.valeur is not None and ligne.valeur > evaluation.bareme:
            raise BusinessRuleError(
                f"La note {ligne.valeur} dépasse le barème de l'évaluation "
                f"({evaluation.bareme:g}).",
                details={"apprenant_id": str(ligne.apprenant_id)},
            )

        note = existantes.get(ligne.apprenant_id)
        if note is None:
            note = Note(evaluation_id=identifiant, apprenant_id=ligne.apprenant_id)
            session.add(note)
        else:
            if note.valeur != ligne.valeur:
                note.ancienne_valeur = note.valeur
                note.modifiee = True

        note.valeur = ligne.valeur
        note.statut = ligne.statut
        note.appreciation = ligne.appreciation or determiner_appreciation(
            ramener_sur_20(ligne.valeur, evaluation.bareme) if ligne.valeur is not None else None
        )
        note.saisie_par_id = contexte.id
        modifiees += 1

    evaluation.statut = StatutEvaluation.SAISIE_TERMINEE
    await session.flush()
    await _recalculer_statistiques(session, evaluation)

    # Rangs internes à l'évaluation.
    stmt = select(Note).where(Note.evaluation_id == identifiant)
    notes = list((await session.execute(stmt)).scalars())
    rangs = calculer_rangs({str(n.apprenant_id): n.valeur for n in notes})
    for note in notes:
        note.rang = rangs.get(str(note.apprenant_id))

    await session.flush()
    await journaliser(
        session,
        action=Action.UPDATE,
        entite_type="notes",
        entite_id=evaluation.id,
        entite_libelle=evaluation.intitule,
        utilisateur_id=contexte.id,
        utilisateur_email=contexte.email,
        valeurs_apres={"notes_saisies": modifiees},
        adresse_ip=metadonnees["adresse_ip"],
    )
    return MessageReponse(
        message="Notes enregistrées.",
        details={"notes": modifiees, "moyenne": evaluation.moyenne},
    )


@evaluations.get(
    "/{identifiant}/notes",
    response_model=list[NoteLecture],
    summary="Notes d'une évaluation",
)
async def lister_notes(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> list[Note]:
    contexte.exiger("notes", Action.READ)
    await exiger_evaluation_dans_la_portee(session, contexte, identifiant)
    stmt = (
        select(Note)
        .join(Apprenant, Apprenant.id == Note.apprenant_id)
        .where(Note.evaluation_id == identifiant)
        .order_by(Apprenant.nom, Apprenant.prenoms)
    )
    return list((await session.execute(stmt)).scalars())


@evaluations.post(
    "/{identifiant}/valider",
    response_model=EvaluationLecture,
    summary="Valider une évaluation",
    description="Passe l'évaluation de la validation enseignant à la publication.",
)
async def valider_evaluation(
    identifiant: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
    niveau: Annotated[
        str, Query(pattern="^(enseignant|etablissement|publication)$")
    ] = "enseignant",
) -> Evaluation:
    contexte.exiger("notes", Action.VALIDATE)
    evaluation = await obtenir_ou_404(session, Evaluation, identifiant, "Évaluation")
    horodatage = datetime.now(UTC)

    if niveau == "enseignant":
        if evaluation.statut is StatutEvaluation.PLANIFIEE:
            raise BusinessRuleError("Les notes doivent être saisies avant validation.")
        evaluation.statut = StatutEvaluation.VALIDEE_ENSEIGNANT
        evaluation.valide_enseignant_le = horodatage
    elif niveau == "etablissement":
        if evaluation.statut is not StatutEvaluation.VALIDEE_ENSEIGNANT:
            raise BusinessRuleError("L'enseignant doit valider avant l'établissement.")
        evaluation.statut = StatutEvaluation.VALIDEE_ETABLISSEMENT
        evaluation.valide_etablissement_le = horodatage
    else:
        if evaluation.statut is not StatutEvaluation.VALIDEE_ETABLISSEMENT:
            raise BusinessRuleError("L'établissement doit valider avant publication.")
        evaluation.statut = StatutEvaluation.PUBLIEE
        evaluation.publiee_le = horodatage

    await session.flush()
    return evaluation


router.include_router(evaluations)


# ------------------------------------------------------------------
#  Bulletins
# ------------------------------------------------------------------

bulletins = creer_routeur_crud(
    modele=Bulletin,
    # Le bulletin appartient à son élève, pas à sa classe : le rattacher à la
    # classe en ouvrirait la lecture à tous ses camarades. L'établissement suffit
    # aux rôles qui doivent en consulter plusieurs, et n'est pas partagé avec
    # les usagers personnels.
    portee=Portee(apprenant="apprenant_id", etablissement="etablissement_id"),
    schema_lecture=BulletinLecture,
    schema_creation=None,
    schema_maj=None,
    prefixe="/bulletins",
    tag="Bulletins",
    ressource="bulletins",
    libelle_singulier="bulletin",
    libelle_pluriel="bulletins",
    champs_recherche=("numero",),
    tri_defaut="numero",
    champs_filtrables=(
        DescripteurChamp("numero", "Numéro", Bulletin.numero),
        DescripteurChamp("apprenant_id", "Apprenant", Bulletin.apprenant_id, "uuid"),
        DescripteurChamp("classe_id", "Classe", Bulletin.classe_id, "uuid"),
        DescripteurChamp("periode_id", "Période", Bulletin.periode_id, "uuid"),
        DescripteurChamp("etablissement_id", "Établissement", Bulletin.etablissement_id, "uuid"),
        DescripteurChamp(
            "moyenne_generale", "Moyenne générale", Bulletin.moyenne_generale, "nombre"
        ),
        DescripteurChamp("rang", "Rang", Bulletin.rang, "nombre"),
        DescripteurChamp("mention", "Mention", Bulletin.mention, "liste"),
        DescripteurChamp("decision", "Décision", Bulletin.decision, "liste"),
        DescripteurChamp("publie", "Publié", Bulletin.publie, "booleen"),
    ),
)


@bulletins.post(
    "/generer",
    status_code=status.HTTP_201_CREATED,
    summary="Calculer les bulletins d'une classe",
    description=(
        "Recalcule moyennes, rangs et appréciations, puis produit un bulletin par "
        "apprenant. L'opération est idempotente et remplace les bulletins existants."
    ),
)
async def generer_bulletins(
    demande: GenerationBulletins,
    session: SessionDep,
    contexte: ContexteDep,
    metadonnees: MetadonneesDep,
) -> dict:
    contexte.exiger("bulletins", Action.CREATE)
    produits = await service_bulletins.calculer_bulletins(
        session, demande.classe_id, demande.periode_id, publier=demande.publier
    )
    await journaliser(
        session,
        action=Action.CREATE,
        entite_type="bulletins",
        entite_id=demande.classe_id,
        entite_libelle=f"{len(produits)} bulletins",
        utilisateur_id=contexte.id,
        utilisateur_email=contexte.email,
        adresse_ip=metadonnees["adresse_ip"],
    )
    return {
        "bulletins_generes": len(produits),
        "publies": demande.publier,
        "moyenne_classe": produits[0].moyenne_classe if produits else None,
    }


@bulletins.get(
    "/{identifiant}/detail",
    response_model=BulletinDetail,
    summary="Bulletin détaillé",
)
async def detail_bulletin(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> BulletinDetail:
    contexte.exiger("bulletins", Action.READ)
    bulletin = await service_bulletins.charger_bulletin_complet(session, identifiant)

    detail = BulletinDetail.model_validate(bulletin)
    detail.apprenant_nom = bulletin.apprenant.nom_complet if bulletin.apprenant else None
    detail.apprenant_identifiant = (
        bulletin.apprenant.identifiant_educatif if bulletin.apprenant else None
    )
    detail.classe_libelle = bulletin.classe.libelle if bulletin.classe else None
    detail.etablissement_nom = (
        bulletin.classe.etablissement.nom
        if bulletin.classe and bulletin.classe.etablissement
        else None
    )
    detail.periode_libelle = bulletin.periode.libelle if bulletin.periode else None
    detail.annee_libelle = (
        bulletin.classe.annee.code if bulletin.classe and bulletin.classe.annee else None
    )
    detail.lignes = [
        BulletinLigne(
            matiere_id=ligne.matiere_id,
            matiere_libelle=ligne.matiere.libelle if ligne.matiere else None,
            enseignant_nom=ligne.enseignant_nom,
            moyenne=ligne.moyenne,
            coefficient=ligne.coefficient,
            points=ligne.points,
            rang=ligne.rang,
            moyenne_classe=ligne.moyenne_classe,
            note_min=ligne.note_min,
            note_max=ligne.note_max,
            appreciation=ligne.appreciation,
        )
        for ligne in sorted(bulletin.lignes, key=lambda item: item.ordre)
    ]
    return detail


@bulletins.get(
    "/{identifiant}/pdf",
    summary="Télécharger le bulletin en PDF",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def bulletin_pdf(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> Response:
    contexte.exiger("bulletins", Action.PRINT)
    bulletin, contenu = await service_bulletins.generer_pdf(session, identifiant)
    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="bulletin-{bulletin.numero}.pdf"'},
    )


@bulletins.post(
    "/{identifiant}/publier",
    response_model=BulletinLecture,
    summary="Publier un bulletin",
)
async def publier_bulletin(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> Bulletin:
    contexte.exiger("bulletins", Action.PUBLISH)
    bulletin = await obtenir_ou_404(session, Bulletin, identifiant, "Bulletin")
    bulletin.publie = True
    bulletin.publie_le = datetime.now(UTC)
    await session.flush()
    return bulletin


@bulletins.get(
    "/classe/{classe_id}/export",
    summary="Exporter les bulletins d'une classe",
    description="Export CSV des moyennes générales, rangs et décisions.",
    response_class=Response,
)
async def exporter_classe(
    classe_id: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
    periode_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Response:
    contexte.exiger("bulletins", Action.EXPORT)
    stmt = (
        select(Bulletin, Apprenant)
        .join(Apprenant, Apprenant.id == Bulletin.apprenant_id)
        .where(Bulletin.classe_id == classe_id)
        .order_by(Bulletin.rang)
    )
    if periode_id:
        stmt = stmt.where(Bulletin.periode_id == periode_id)

    lignes = [
        [
            bulletin.rang,
            apprenant.identifiant_educatif,
            apprenant.nom,
            apprenant.prenoms,
            apprenant.sexe.value,
            bulletin.moyenne_generale,
            bulletin.mention,
            bulletin.decision.value if bulletin.decision else None,
            bulletin.absences_heures,
            bulletin.retards,
        ]
        for bulletin, apprenant in (await session.execute(stmt)).all()
    ]

    contenu = exporter_csv(
        [
            "Rang",
            "Identifiant",
            "Nom",
            "Prénoms",
            "Sexe",
            "Moyenne",
            "Mention",
            "Décision",
            "Absences (h)",
            "Retards",
        ],
        lignes,
    )
    return Response(
        content=contenu,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="bulletins-classe.csv"'},
    )


router.include_router(bulletins)


# ------------------------------------------------------------------
#  Moyennes, conseils et statistiques
# ------------------------------------------------------------------


@router.get(
    "/apprenants/{identifiant}/moyennes",
    response_model=list[MoyenneMatiereLecture],
    tags=["Bulletins"],
    summary="Moyennes par matière d'un apprenant",
)
async def moyennes_apprenant(
    identifiant: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
    periode_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[MoyenneMatiereLecture]:
    contexte.exiger("notes", Action.READ)
    # Les moyennes prolongent la fiche d'un apprenant : sans cadrage,
    # « notes:READ » ouvrait celles de n'importe quel élève du pays.
    await exiger_apprenant_dans_la_portee(session, contexte, identifiant)
    stmt = (
        select(MoyenneMatiere, Matiere)
        .join(Matiere, Matiere.id == MoyenneMatiere.matiere_id)
        .where(MoyenneMatiere.apprenant_id == identifiant)
        .order_by(Matiere.libelle)
    )
    if periode_id:
        stmt = stmt.where(MoyenneMatiere.periode_id == periode_id)

    return [
        MoyenneMatiereLecture(
            matiere_id=moyenne.matiere_id,
            matiere_libelle=matiere.libelle,
            moyenne=moyenne.moyenne,
            coefficient=moyenne.coefficient,
            rang=moyenne.rang,
            moyenne_classe=moyenne.moyenne_classe,
            note_min_classe=moyenne.note_min_classe,
            note_max_classe=moyenne.note_max_classe,
            appreciation=moyenne.appreciation,
        )
        for moyenne, matiere in (await session.execute(stmt)).all()
    ]


@router.get(
    "/classes/{identifiant}/statistiques",
    response_model=StatistiquesClasse,
    tags=["Bulletins"],
    summary="Statistiques d'une classe",
)
async def statistiques_classe(
    identifiant: uuid.UUID,
    periode_id: Annotated[uuid.UUID, Query()],
    session: SessionDep,
    contexte: ContexteDep,
) -> StatistiquesClasse:
    contexte.exiger("analytics", Action.READ)
    classe = await obtenir_ou_404(session, Classe, identifiant, "Classe")
    # Sans cette vérification, un enseignant lisait les statistiques de
    # n'importe quelle classe du pays : la permission ouvre la fonction, elle ne
    # désigne pas les classes auxquelles elle s'applique.
    await exiger_classe_dans_la_portee(session, contexte, identifiant)
    periode = await obtenir_ou_404(session, Periode, periode_id, "Période")

    stmt = select(Bulletin.moyenne_generale).where(
        Bulletin.classe_id == identifiant,
        Bulletin.periode_id == periode_id,
        Bulletin.moyenne_generale.isnot(None),
    )
    moyennes = [float(v) for v in (await session.execute(stmt)).scalars()]

    bornes = (0, 5, 8, 10, 12, 14, 16, 18, 20.01)
    distribution = [
        {
            "tranche": f"[{bornes[i]:g} ; {bornes[i + 1]:g}[",
            "effectif": sum(1 for m in moyennes if bornes[i] <= m < bornes[i + 1]),
        }
        for i in range(len(bornes) - 1)
    ]

    stmt = (
        select(
            Matiere.libelle,
            func.avg(MoyenneMatiere.moyenne),
            func.min(MoyenneMatiere.moyenne),
            func.max(MoyenneMatiere.moyenne),
            func.count(MoyenneMatiere.id),
        )
        .join(Matiere, Matiere.id == MoyenneMatiere.matiere_id)
        .where(MoyenneMatiere.classe_id == identifiant, MoyenneMatiere.periode_id == periode_id)
        .group_by(Matiere.libelle)
        .order_by(Matiere.libelle)
    )
    par_matiere = [
        {
            "matiere": libelle,
            "moyenne": round(float(moyenne), 2) if moyenne is not None else None,
            "minimum": round(float(mini), 2) if mini is not None else None,
            "maximum": round(float(maxi), 2) if maxi is not None else None,
            "effectif": effectif,
        }
        for libelle, moyenne, mini, maxi, effectif in (await session.execute(stmt)).all()
    ]

    reussite = sum(1 for m in moyennes if m >= 10)
    return StatistiquesClasse(
        classe_id=identifiant,
        classe_libelle=classe.libelle,
        periode_libelle=periode.libelle,
        effectif=len(moyennes),
        moyenne_classe=round(sum(moyennes) / len(moyennes), 2) if moyennes else None,
        moyenne_maximale=max(moyennes) if moyennes else None,
        moyenne_minimale=min(moyennes) if moyennes else None,
        nombre_moyennes_superieures_10=reussite,
        taux_reussite=taux(reussite, len(moyennes) or 1),
        distribution=distribution,
        par_matiere=par_matiere,
    )


router.include_router(
    creer_routeur_crud(
        modele=ConseilClasse,
        portee=Portee(classe="classe_id"),
        schema_lecture=ConseilClasseLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/conseils-classe",
        tag="Bulletins",
        ressource="conseils",
        libelle_singulier="conseil de classe",
        libelle_pluriel="conseils de classe",
        champs_recherche=(),
        tri_defaut="date_conseil",
        champs_filtrables=(
            DescripteurChamp("classe_id", "Classe", ConseilClasse.classe_id, "uuid"),
            DescripteurChamp("periode_id", "Période", ConseilClasse.periode_id, "uuid"),
            DescripteurChamp("cloture", "Clôturé", ConseilClasse.cloture, "booleen"),
        ),
    )
)
