"""Services ouverts au public : consultation des résultats et vérification de documents."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import func, or_, select

from app.api.deps import SessionDep
from app.core.exceptions import NotFoundError
from app.models.diplome import Attestation, DiplomeDelivre, StatutDiplome, VerificationDocument
from app.models.evaluation import Bulletin
from app.models.examen import (
    Candidat,
    CentreComposition,
    DecisionExamen,
    Examen,
    ResultatExamen,
    SessionExamen,
)
from app.models.scolarite import Serie
from app.schemas.examen import ResultatPublic, VerificationDiplomeReponse
from app.services import examens as service

router = APIRouter(prefix="/public", tags=["Services publics"])


@router.get(
    "/sessions",
    summary="Sessions dont les résultats sont publiés",
    description="Accessible sans authentification, pour la consultation des résultats.",
)
async def sessions_publiees(session: SessionDep) -> list[dict]:
    stmt = (
        select(SessionExamen, Examen)
        .join(Examen, Examen.id == SessionExamen.examen_id)
        .where(SessionExamen.resultats_publies_le.isnot(None))
        .order_by(SessionExamen.annee.desc(), Examen.nom)
    )
    return [
        {
            "id": str(session_examen.id),
            "code": session_examen.code,
            "libelle": session_examen.libelle,
            "examen": examen.nom,
            "sigle": examen.sigle,
            "annee": session_examen.annee,
            "nombre_inscrits": session_examen.nombre_inscrits,
            "nombre_admis": session_examen.nombre_admis,
            "taux_reussite": session_examen.taux_reussite,
            "date_publication": session_examen.date_publication_resultats.isoformat()
            if session_examen.date_publication_resultats
            else None,
        }
        for session_examen, examen in (await session.execute(stmt)).all()
    ]


@router.get(
    "/resultats",
    response_model=ResultatPublic,
    summary="Consulter un résultat d'examen",
    description=(
        "Recherche par numéro de table ou numéro de candidat. "
        "Seuls les résultats publiés sont accessibles."
    ),
)
async def consulter_resultat(
    session: SessionDep,
    numero: Annotated[str, Query(min_length=3, description="Numéro de table ou de candidat")],
    session_id: Annotated[str | None, Query()] = None,
) -> ResultatPublic:
    reference = numero.strip().upper()
    stmt = (
        select(ResultatExamen, Candidat, SessionExamen, Examen, Serie, CentreComposition)
        .join(Candidat, Candidat.id == ResultatExamen.candidat_id)
        .join(SessionExamen, SessionExamen.id == ResultatExamen.session_id)
        .join(Examen, Examen.id == SessionExamen.examen_id)
        .outerjoin(Serie, Serie.id == Candidat.serie_id)
        .outerjoin(CentreComposition, CentreComposition.id == Candidat.centre_id)
        .where(
            ResultatExamen.publie.is_(True),
            or_(
                func.upper(Candidat.numero_table) == reference,
                func.upper(Candidat.numero_candidat) == reference,
            ),
        )
        .limit(1)
    )
    if session_id:
        stmt = stmt.where(ResultatExamen.session_id == session_id)

    ligne = (await session.execute(stmt)).first()
    if ligne is None:
        raise NotFoundError(
            "Aucun résultat publié ne correspond à ce numéro.",
            details={"numero": reference},
        )

    resultat, candidat, session_examen, examen, serie, centre = ligne
    return ResultatPublic(
        numero_candidat=candidat.numero_candidat,
        numero_table=candidat.numero_table,
        nom_complet=candidat.nom_complet,
        examen=examen.nom,
        session=session_examen.libelle,
        serie=serie.code if serie else None,
        centre=centre.nom if centre else None,
        moyenne=resultat.moyenne,
        mention=resultat.mention,
        decision=resultat.decision,
        rang_national=resultat.rang_national,
        code_verification=resultat.code_verification,
    )


@router.get(
    "/resultats/{session_id}/statistiques",
    summary="Statistiques publiques d'une session",
)
async def statistiques_publiques(session_id: str, session: SessionDep) -> dict:
    session_examen = await service.charger_session(session, session_id)
    if session_examen.resultats_publies_le is None:
        raise NotFoundError("Les résultats de cette session ne sont pas encore publiés.")

    stmt = (
        select(ResultatExamen.mention, func.count())
        .where(
            ResultatExamen.session_id == session_id,
            ResultatExamen.decision == DecisionExamen.ADMIS,
        )
        .group_by(ResultatExamen.mention)
    )
    mentions = {
        mention or "Sans mention": total for mention, total in (await session.execute(stmt)).all()
    }

    return {
        "session": session_examen.libelle,
        "annee": session_examen.annee,
        "inscrits": session_examen.nombre_inscrits,
        "presents": session_examen.nombre_presents,
        "absents": session_examen.nombre_absents,
        "admis": session_examen.nombre_admis,
        "taux_reussite": session_examen.taux_reussite,
        "moyenne_generale": session_examen.moyenne_generale,
        "mentions": mentions,
    }


@router.get(
    "/verification/{code}",
    response_model=VerificationDiplomeReponse,
    summary="Vérifier l'authenticité d'un document",
    description=(
        "Contrôle un diplôme, une attestation, un relevé ou un bulletin à partir "
        "de son code de vérification ou du contenu de son QR code."
    ),
)
async def verifier(code: str, session: SessionDep, request: Request) -> VerificationDiplomeReponse:
    reference = code.strip().upper()
    client = request.client

    async def tracer(valide: bool, type_document: str | None, document_id=None) -> None:
        session.add(
            VerificationDocument(
                code_verification=reference,
                type_document=type_document or "INCONNU",
                document_id=document_id,
                resultat_valide=valide,
                adresse_ip=client.host if client else None,
                agent_utilisateur=request.headers.get("user-agent"),
                verifie_le=datetime.now(UTC),
            )
        )

    diplome = (
        await session.execute(
            select(DiplomeDelivre).where(DiplomeDelivre.code_verification == reference)
        )
    ).scalar_one_or_none()
    if diplome is not None:
        valide = diplome.statut in {StatutDiplome.EMIS, StatutDiplome.REMIS}
        diplome.nombre_verifications += 1
        await tracer(valide, "DIPLOME", diplome.id)
        return VerificationDiplomeReponse(
            valide=valide,
            message="Diplôme authentique." if valide else "Ce diplôme a été annulé ou suspendu.",
            type_document="DIPLOME",
            numero=diplome.numero,
            titulaire=diplome.titulaire_nom,
            intitule=diplome.intitule,
            session=diplome.session_libelle,
            annee=diplome.annee,
            mention=diplome.mention,
            date_delivrance=diplome.date_delivrance,
        )

    attestation = (
        await session.execute(select(Attestation).where(Attestation.code_verification == reference))
    ).scalar_one_or_none()
    if attestation is not None:
        valide = not attestation.annulee
        await tracer(valide, "ATTESTATION", attestation.id)
        return VerificationDiplomeReponse(
            valide=valide,
            message="Attestation authentique." if valide else "Cette attestation a été annulée.",
            type_document=attestation.type_attestation.value,
            numero=attestation.numero,
            titulaire=attestation.titulaire_nom,
            intitule=attestation.objet,
            date_delivrance=attestation.date_delivrance,
        )

    resultat = (
        await session.execute(
            select(ResultatExamen, Candidat, SessionExamen)
            .join(Candidat, Candidat.id == ResultatExamen.candidat_id)
            .join(SessionExamen, SessionExamen.id == ResultatExamen.session_id)
            .where(ResultatExamen.code_verification == reference)
        )
    ).first()
    if resultat is not None:
        ligne, candidat, session_examen = resultat
        await tracer(ligne.publie, "RELEVE", ligne.id)
        return VerificationDiplomeReponse(
            valide=ligne.publie,
            message="Relevé de notes authentique."
            if ligne.publie
            else "Ce relevé n'est pas encore publié.",
            type_document="RELEVE",
            numero=candidat.numero_candidat,
            titulaire=candidat.nom_complet,
            intitule=f"Relevé de notes — {session_examen.libelle}",
            session=session_examen.libelle,
            annee=session_examen.annee,
            mention=ligne.mention,
        )

    bulletin = (
        await session.execute(select(Bulletin).where(Bulletin.code_verification == reference))
    ).scalar_one_or_none()
    if bulletin is not None:
        await tracer(bulletin.publie, "BULLETIN", bulletin.id)
        return VerificationDiplomeReponse(
            valide=bulletin.publie,
            message="Bulletin authentique."
            if bulletin.publie
            else "Ce bulletin n'est pas encore publié.",
            type_document="BULLETIN",
            numero=bulletin.numero,
            intitule="Bulletin de notes",
            mention=bulletin.mention,
        )

    await tracer(False, None)
    return VerificationDiplomeReponse(
        valide=False,
        message="Aucun document ne correspond à ce code de vérification.",
    )


@router.get(
    "/diplomes/{code}/pdf",
    summary="Télécharger un diplôme vérifié",
    response_class=Response,
)
async def diplome_pdf(code: str, session: SessionDep) -> Response:
    diplome = (
        await session.execute(
            select(DiplomeDelivre).where(DiplomeDelivre.code_verification == code.strip().upper())
        )
    ).scalar_one_or_none()
    if diplome is None:
        raise NotFoundError("Aucun diplôme ne correspond à ce code.")
    if diplome.statut not in {StatutDiplome.EMIS, StatutDiplome.REMIS}:
        raise NotFoundError("Ce diplôme n'est plus valide.")

    contenu = service.composer_pdf_diplome(diplome)
    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="diplome-{diplome.numero.replace("/", "-")}.pdf"'
            )
        },
    )


@router.get(
    "/accessibilite",
    summary="Options d'accessibilité disponibles",
    description="Décrit les aménagements proposés par la plateforme.",
)
async def options_accessibilite() -> dict:
    return {
        "affichage": [
            {"cle": "contraste_eleve", "libelle": "Contraste élevé"},
            {"cle": "grande_police", "libelle": "Grande police"},
            {"cle": "mode_simplifie", "libelle": "Interface simplifiée à pictogrammes"},
        ],
        "audio": [
            {"cle": "lecture_vocale", "libelle": "Lecture vocale des contenus"},
            {"cle": "transcription", "libelle": "Transcription des vidéos"},
            {"cle": "sous_titres", "libelle": "Sous-titrage"},
        ],
        "navigation": [
            {"cle": "clavier", "libelle": "Navigation clavier complète"},
            {"cle": "lecteur_ecran", "libelle": "Compatibilité lecteur d'écran"},
        ],
        "langues": ["FR", "FON", "YORUBA", "BARIBA", "DENDI", "ADJA", "EN"],
        "examens": [
            {"cle": "tiers_temps", "libelle": "Tiers temps supplémentaire"},
            {"cle": "salle_amenagee", "libelle": "Salle de composition aménagée"},
            {"cle": "secretaire", "libelle": "Secrétaire d'examen"},
            {"cle": "braille", "libelle": "Sujets en braille"},
            {"cle": "interprete", "libelle": "Interprète en langue des signes"},
        ],
    }
