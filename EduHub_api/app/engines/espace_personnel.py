"""Tableaux de bord propres à chaque rôle.

Le tableau de bord national consolide les chiffres du pilotage : effectifs du
pays, parité, taux de réussite. Il répond à la question d'un ministère, pas à
celle d'un élève, qui veut savoir sa moyenne, son rang et ses prochains
devoirs.

Ce module compose, pour chaque famille de rôles, les indicateurs qui la
concernent, en s'en tenant strictement au périmètre déjà résolu par le moteur
de portée. Un parent n'y voit que ses enfants, un enseignant que son
établissement.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.analytics import Indicateur
from app.engines.identity import ContexteUtilisateur
from app.engines.portee import PerimetrePersonnel
from app.models.apprenant import Apprenant
from app.models.evaluation import Bulletin, Evaluation
from app.models.pedagogie import Presence
from app.models.personnel import Enseignant
from app.models.scolarite import Classe, Inscription

#: Statuts comptés comme une absence. Le retard n'en est pas une : l'élève a
#: bien assisté au cours, et l'agréger fausserait la lecture du taux.
_ABSENCES = ("ABSENT", "ABSENCE_JUSTIFIEE", "ABSENCE_INJUSTIFIEE", "EXCLU_COURS")


async def _moyenne_et_rang(
    session: AsyncSession, apprenants: set[uuid.UUID]
) -> tuple[float | None, int | None, int | None]:
    """Dernier bulletin connu : moyenne générale, rang et effectif de la classe."""
    if not apprenants:
        return None, None, None
    ligne = (
        await session.execute(
            select(Bulletin.moyenne_generale, Bulletin.rang, Bulletin.effectif_classe)
            .where(
                Bulletin.apprenant_id.in_(apprenants),
                Bulletin.moyenne_generale.isnot(None),
            )
            .order_by(Bulletin.created_at.desc())
            .limit(1)
        )
    ).first()
    return ligne if ligne is not None else (None, None, None)


async def _taux_presence(session: AsyncSession, apprenants: set[uuid.UUID]) -> float | None:
    """Part des séances où l'apprenant était présent, sur l'ensemble des relevés."""
    if not apprenants:
        return None
    total = await session.scalar(
        select(func.count()).select_from(Presence).where(Presence.apprenant_id.in_(apprenants))
    )
    if not total:
        return None
    absences = await session.scalar(
        select(func.count())
        .select_from(Presence)
        .where(Presence.apprenant_id.in_(apprenants), Presence.statut.in_(_ABSENCES))
    )
    return round(100 * (total - (absences or 0)) / total, 1)


def _compter(modele: type, condition) -> Select:
    return select(func.count()).select_from(modele).where(condition)


async def indicateurs_eleve(
    session: AsyncSession, perimetre: PerimetrePersonnel
) -> list[Indicateur]:
    """Ce qu'un élève veut voir en arrivant : où il en est."""
    moyenne, rang, effectif = await _moyenne_et_rang(session, perimetre.apprenants)
    presence = await _taux_presence(session, perimetre.apprenants)

    bulletins = await session.scalar(
        _compter(Bulletin, Bulletin.apprenant_id.in_(perimetre.apprenants or {uuid.uuid4()}))
    )
    # Les évaluations à venir dans ses classes, pour anticiper.
    a_venir = await session.scalar(
        _compter(
            Evaluation,
            Evaluation.classe_id.in_(perimetre.classes or {uuid.uuid4()}),
        ).where(Evaluation.date_evaluation >= date.today())
    )

    indicateurs = [
        Indicateur("moyenne_generale", "Ma moyenne générale", moyenne or 0, "sur 20"),
        Indicateur("rang", "Mon rang", rang or 0, f"sur {effectif}" if effectif else None),
        Indicateur("taux_presence", "Mon assiduité", presence or 0, "%"),
        Indicateur("bulletins", "Mes bulletins", bulletins or 0),
        Indicateur("evaluations_a_venir", "Évaluations à venir", a_venir or 0),
    ]
    return indicateurs


