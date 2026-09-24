"""Moteur analytique — indicateurs, agrégations et détection d'alertes."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.apprenant import Apprenant
from app.models.etablissement import Etablissement, Salle
from app.models.evaluation import Bulletin
from app.models.examen import Candidat, DecisionExamen, ResultatExamen, SessionExamen
from app.models.personnel import Enseignant
from app.models.referentiel import Commune, Departement
from app.models.scolarite import Classe, Inscription, StatutInscription
from app.utils.calculs import taux


@dataclass(slots=True)
class Indicateur:
    """Indicateur affichable sur un tableau de bord."""

    code: str
    libelle: str
    valeur: float
    unite: str | None = None
    variation: float | None = None
    detail: dict[str, Any] | None = None

    def en_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "libelle": self.libelle,
            "valeur": self.valeur,
            "unite": self.unite,
            "variation": self.variation,
            "detail": self.detail,
        }


async def _compter(session: AsyncSession, statement: Select) -> int:
    stmt = select(func.count()).select_from(statement.order_by(None).subquery())
    return int((await session.execute(stmt)).scalar_one())


# ------------------------------------------------------------------
#  Tableau de bord national
# ------------------------------------------------------------------


async def tableau_bord_national(
    session: AsyncSession, annee_id: uuid.UUID | None = None
) -> list[Indicateur]:
    """Chiffres clés du système éducatif à l'échelle nationale."""
    apprenants = await _compter(session, select(Apprenant).where(Apprenant.supprime.is_(False)))
    enseignants = await _compter(session, select(Enseignant).where(Enseignant.supprime.is_(False)))
    etablissements = await _compter(
        session, select(Etablissement).where(Etablissement.supprime.is_(False))
    )

    classes_stmt = select(Classe)
    if annee_id:
        classes_stmt = classes_stmt.where(Classe.annee_id == annee_id)
    classes = await _compter(session, classes_stmt)

    salles = await _compter(session, select(Salle))
    sessions = await _compter(session, select(SessionExamen))
    candidats = await _compter(session, select(Candidat))

    filles = await _compter(
        session,
        select(Apprenant).where(Apprenant.supprime.is_(False), Apprenant.sexe == "FEMININ"),
    )

    admis = await _compter(
        session, select(ResultatExamen).where(ResultatExamen.decision == DecisionExamen.ADMIS)
    )
    resultats = await _compter(session, select(ResultatExamen))

    ratio_eleves_enseignant = round(apprenants / enseignants, 1) if enseignants else 0.0

    return [
        Indicateur("apprenants", "Apprenants", apprenants),
        Indicateur("enseignants", "Enseignants", enseignants),
        Indicateur("etablissements", "Établissements", etablissements),
        Indicateur("classes", "Classes", classes),
        Indicateur("salles", "Salles", salles),
        Indicateur("sessions_examen", "Sessions d'examen", sessions),
        Indicateur("candidats", "Candidats", candidats),
        Indicateur("taux_filles", "Part des filles", taux(filles, apprenants), "%"),
        Indicateur("taux_reussite", "Taux de réussite", taux(admis, resultats), "%"),
        Indicateur(
            "ratio_eleves_enseignant",
            "Élèves par enseignant",
            ratio_eleves_enseignant,
            "élèves",
        ),
    ]


# ------------------------------------------------------------------
#  Agrégations territoriales
# ------------------------------------------------------------------


async def effectifs_par_departement(
    session: AsyncSession, annee_id: uuid.UUID | None = None
) -> list[dict[str, Any]]:
    """Répartition des effectifs et des établissements par département."""
    stmt = (
        select(
            Departement.code,
            Departement.libelle,
            func.count(func.distinct(Etablissement.id)).label("etablissements"),
            func.count(func.distinct(Inscription.id)).label("inscriptions"),
        )
        .select_from(Departement)
        .outerjoin(Commune, Commune.departement_id == Departement.id)
        .outerjoin(Etablissement, Etablissement.commune_id == Commune.id)
        .outerjoin(Inscription, Inscription.etablissement_id == Etablissement.id)
        .group_by(Departement.code, Departement.libelle)
        .order_by(Departement.libelle)
    )
    if annee_id:
        stmt = stmt.where(Inscription.annee_id == annee_id)

    return [
        {
            "code": code,
            "departement": libelle,
            "etablissements": etablissements,
            "apprenants": inscriptions,
        }
        for code, libelle, etablissements, inscriptions in (await session.execute(stmt)).all()
    ]


