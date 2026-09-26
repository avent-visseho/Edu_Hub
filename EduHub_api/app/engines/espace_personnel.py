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
from app.models.scolarite import Classe, Inscription, Matiere, Niveau, Periode

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


async def evolution_moyennes(
    session: AsyncSession, apprenants: set[uuid.UUID]
) -> list[dict[str, object]]:
    """Moyenne générale période par période, pour situer une progression.

    Un chiffre isolé ne dit pas grand-chose : savoir qu'on est passé de 9 à 12
    en dit plus que la valeur seule. Les bulletins sont rendus dans l'ordre où
    ils ont été établis, moyenne de la classe comprise pour donner un repère.
    """
    if not apprenants:
        return []
    lignes = await session.execute(
        select(
            Periode.libelle,
            Bulletin.moyenne_generale,
            Bulletin.moyenne_classe,
            Bulletin.rang,
        )
        .join(Periode, Periode.id == Bulletin.periode_id)
        .where(Bulletin.apprenant_id.in_(apprenants), Bulletin.moyenne_generale.isnot(None))
        .order_by(Periode.numero, Bulletin.created_at)
        .limit(12)
    )
    return [
        {
            "periode": libelle,
            "ma_moyenne": round(moyenne, 2),
            "moyenne_classe": round(moyenne_classe, 2) if moyenne_classe is not None else None,
            "rang": rang,
        }
        for libelle, moyenne, moyenne_classe, rang in lignes
    ]


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
    """Le suivi d'un parent porte sur ses enfants, nommément.

    Agréger plusieurs enfants n'aurait pas de sens : « dernière moyenne 11,5 »
    ne dirait pas de qui il s'agit, et mélangerait l'aîné qui décroche avec la
    cadette qui réussit. Chaque enfant a donc ses propres indicateurs, préfixés
    de son prénom.
    """
    if not perimetre.apprenants:
        return [Indicateur("enfants", "Mes enfants", 0)]

    enfants = list(
        await session.execute(
            select(Apprenant.id, Apprenant.prenoms, Apprenant.nom)
            .where(Apprenant.id.in_(perimetre.apprenants))
            .order_by(Apprenant.date_naissance)
        )
    )

    indicateurs = [Indicateur("enfants", "Mes enfants", len(enfants))]
    for identifiant, prenoms, nom in enfants:
        seul = {identifiant}
        moyenne, rang, effectif = await _moyenne_et_rang(session, seul)
        presence = await _taux_presence(session, seul)
        # Le prénom suffit à distinguer, sauf homonymie dans la fratrie.
        appel = prenoms.split()[0] if prenoms else nom
        suffixe = str(identifiant)[:8]
        indicateurs.extend(
            [
                Indicateur(
                    f"moyenne_{suffixe}",
                    f"Moyenne de {appel}",
                    moyenne or 0,
                    "sur 20",
                    detail={"apprenant_id": str(identifiant)},
                ),
                Indicateur(
                    f"rang_{suffixe}",
                    f"Rang de {appel}",
                    rang or 0,
                    f"sur {effectif}" if effectif else None,
                ),
                Indicateur(
                    f"presence_{suffixe}",
                    f"Assiduité de {appel}",
                    presence or 0,
                    "%",
                ),
            ]
        )
    return indicateurs


async def prochaines_evaluations(
    session: AsyncSession, classes: set[uuid.UUID]
) -> list[dict[str, object]]:
    """Les devoirs à venir dans les classes de l'élève.

    Un compteur annonçant « dix-huit évaluations à venir » n'aide personne à
    s'organiser : c'est la matière et la date qui comptent. On s'arrête à six,
    au-delà l'horizon cesse d'être utile.
    """
    if not classes:
        return []
    lignes = await session.execute(
        select(
            Evaluation.intitule,
            Evaluation.date_evaluation,
            Matiere.libelle,
            Evaluation.type_evaluation,
            Evaluation.coefficient,
        )
        .join(Matiere, Matiere.id == Evaluation.matiere_id)
        .where(Evaluation.classe_id.in_(classes), Evaluation.date_evaluation >= date.today())
        .order_by(Evaluation.date_evaluation)
        .limit(6)
    )
    return [
        {
            "intitule": intitule,
            "date": echeance.isoformat(),
            "matiere": matiere,
            "type": type_evaluation.value if hasattr(type_evaluation, "value") else type_evaluation,
            "coefficient": coefficient,
        }
        for intitule, echeance, matiere, type_evaluation, coefficient in lignes
    ]


async def repartition_par_niveau(
    session: AsyncSession, etablissements: set[uuid.UUID]
) -> list[dict[str, object]]:
    """Effectif par niveau dans l'établissement, pour voir où se concentre la charge."""
    if not etablissements:
        return []
    lignes = await session.execute(
        select(Niveau.libelle, func.count(func.distinct(Inscription.apprenant_id)))
        .select_from(Inscription)
        .join(Classe, Classe.id == Inscription.classe_id)
        .join(Niveau, Niveau.id == Classe.niveau_id)
        .where(Inscription.etablissement_id.in_(etablissements))
        .group_by(Niveau.libelle, Niveau.rang)
        .order_by(Niveau.rang)
    )
    return [{"categorie": libelle, "effectif": total} for libelle, total in lignes]


async def moyennes_par_classe(
    session: AsyncSession, etablissements: set[uuid.UUID]
) -> list[dict[str, object]]:
    """Moyenne de chaque classe, pour repérer celles qui décrochent."""
    if not etablissements:
        return []
    lignes = await session.execute(
        select(Classe.libelle, func.avg(Bulletin.moyenne_generale))
        .select_from(Bulletin)
        .join(Classe, Classe.id == Bulletin.classe_id)
        .where(
            Bulletin.etablissement_id.in_(etablissements),
            Bulletin.moyenne_generale.isnot(None),
        )
        .group_by(Classe.libelle)
        .order_by(func.avg(Bulletin.moyenne_generale))
        .limit(15)
    )
    return [{"classe": libelle, "moyenne": round(float(moyenne), 2)} for libelle, moyenne in lignes]


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
