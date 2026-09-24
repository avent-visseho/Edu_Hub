"""Calcul, publication et impression des bulletins de notes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.engines.reporting import BlocTableau, EnTeteDocument, generer_document
from app.models.apprenant import Apprenant
from app.models.etablissement import Etablissement
from app.models.evaluation import (
    Bulletin,
    BulletinMatiere,
    DecisionConseil,
    Evaluation,
    MoyenneMatiere,
    Note,
    StatutNote,
)
from app.models.pedagogie import SyntheseAssiduite
from app.models.scolarite import Classe, Inscription, MatiereNiveau, Periode
from app.utils.calculs import (
    ElementNote,
    calculer_rangs,
    determiner_appreciation,
    determiner_mention,
    ramener_sur_20,
    totaux_ponderes,
)
from app.utils.codes import generer_code_verification, generer_numero_bulletin


def _decision(moyenne: float | None) -> DecisionConseil:
    """Décision proposée au conseil de classe à partir de la moyenne."""
    if moyenne is None:
        return DecisionConseil.AVERTISSEMENT_TRAVAIL
    if moyenne >= 16:
        return DecisionConseil.FELICITATIONS
    if moyenne >= 14:
        return DecisionConseil.ENCOURAGEMENT
    if moyenne >= 10:
        return DecisionConseil.PASSAGE
    if moyenne >= 8:
        return DecisionConseil.AVERTISSEMENT_TRAVAIL
    return DecisionConseil.REDOUBLEMENT


async def _coefficients(session: AsyncSession, classe: Classe) -> dict[uuid.UUID, float]:
    """Coefficients applicables à la classe, selon son niveau et sa série."""
    stmt = select(MatiereNiveau).where(MatiereNiveau.niveau_id == classe.niveau_id)
    if classe.serie_id:
        stmt = stmt.where(
            (MatiereNiveau.serie_id == classe.serie_id) | (MatiereNiveau.serie_id.is_(None))
        )
    return {lien.matiere_id: lien.coefficient for lien in (await session.execute(stmt)).scalars()}


async def calculer_bulletins(
    session: AsyncSession,
    classe_id: uuid.UUID,
    periode_id: uuid.UUID,
    *,
    publier: bool = False,
) -> list[Bulletin]:
    """Recalcule les moyennes, les rangs et les bulletins d'une classe.

    Les bulletins existants pour la période sont remplacés : la fonction est
    idempotente et peut être relancée après une correction de notes.
    """
    classe = await session.get(Classe, classe_id)
    if classe is None:
        raise NotFoundError("Classe introuvable.")
    periode = await session.get(Periode, periode_id)
    if periode is None:
        raise NotFoundError("Période introuvable.")

    # --- Apprenants inscrits dans la classe ---
    stmt = (
        select(Apprenant)
        .join(Inscription, Inscription.apprenant_id == Apprenant.id)
        .where(Inscription.classe_id == classe_id)
        .order_by(Apprenant.nom, Apprenant.prenoms)
    )
    apprenants = list((await session.execute(stmt)).scalars().unique())
    if not apprenants:
        raise BusinessRuleError("Aucun apprenant n'est inscrit dans cette classe.")

    # --- Notes de la période ---
    stmt = (
        select(Note, Evaluation)
        .join(Evaluation, Evaluation.id == Note.evaluation_id)
        .where(Evaluation.classe_id == classe_id, Evaluation.periode_id == periode_id)
    )
    lignes = (await session.execute(stmt)).all()
    if not lignes:
        raise BusinessRuleError(
            "Aucune note n'a été saisie pour cette classe sur la période demandée."
        )

    coefficients = await _coefficients(session, classe)

    # --- Regroupement des notes par apprenant et par matière ---
    brut: dict[tuple[uuid.UUID, uuid.UUID], list[ElementNote]] = {}
    matieres_vues: set[uuid.UUID] = set()
    for note, evaluation in lignes:
        matieres_vues.add(evaluation.matiere_id)
        if note.statut is not StatutNote.SAISIE or note.valeur is None:
            continue
        cle = (note.apprenant_id, evaluation.matiere_id)
        brut.setdefault(cle, []).append(
            ElementNote(ramener_sur_20(note.valeur, evaluation.bareme), evaluation.coefficient)
        )

    # --- Moyennes par matière et rangs ---
    detail: dict[uuid.UUID, list[dict]] = {}
    for matiere_id in matieres_vues:
        valeurs: dict[str, float | None] = {}
        for apprenant in apprenants:
            elements = brut.get((apprenant.id, matiere_id), [])
            points, total_coefficients = totaux_ponderes(elements)
            valeurs[str(apprenant.id)] = (
                round(points / total_coefficients, 2) if total_coefficients else None
            )

        rangs = calculer_rangs(valeurs)
        connues = [v for v in valeurs.values() if v is not None]
        moyenne_classe_matiere = round(sum(connues) / len(connues), 2) if connues else None
        coefficient = coefficients.get(matiere_id, 1.0)

        for apprenant in apprenants:
            valeur = valeurs[str(apprenant.id)]
            detail.setdefault(apprenant.id, []).append(
                {
                    "matiere_id": matiere_id,
                    "moyenne": valeur,
                    "coefficient": coefficient,
                    "rang": rangs.get(str(apprenant.id)),
                    "moyenne_classe": moyenne_classe_matiere,
                    "note_min": min(connues) if connues else None,
                    "note_max": max(connues) if connues else None,
                }
            )

    # --- Remplacement des moyennes matière existantes ---
    await session.execute(
        delete(MoyenneMatiere).where(
            MoyenneMatiere.classe_id == classe_id, MoyenneMatiere.periode_id == periode_id
        )
    )
    for apprenant_id, matieres in detail.items():
        for ligne in matieres:
            session.add(
                MoyenneMatiere(
                    apprenant_id=apprenant_id,
                    classe_id=classe_id,
                    matiere_id=ligne["matiere_id"],
                    periode_id=periode_id,
                    moyenne=ligne["moyenne"],
                    coefficient=ligne["coefficient"],
                    rang=ligne["rang"],
                    moyenne_classe=ligne["moyenne_classe"],
                    note_min_classe=ligne["note_min"],
                    note_max_classe=ligne["note_max"],
                    appreciation=determiner_appreciation(ligne["moyenne"]),
                )
            )

    # --- Moyennes générales et rangs ---
    moyennes_generales: dict[str, float | None] = {}
    totaux: dict[uuid.UUID, tuple[float, float]] = {}
    for apprenant in apprenants:
        elements = [
            ElementNote(ligne["moyenne"], ligne["coefficient"])
            for ligne in detail.get(apprenant.id, [])
            if ligne["moyenne"] is not None
        ]
        points, coefficient_total = totaux_ponderes(elements)
        totaux[apprenant.id] = (points, coefficient_total)
        moyennes_generales[str(apprenant.id)] = (
            round(points / coefficient_total, 2) if coefficient_total else None
        )

    rangs = calculer_rangs(moyennes_generales)
    connues = [v for v in moyennes_generales.values() if v is not None]
    moyenne_classe = round(sum(connues) / len(connues), 2) if connues else None

    classe.moyenne_classe = moyenne_classe

    # --- Assiduité ---
    stmt = select(SyntheseAssiduite).where(
        SyntheseAssiduite.classe_id == classe_id,
        SyntheseAssiduite.periode_id == periode_id,
    )
    assiduite = {
        synthese.apprenant_id: synthese for synthese in (await session.execute(stmt)).scalars()
    }

    # --- Écriture des bulletins ---
    await session.execute(
        delete(Bulletin).where(Bulletin.classe_id == classe_id, Bulletin.periode_id == periode_id)
    )
    await session.flush()

    etablissement = await session.get(Etablissement, classe.etablissement_id)
    sequence_depart = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Bulletin)
                .where(Bulletin.etablissement_id == classe.etablissement_id)
            )
        ).scalar_one()
    )
    horodatage = datetime.now(UTC)
    produits: list[Bulletin] = []

    for index, apprenant in enumerate(apprenants, start=1):
        points, coefficient_total = totaux[apprenant.id]
        moyenne = moyennes_generales[str(apprenant.id)]
        synthese = assiduite.get(apprenant.id)

        bulletin = Bulletin(
            numero=generer_numero_bulletin(
                str(classe.annee_id)[:8],
                (etablissement.code if etablissement else "ETAB")[:16],
                sequence_depart + index,
            ),
            apprenant_id=apprenant.id,
            classe_id=classe_id,
            periode_id=periode_id,
            etablissement_id=classe.etablissement_id,
            moyenne_generale=moyenne,
            total_points=points,
            total_coefficients=coefficient_total,
            rang=rangs.get(str(apprenant.id)),
            effectif_classe=len(apprenants),
            moyenne_classe=moyenne_classe,
            moyenne_premier=max(connues) if connues else None,
            moyenne_dernier=min(connues) if connues else None,
            absences_heures=(synthese.absences_injustifiees * 2) if synthese else 0,
            absences_justifiees=(synthese.absences_justifiees * 2) if synthese else 0,
            retards=synthese.retards if synthese else 0,
            appreciation_generale=determiner_appreciation(moyenne),
            decision=_decision(moyenne),
            mention=determiner_mention(moyenne),
            publie=publier,
            publie_le=horodatage if publier else None,
            code_verification=generer_code_verification(),
        )
        session.add(bulletin)
        await session.flush()

        for ordre, ligne in enumerate(
            sorted(detail.get(apprenant.id, []), key=lambda item: str(item["matiere_id"]))
        ):
            session.add(
                BulletinMatiere(
                    bulletin_id=bulletin.id,
                    matiere_id=ligne["matiere_id"],
                    moyenne=ligne["moyenne"],
                    coefficient=ligne["coefficient"],
                    points=None
                    if ligne["moyenne"] is None
                    else round(ligne["moyenne"] * ligne["coefficient"], 2),
                    rang=ligne["rang"],
                    moyenne_classe=ligne["moyenne_classe"],
                    note_min=ligne["note_min"],
                    note_max=ligne["note_max"],
                    appreciation=determiner_appreciation(ligne["moyenne"]),
                    ordre=ordre,
                )
            )
        produits.append(bulletin)

    await session.flush()
    return produits


async def charger_bulletin_complet(session: AsyncSession, bulletin_id: uuid.UUID):
    """Charge un bulletin avec tout ce qu'il faut pour l'afficher ou l'imprimer."""
    stmt = (
        select(Bulletin)
        .where(Bulletin.id == bulletin_id)
        .options(
            selectinload(Bulletin.apprenant),
            selectinload(Bulletin.classe).selectinload(Classe.etablissement),
            selectinload(Bulletin.classe).selectinload(Classe.annee),
            selectinload(Bulletin.periode),
            selectinload(Bulletin.lignes).selectinload(BulletinMatiere.matiere),
        )
    )
    bulletin = (await session.execute(stmt)).scalar_one_or_none()
    if bulletin is None:
        raise NotFoundError("Bulletin introuvable.")
    return bulletin