async def resultats_par_etablissement(
    session: AsyncSession, session_examen_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Palmarès des établissements pour une session d'examen."""
    stmt = (
        select(
            Etablissement.id,
            Etablissement.code,
            Etablissement.nom,
            func.count(ResultatExamen.id).label("candidats"),
            func.count(ResultatExamen.id)
            .filter(ResultatExamen.decision == DecisionExamen.ADMIS)
            .label("admis"),
            func.avg(ResultatExamen.moyenne).label("moyenne"),
            func.max(ResultatExamen.moyenne).label("meilleure_moyenne"),
        )
        .select_from(ResultatExamen)
        .join(Etablissement, Etablissement.id == ResultatExamen.etablissement_id)
        .where(ResultatExamen.session_id == session_examen_id)
        .group_by(Etablissement.id, Etablissement.code, Etablissement.nom)
        .order_by(func.avg(ResultatExamen.moyenne).desc().nullslast())
    )

    lignes = []
    for ident, code, nom, candidats, admis, moyenne, meilleure in (
        await session.execute(stmt)
    ).all():
        lignes.append(
            {
                "etablissement_id": str(ident),
                "code": code,
                "nom": nom,
                "candidats": candidats,
                "admis": admis,
                "non_admis": candidats - admis,
                "taux_reussite": taux(admis, candidats),
                "moyenne": round(float(moyenne), 2) if moyenne is not None else None,
                "meilleure_moyenne": round(float(meilleure), 2) if meilleure is not None else None,
            }
        )
    return lignes


async def resultats_par_departement(
    session: AsyncSession, session_examen_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Synthèse départementale des résultats d'une session."""
    stmt = (
        select(
            Departement.code,
            Departement.libelle,
            func.count(ResultatExamen.id).label("candidats"),
            func.count(ResultatExamen.id)
            .filter(ResultatExamen.decision == DecisionExamen.ADMIS)
            .label("admis"),
            func.avg(ResultatExamen.moyenne).label("moyenne"),
        )
        .select_from(ResultatExamen)
        .join(Departement, Departement.id == ResultatExamen.departement_id)
        .where(ResultatExamen.session_id == session_examen_id)
        .group_by(Departement.code, Departement.libelle)
        .order_by(Departement.libelle)
    )

    return [
        {
            "code": code,
            "departement": libelle,
            "candidats": candidats,
            "admis": admis,
            "non_admis": candidats - admis,
            "taux_reussite": taux(admis, candidats),
            "moyenne": round(float(moyenne), 2) if moyenne is not None else None,
        }
        for code, libelle, candidats, admis, moyenne in (await session.execute(stmt)).all()
    ]


async def statistiques_etablissement(
    session: AsyncSession, etablissement_id: uuid.UUID, annee_id: uuid.UUID | None = None
) -> dict[str, Any]:
    """Indicateurs consolidés d'un établissement."""
    inscriptions_stmt = select(Inscription).where(
        Inscription.etablissement_id == etablissement_id,
        Inscription.statut == StatutInscription.INSCRIT,
    )
    if annee_id:
        inscriptions_stmt = inscriptions_stmt.where(Inscription.annee_id == annee_id)

    effectif = await _compter(session, inscriptions_stmt)

    filles_stmt = (
        select(Inscription)
        .join(Apprenant, Apprenant.id == Inscription.apprenant_id)
        .where(
            Inscription.etablissement_id == etablissement_id,
            Inscription.statut == StatutInscription.INSCRIT,
            Apprenant.sexe == "FEMININ",
        )
    )
    if annee_id:
        filles_stmt = filles_stmt.where(Inscription.annee_id == annee_id)
    filles = await _compter(session, filles_stmt)

    classes_stmt = select(Classe).where(Classe.etablissement_id == etablissement_id)
    if annee_id:
        classes_stmt = classes_stmt.where(Classe.annee_id == annee_id)
    classes = await _compter(session, classes_stmt)

    salles = await _compter(
        session, select(Salle).where(Salle.etablissement_id == etablissement_id)
    )
    enseignants = await _compter(
        session,
        select(Enseignant).where(
            Enseignant.etablissement_principal_id == etablissement_id,
            Enseignant.supprime.is_(False),
        ),
    )

    moyenne_stmt = select(func.avg(Bulletin.moyenne_generale)).where(
        Bulletin.etablissement_id == etablissement_id
    )
    moyenne = (await session.execute(moyenne_stmt)).scalar_one_or_none()

    return {
        "effectif": effectif,
        "filles": filles,
        "garcons": effectif - filles,
        "taux_filles": taux(filles, effectif),
        "classes": classes,
        "salles": salles,
        "enseignants": enseignants,
        "eleves_par_classe": round(effectif / classes, 1) if classes else 0.0,
        "eleves_par_salle": round(effectif / salles, 1) if salles else 0.0,
        "eleves_par_enseignant": round(effectif / enseignants, 1) if enseignants else 0.0,
        "moyenne_etablissement": round(float(moyenne), 2) if moyenne is not None else None,
    }


async def distribution_moyennes(
    session: AsyncSession,
    etablissement_id: uuid.UUID | None = None,
    bornes: Sequence[float] = (0, 5, 8, 10, 12, 14, 16, 18, 20),
) -> list[dict[str, Any]]:
    """Histogramme de répartition des moyennes générales."""
    stmt = select(Bulletin.moyenne_generale).where(Bulletin.moyenne_generale.isnot(None))
    if etablissement_id:
        stmt = stmt.where(Bulletin.etablissement_id == etablissement_id)
    moyennes = [float(v) for v in (await session.execute(stmt)).scalars()]

    tranches = []
    for index in range(len(bornes) - 1):
        borne_min, borne_max = bornes[index], bornes[index + 1]
        effectif = sum(1 for m in moyennes if borne_min <= m < borne_max)
        tranches.append(
            {
                "tranche": f"[{borne_min:g} ; {borne_max:g}[",
                "borne_min": borne_min,
                "borne_max": borne_max,
                "effectif": effectif,
                "pourcentage": taux(effectif, len(moyennes)),
            }
        )
    return tranches