async def indicateurs_parent(
    session: AsyncSession, perimetre: PerimetrePersonnel
) -> list[Indicateur]:
    """Le suivi d'un parent porte sur ses enfants, pas sur lui."""
    moyenne, rang, effectif = await _moyenne_et_rang(session, perimetre.apprenants)
    presence = await _taux_presence(session, perimetre.apprenants)
    bulletins = await session.scalar(
        _compter(Bulletin, Bulletin.apprenant_id.in_(perimetre.apprenants or {uuid.uuid4()}))
    )

    return [
        Indicateur("enfants", "Mes enfants", len(perimetre.apprenants)),
        Indicateur("moyenne_generale", "Dernière moyenne", moyenne or 0, "sur 20"),
        Indicateur("rang", "Rang", rang or 0, f"sur {effectif}" if effectif else None),
        Indicateur("taux_presence", "Assiduité", presence or 0, "%"),
        Indicateur("bulletins", "Bulletins disponibles", bulletins or 0),
    ]


async def indicateurs_enseignant(
    session: AsyncSession, contexte: ContexteUtilisateur, perimetre: PerimetrePersonnel
) -> list[Indicateur]:
    """Un enseignant pilote ses classes, ses évaluations et ses saisies."""
    enseignant_id = await session.scalar(
        select(Enseignant.id).where(Enseignant.utilisateur_id == contexte.id)
    )
    jeton = {enseignant_id} if enseignant_id else {uuid.uuid4()}

    classes = await session.scalar(
        _compter(Evaluation, Evaluation.enseignant_id.in_(jeton)).with_only_columns(
            func.count(func.distinct(Evaluation.classe_id))
        )
    )
    evaluations = await session.scalar(_compter(Evaluation, Evaluation.enseignant_id.in_(jeton)))
    # Une évaluation passée dont les notes ne sont pas publiées reste à traiter.
    a_corriger = await session.scalar(
        _compter(Evaluation, Evaluation.enseignant_id.in_(jeton)).where(
            Evaluation.date_evaluation < date.today(), Evaluation.publiee_le.is_(None)
        )
    )
    eleves = await session.scalar(
        _compter(
            Inscription,
            Inscription.etablissement_id.in_(perimetre.etablissements or {uuid.uuid4()}),
        ).with_only_columns(func.count(func.distinct(Inscription.apprenant_id)))
    )

    return [
        Indicateur("mes_classes", "Mes classes", classes or 0),
        Indicateur("mes_evaluations", "Mes évaluations", evaluations or 0),
        Indicateur("a_corriger", "Notes à publier", a_corriger or 0),
        Indicateur("eleves_etablissement", "Élèves de l'établissement", eleves or 0),
    ]


async def indicateurs_etablissement(
    session: AsyncSession, perimetre: PerimetrePersonnel
) -> list[Indicateur]:
    """La vue d'un chef d'établissement : son école, et elle seule."""
    etablissements = perimetre.etablissements or {uuid.uuid4()}

    eleves = await session.scalar(
        _compter(Inscription, Inscription.etablissement_id.in_(etablissements)).with_only_columns(
            func.count(func.distinct(Inscription.apprenant_id))
        )
    )
    classes = await session.scalar(_compter(Classe, Classe.etablissement_id.in_(etablissements)))
    enseignants = await session.scalar(
        _compter(Enseignant, Enseignant.etablissement_principal_id.in_(etablissements))
    )
    moyenne = await session.scalar(
        select(func.avg(Bulletin.moyenne_generale)).where(
            Bulletin.etablissement_id.in_(etablissements), Bulletin.moyenne_generale.isnot(None)
        )
    )
    filles = await session.scalar(
        select(func.count(func.distinct(Inscription.apprenant_id)))
        .select_from(Inscription)
        .join(Apprenant, Apprenant.id == Inscription.apprenant_id)
        .where(Inscription.etablissement_id.in_(etablissements), Apprenant.sexe == "FEMININ")
    )

    return [
        Indicateur("eleves", "Élèves inscrits", eleves or 0),
        Indicateur("classes", "Classes", classes or 0),
        Indicateur("enseignants", "Enseignants", enseignants or 0),
        Indicateur("moyenne", "Moyenne de l'établissement", round(moyenne or 0, 2), "sur 20"),
        Indicateur(
            "part_filles",
            "Part des filles",
            round(100 * (filles or 0) / eleves, 1) if eleves else 0,
            "%",
        ),
    ]
