"""Étape 6 — Évaluations, notes, moyennes, bulletins et conseils de classe."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.models.evaluation import (
    Bulletin,
    BulletinMatiere,
    ConseilClasse,
    DecisionConseil,
    DecisionConseilApprenant,
    Evaluation,
    MoyenneMatiere,
    Note,
    StatutEvaluation,
    StatutNote,
    TypeEvaluation,
)
from app.seed.contexte import ContexteSeed, logger
from app.utils.calculs import (
    ElementNote,
    calculer_rangs,
    determiner_appreciation,
    determiner_mention,
    ecart_type,
    moyenne_ponderee,
    taux,
    totaux_ponderes,
)
from app.utils.codes import generer_code_verification, generer_numero_bulletin

#: Nombre d'évaluations par matière et par période.
EVALUATIONS_PAR_MATIERE = 2

#: Types d'évaluation utilisés et leur poids.
TYPES = (TypeEvaluation.DEVOIR, TypeEvaluation.INTERROGATION, TypeEvaluation.CONTROLE_CONTINU)


async def generer(ctx: ContexteSeed) -> None:
    """Génère les évaluations du premier trimestre, puis les bulletins associés."""
    code_annee = ctx.recuperer("annee_code", "courante")
    periodes = ctx.cache("periodes_par_annee")[code_annee]
    code_periode, id_periode = periodes[0]

    evaluations, notes = [], []
    moyennes_matiere, bulletins, lignes_bulletin = [], [], []
    conseils, decisions = [], []

    debut_periode = date(int(code_annee.split("-")[0]), 10, 1)
    horodatage = datetime.now(UTC)
    numero_bulletin = 0

    for code_classe, info in ctx.cache("classe_info").items():
        matieres = info["matieres"]
        membres = info["apprenants"]
        if not matieres or not membres:
            continue

        # --- Niveau moyen propre à chaque apprenant, pour des notes cohérentes ---
        aptitudes = {m["id"]: ctx.rng.gauss(11.2, 2.6) for m in membres}
        # --- Niveau moyen propre à l'établissement ---
        biais_etablissement = ctx.rng.gauss(0, 1.1)

        notes_par_apprenant_matiere: dict[tuple, list[ElementNote]] = {}

        for code_matiere, _ in matieres:
            enseignant = next(
                (e for e in info["enseignants"] if code_matiere in e["matieres"]), None
            )
            difficulte = ctx.rng.gauss(0, 0.9)

            for numero in range(1, EVALUATIONS_PAR_MATIERE + 1):
                id_evaluation = ctx.nouvel_id()
                date_evaluation = debut_periode + timedelta(days=ctx.entier(5, 70))
                valeurs: list[float] = []

                for membre in membres:
                    if ctx.probabilite(0.03):
                        statut = ctx.choix(
                            [StatutNote.ABSENT, StatutNote.ABSENT_JUSTIFIE, StatutNote.NON_RENDU]
                        )
                        valeur = None
                    else:
                        statut = StatutNote.SAISIE
                        brut = (
                            aptitudes[membre["id"]]
                            + biais_etablissement
                            - difficulte
                            + ctx.rng.gauss(0, 1.8)
                        )
                        valeur = round(max(0.0, min(20.0, brut)) * 4) / 4
                        valeurs.append(valeur)
                        notes_par_apprenant_matiere.setdefault(
                            (membre["id"], code_matiere), []
                        ).append(ElementNote(valeur, 1.0))

                    notes.append(
                        {
                            "id": ctx.nouvel_id(),
                            "evaluation_id": id_evaluation,
                            "apprenant_id": membre["id"],
                            "valeur": valeur,
                            "statut": statut,
                            "appreciation": determiner_appreciation(valeur),
                            "modifiee": False,
                        }
                    )

                evaluations.append(
                    {
                        "id": id_evaluation,
                        "classe_id": info["id"],
                        "matiere_id": ctx.recuperer("matiere", code_matiere),
                        "periode_id": id_periode,
                        "enseignant_id": enseignant["id"] if enseignant else None,
                        "code": f"{code_classe}-{code_matiere}-{code_periode}-{numero}",
                        "intitule": f"{'Devoir' if numero == 1 else 'Interrogation'} n°{numero}",
                        "type_evaluation": TYPES[numero % len(TYPES)],
                        "date_evaluation": date_evaluation,
                        "bareme": 20.0,
                        "coefficient": 1.0,
                        "duree_minutes": ctx.choix([60, 90, 120]),
                        "statut": StatutEvaluation.PUBLIEE,
                        "moyenne": moyenne_ponderee([ElementNote(v, 1.0) for v in valeurs]),
                        "note_min": min(valeurs) if valeurs else None,
                        "note_max": max(valeurs) if valeurs else None,
                        "ecart_type": ecart_type(valeurs),
                        "nombre_notes": len(valeurs),
                        "valide_enseignant_le": horodatage,
                        "valide_etablissement_le": horodatage,
                        "publiee_le": horodatage,
                    }
                )

        # --- Moyennes par matière, rangs et bulletins ---
        moyennes_generales: dict[str, float | None] = {}
        detail_par_apprenant: dict[str, list[dict]] = {}

        for code_matiere, coefficient in matieres:
            valeurs_matiere = {
                membre["id"]: moyenne_ponderee(
                    notes_par_apprenant_matiere.get((membre["id"], code_matiere), [])
                )
                for membre in membres
            }
            rangs_matiere = calculer_rangs(valeurs_matiere)
            connues = [v for v in valeurs_matiere.values() if v is not None]
            moyenne_classe_matiere = moyenne_ponderee([ElementNote(v, 1.0) for v in connues])

            for membre in membres:
                valeur = valeurs_matiere[membre["id"]]
                moyennes_matiere.append(
                    {
                        "id": ctx.nouvel_id(),
                        "apprenant_id": membre["id"],
                        "classe_id": info["id"],
                        "matiere_id": ctx.recuperer("matiere", code_matiere),
                        "periode_id": id_periode,
                        "moyenne": valeur,
                        "coefficient": float(coefficient),
                        "rang": rangs_matiere.get(membre["id"]),
                        "moyenne_classe": moyenne_classe_matiere,
                        "note_min_classe": min(connues) if connues else None,
                        "note_max_classe": max(connues) if connues else None,
                        "appreciation": determiner_appreciation(valeur),
                    }
                )
                detail_par_apprenant.setdefault(membre["id"], []).append(
                    {
                        "matiere": code_matiere,
                        "moyenne": valeur,
                        "coefficient": float(coefficient),
                        "rang": rangs_matiere.get(membre["id"]),
                        "moyenne_classe": moyenne_classe_matiere,
                        "note_min": min(connues) if connues else None,
                        "note_max": max(connues) if connues else None,
                    }
                )

        for membre in membres:
            elements = [
                ElementNote(ligne["moyenne"], ligne["coefficient"])
                for ligne in detail_par_apprenant.get(membre["id"], [])
                if ligne["moyenne"] is not None
            ]
            moyennes_generales[membre["id"]] = moyenne_ponderee(elements)

        rangs = calculer_rangs(moyennes_generales)
        connues = [v for v in moyennes_generales.values() if v is not None]
        moyenne_classe = moyenne_ponderee([ElementNote(v, 1.0) for v in connues])
        meilleure = max(connues) if connues else None
        derniere = min(connues) if connues else None

        id_conseil = ctx.nouvel_id()
        conseils.append(
            {
                "id": id_conseil,
                "classe_id": info["id"],
                "periode_id": id_periode,
                "date_conseil": debut_periode + timedelta(days=85),
                "president_nom": "Le chef d'établissement",
                "participants": "Professeur principal, enseignants, représentants des parents",
                "moyenne_classe": moyenne_classe,
                "taux_reussite": taux(sum(1 for v in connues if v >= 10), len(connues) or 1),
                "cloture": True,
            }
        )

        for membre in membres:
            numero_bulletin += 1
            moyenne = moyennes_generales[membre["id"]]
            lignes = detail_par_apprenant.get(membre["id"], [])
            points, coefficients = totaux_ponderes(
                [
                    ElementNote(ligne["moyenne"], ligne["coefficient"])
                    for ligne in lignes
                    if ligne["moyenne"] is not None
                ]
            )
            assiduite = membre.get("assiduite", {})
            id_bulletin = ctx.nouvel_id()

            decision = _decision(moyenne)
            bulletins.append(
                {
                    "id": id_bulletin,
                    "numero": generer_numero_bulletin(
                        code_annee, info["etablissement"][:16], numero_bulletin
                    ),
                    "apprenant_id": membre["id"],
                    "classe_id": info["id"],
                    "periode_id": id_periode,
                    "etablissement_id": info["etablissement_id"],
                    "moyenne_generale": moyenne,
                    "total_points": points,
                    "total_coefficients": coefficients,
                    "rang": rangs.get(membre["id"]),
                    "effectif_classe": len(membres),
                    "moyenne_classe": moyenne_classe,
                    "moyenne_premier": meilleure,
                    "moyenne_dernier": derniere,
                    "absences_heures": assiduite.get("injustifiee", 0) * 2,
                    "absences_justifiees": assiduite.get("justifiee", 0) * 2,
                    "retards": assiduite.get("retard", 0),
                    "appreciation_generale": determiner_appreciation(moyenne),
                    "appreciation_conduite": ctx.choix(
                        ["Bonne conduite", "Conduite satisfaisante", "Élève discipliné"]
                    ),
                    "decision": decision,
                    "mention": determiner_mention(moyenne),
                    "publie": True,
                    "publie_le": horodatage,
                    "code_verification": generer_code_verification(),
                }
            )

            for rang_ligne, ligne in enumerate(lignes):
                lignes_bulletin.append(
                    {
                        "id": ctx.nouvel_id(),
                        "bulletin_id": id_bulletin,
                        "matiere_id": ctx.recuperer("matiere", ligne["matiere"]),
                        "moyenne": ligne["moyenne"],
                        "coefficient": ligne["coefficient"],
                        "points": None
                        if ligne["moyenne"] is None
                        else round(ligne["moyenne"] * ligne["coefficient"], 2),
                        "rang": ligne["rang"],
                        "moyenne_classe": ligne["moyenne_classe"],
                        "note_min": ligne["note_min"],
                        "note_max": ligne["note_max"],
                        "appreciation": determiner_appreciation(ligne["moyenne"]),
                        "ordre": rang_ligne,
                    }
                )

            decisions.append(
                {
                    "id": ctx.nouvel_id(),
                    "conseil_id": id_conseil,
                    "apprenant_id": membre["id"],
                    "decision": decision,
                    "motivation": determiner_appreciation(moyenne),
                }
            )

            membre["moyenne_generale"] = moyenne

    await ctx.inserer(Evaluation, evaluations)
    await ctx.inserer(Note, notes)
    await ctx.inserer(MoyenneMatiere, moyennes_matiere)
    await ctx.inserer(Bulletin, bulletins)
    await ctx.inserer(BulletinMatiere, lignes_bulletin)
    await ctx.inserer(ConseilClasse, conseils)
    await ctx.inserer(DecisionConseilApprenant, decisions)

    logger.info("%d bulletins générés à partir de %d notes.", len(bulletins), len(notes))


def _decision(moyenne: float | None) -> DecisionConseil:
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