def _format_note(valeur: float | None) -> str:
    return "—" if valeur is None else f"{valeur:.2f}".replace(".", ",")


async def generer_pdf(session: AsyncSession, bulletin_id: uuid.UUID) -> tuple[Bulletin, bytes]:
    """Produit le PDF imprimable d'un bulletin, avec son QR code de vérification."""
    bulletin = await charger_bulletin_complet(session, bulletin_id)
    apprenant = bulletin.apprenant
    classe = bulletin.classe
    etablissement = classe.etablissement if classe else None

    entete = EnTeteDocument(
        ministere="Ministère en charge de l'éducation",
        etablissement=etablissement.nom if etablissement else "",
        titre="Bulletin de notes",
        sous_titre=(
            f"{bulletin.periode.libelle} — année {classe.annee.code}"
            if bulletin.periode and classe and classe.annee
            else ""
        ),
    )

    identite = {
        "Apprenant": apprenant.nom_complet if apprenant else "—",
        "Identifiant éducatif": apprenant.identifiant_educatif if apprenant else "—",
        "Date de naissance": apprenant.date_naissance.strftime("%d/%m/%Y") if apprenant else "—",
        "Classe": classe.libelle if classe else "—",
        "Effectif": str(bulletin.effectif_classe or "—"),
        "Numéro du bulletin": bulletin.numero,
    }

    lignes = sorted(bulletin.lignes, key=lambda ligne: ligne.ordre)
    tableau = BlocTableau(
        entetes=["Matière", "Moyenne", "Coef.", "Points", "Rang", "Moy. classe", "Appréciation"],
        lignes=[
            [
                ligne.matiere.libelle if ligne.matiere else "—",
                _format_note(ligne.moyenne),
                f"{ligne.coefficient:g}",
                _format_note(ligne.points),
                str(ligne.rang or "—"),
                _format_note(ligne.moyenne_classe),
                ligne.appreciation or "—",
            ]
            for ligne in lignes
        ],
        alignements={1: "center", 2: "center", 3: "center", 4: "center", 5: "center"},
    )

    synthese = {
        "Moyenne générale": f"{_format_note(bulletin.moyenne_generale)} / 20",
        "Rang": f"{bulletin.rang or '—'} / {bulletin.effectif_classe or '—'}",
        "Moyenne de la classe": _format_note(bulletin.moyenne_classe),
        "Meilleure moyenne": _format_note(bulletin.moyenne_premier),
        "Moyenne la plus basse": _format_note(bulletin.moyenne_dernier),
        "Mention": bulletin.mention or "—",
        "Absences": f"{bulletin.absences_heures} h dont "
        f"{bulletin.absences_justifiees} h justifiées",
        "Retards": str(bulletin.retards),
        "Appréciation générale": bulletin.appreciation_generale or "—",
        "Décision": bulletin.decision.value if bulletin.decision else "—",
    }

    contenu = generer_document(
        entete,
        [identite, tableau, synthese],
        code_verification=bulletin.code_verification,
        pied_de_page=(
            "Bulletin produit par la plateforme EduHub. "
            "Son authenticité est vérifiable en ligne à l'aide du code ci-dessus."
        ),
    )
    return bulletin, contenu
