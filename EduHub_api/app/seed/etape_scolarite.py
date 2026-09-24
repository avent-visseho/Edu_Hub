"""Étape 5 — Classes, inscriptions, emploi du temps et assiduité."""

from __future__ import annotations

from datetime import date, time, timedelta

from app.models.pedagogie import (
    CreneauEmploiDuTemps,
    JourSemaine,
    Presence,
    Seance,
    StatutPresence,
    StatutSeance,
    SyntheseAssiduite,
)
from app.models.scolarite import (
    Classe,
    DecisionFinAnnee,
    Inscription,
    RegimeScolarite,
    StatutInscription,
)
from app.seed import scolaire
from app.seed.contexte import ContexteSeed, logger
from app.seed.etape_etablissements import niveaux_du_type
from app.utils.calculs import taux

#: Créneaux horaires d'une journée type.
HORAIRES: tuple[tuple[time, time], ...] = (
    (time(7, 30), time(9, 30)),
    (time(9, 45), time(11, 45)),
    (time(12, 0), time(13, 0)),
    (time(15, 0), time(17, 0)),
)

JOURS_OUVRES: tuple[JourSemaine, ...] = (
    JourSemaine.LUNDI,
    JourSemaine.MARDI,
    JourSemaine.MERCREDI,
    JourSemaine.JEUDI,
    JourSemaine.VENDREDI,
)

#: Nombre de séances effectivement historisées par classe, pour l'assiduité.
SEANCES_SUIVIES = 6


async def generer(ctx: ContexteSeed) -> None:
    await _classes_et_inscriptions(ctx)
    await _emploi_du_temps(ctx)
    await _assiduite(ctx)
    logger.info("%d classes générées avec leurs inscriptions.", len(ctx.cache("classe_info")))


# ------------------------------------------------------------------


def _matieres_de_la_classe(code_niveau: str, code_serie: str | None) -> list[tuple[str, float]]:
    """Matières et coefficients applicables à une classe."""
    if code_serie:
        return list(scolaire.PROGRAMME_PAR_SERIE.get(code_serie, ()))
    cycle = next(
        (cycle for code, _, cycle, _ in scolaire.NIVEAUX if code == code_niveau), "PRIMAIRE"
    )
    matieres = scolaire.PROGRAMME_PAR_NIVEAU.get(cycle, ())
    coefficients = {code: coef for code, _, _, _, coef, _ in scolaire.MATIERES}
    return [(code, coefficients[code]) for code in matieres]


async def _classes_et_inscriptions(ctx: ContexteSeed) -> None:
    code_annee = ctx.recuperer("annee_code", "courante")
    id_annee = ctx.recuperer("annee", "courante")

    classes, inscriptions = [], []
    numero_inscription = 0

    for code_etablissement, info in ctx.cache("etablissement_info").items():
        apprenants = ctx.cache("apprenants_par_etablissement").get(code_etablissement, [])
        if not apprenants:
            continue

        niveaux = niveaux_du_type(info["type"])
        if not niveaux:
            continue

        enseignants = ctx.cache("enseignants_par_etablissement").get(code_etablissement, [])
        salles = ctx.cache("salles_de_classe").get(code_etablissement, [])

        # Constitution des classes : chaque niveau reçoit une ou plusieurs divisions.
        divisions: list[tuple[str, str | None, str]] = []
        for code_niveau in niveaux:
            series = (
                scolaire.SERIES_GENERALES
                if code_niveau in scolaire.NIVEAUX_SECOND_CYCLE and info["type"] != "LT"
                else (None,)
            )
            if info["type"] == "LT" and code_niveau in scolaire.NIVEAUX_SECOND_CYCLE:
                series = ("F1", "F2", "F3", "G1", "G2")
            for code_serie in series:
                if code_serie and not ctx.probabilite(0.55):
                    continue
                suffixe = "ABCD"[ctx.entier(0, 1)]
                divisions.append((code_niveau, code_serie, suffixe))

        if not divisions:
            continue

        # Répartition des apprenants entre les divisions.
        ctx.rng.shuffle(apprenants)
        par_division = max(1, len(apprenants) // len(divisions))

        for rang, (code_niveau, code_serie, suffixe) in enumerate(divisions):
            debut = rang * par_division
            membres = apprenants[debut : debut + par_division]
            if rang == len(divisions) - 1:
                membres = apprenants[debut:]
            if not membres:
                continue

            code_classe = f"{code_etablissement}-{code_niveau}{code_serie or ''}{suffixe}"
            id_classe = ctx.nouvel_id()
            professeur = ctx.choix(enseignants) if enseignants else None

            libelle = f"{_libelle_niveau(code_niveau)} {code_serie or ''}{suffixe}".strip()
            classes.append(
                {
                    "id": id_classe,
                    "etablissement_id": info["id"],
                    "annee_id": id_annee,
                    "niveau_id": ctx.recuperer("niveau", code_niveau),
                    "serie_id": ctx.recuperer("serie", code_serie) if code_serie else None,
                    "filiere_id": None,
                    "salle_id": ctx.choix(salles) if salles else None,
                    "professeur_principal_id": professeur["id"] if professeur else None,
                    "code": code_classe,
                    "libelle": libelle,
                    "effectif_max": 60,
                    "effectif": len(membres),
                }
            )

            ctx.cache("classe_info")[code_classe] = {
                "id": id_classe,
                "etablissement": code_etablissement,
                "etablissement_id": info["id"],
                "niveau": code_niveau,
                "serie": code_serie,
                "libelle": libelle,
                "apprenants": membres,
                "matieres": _matieres_de_la_classe(code_niveau, code_serie),
                "enseignants": enseignants,
                "salle_id": ctx.choix(salles) if salles else None,
            }
            ctx.cache("classes_par_niveau").setdefault(code_niveau, []).append(code_classe)

            for membre in membres:
                numero_inscription += 1
                inscriptions.append(
                    {
                        "id": ctx.nouvel_id(),
                        "apprenant_id": membre["id"],
                        "etablissement_id": info["id"],
                        "annee_id": id_annee,
                        "classe_id": id_classe,
                        "numero": f"INS-{code_annee}-{numero_inscription:07d}",
                        "statut": StatutInscription.INSCRIT,
                        "regime": ctx.rng.choices(list(RegimeScolarite), weights=[78, 14, 8])[0],
                        "redoublant": ctx.probabilite(0.11),
                        "boursier": ctx.probabilite(0.07),
                        "date_demande": date(int(code_annee.split("-")[0]), 9, 1),
                        "date_validation": date(int(code_annee.split("-")[0]), 9, 20),
                        "frais_scolarite": float(ctx.entier(0, 120_000)),
                        "montant_paye": 0.0,
                        "decision": DecisionFinAnnee.EN_ATTENTE,
                    }
                )

    await ctx.inserer(Classe, classes)
    await ctx.inserer(Inscription, inscriptions)


async def _emploi_du_temps(ctx: ContexteSeed) -> None:
    """Emploi du temps hebdomadaire, sans conflit d'enseignant ni de salle."""
    creneaux = []

    for info in ctx.cache("classe_info").values():
        matieres = info["matieres"]
        if not matieres:
            continue
        enseignants = info["enseignants"]
        occupation_enseignant: dict[tuple, set] = {}

        rang = 0
        for jour in JOURS_OUVRES:
            for heure_debut, heure_fin in HORAIRES[:3]:
                code_matiere = matieres[rang % len(matieres)][0]
                rang += 1

                # On privilégie un enseignant habilité, disponible sur ce créneau.
                candidats = [
                    e
                    for e in enseignants
                    if code_matiere in e["matieres"]
                    and (jour, heure_debut) not in occupation_enseignant.get(e["id"], set())
                ]
                enseignant = ctx.choix(candidats) if candidats else None
                if enseignant:
                    occupation_enseignant.setdefault(enseignant["id"], set()).add(
                        (jour, heure_debut)
                    )

                id_creneau = ctx.nouvel_id()
                creneaux.append(
                    {
                        "id": id_creneau,
                        "classe_id": info["id"],
                        "matiere_id": ctx.recuperer("matiere", code_matiere),
                        "enseignant_id": enseignant["id"] if enseignant else None,
                        "salle_id": info["salle_id"],
                        "jour": jour,
                        "heure_debut": heure_debut,
                        "heure_fin": heure_fin,
                    }
                )
                info.setdefault("creneaux", []).append(
                    {
                        "id": id_creneau,
                        "matiere": code_matiere,
                        "enseignant_id": enseignant["id"] if enseignant else None,
                        "jour": jour,
                        "heure_debut": heure_debut,
                        "heure_fin": heure_fin,
                    }
                )

    await ctx.inserer(CreneauEmploiDuTemps, creneaux)


async def _assiduite(ctx: ContexteSeed) -> None:
    """Séances tenues, appels effectués et synthèses d'assiduité."""
    code_annee = ctx.recuperer("annee_code", "courante")
    periodes = ctx.cache("periodes_par_annee")[code_annee]
    code_periode, id_periode = periodes[0]

    seances, presences, syntheses = [], [], []
    reference = date(int(code_annee.split("-")[0]), 10, 6)

    poids_presence = [88, 4, 4, 2, 2, 0]
    statuts = list(StatutPresence)

    for info in ctx.cache("classe_info").values():
        creneaux = info.get("creneaux") or []
        if not creneaux:
            continue

        compteurs: dict = {
            membre["id"]: {"present": 0, "justifiee": 0, "injustifiee": 0, "retard": 0}
            for membre in info["apprenants"]
        }

        for numero, creneau in enumerate(ctx.echantillon(creneaux, SEANCES_SUIVIES)):
            date_seance = reference + timedelta(days=numero * 7)
            id_seance = ctx.nouvel_id()
            seances.append(
                {
                    "id": id_seance,
                    "creneau_id": creneau["id"],
                    "classe_id": info["id"],
                    "matiere_id": ctx.recuperer("matiere", creneau["matiere"]),
                    "enseignant_id": creneau["enseignant_id"],
                    "salle_id": info["salle_id"],
                    "periode_id": id_periode,
                    "date_seance": date_seance,
                    "heure_debut": creneau["heure_debut"],
                    "heure_fin": creneau["heure_fin"],
                    "statut": StatutSeance.TENUE,
                    "contenu_seance": "Séance conforme à la progression annuelle.",
                    "appel_fait": True,
                }
            )

            for membre in info["apprenants"]:
                statut = ctx.rng.choices(statuts, weights=poids_presence)[0]
                compteur = compteurs[membre["id"]]
                if statut is StatutPresence.PRESENT:
                    compteur["present"] += 1
                elif statut is StatutPresence.RETARD:
                    compteur["present"] += 1
                    compteur["retard"] += 1
                elif statut is StatutPresence.ABSENCE_JUSTIFIEE:
                    compteur["justifiee"] += 1
                elif statut is StatutPresence.ABSENT:
                    compteur["injustifiee"] += 1
                else:
                    compteur["injustifiee"] += 1

                presences.append(
                    {
                        "id": ctx.nouvel_id(),
                        "seance_id": id_seance,
                        "apprenant_id": membre["id"],
                        "statut": statut,
                        "minutes_retard": ctx.entier(5, 45)
                        if statut is StatutPresence.RETARD
                        else 0,
                        "justification": "Certificat médical"
                        if statut is StatutPresence.ABSENCE_JUSTIFIEE
                        else None,
                    }
                )

        total = min(SEANCES_SUIVIES, len(creneaux))
        for membre in info["apprenants"]:
            compteur = compteurs[membre["id"]]
            syntheses.append(
                {
                    "id": ctx.nouvel_id(),
                    "apprenant_id": membre["id"],
                    "classe_id": info["id"],
                    "periode_id": id_periode,
                    "seances_totales": total,
                    "presences": compteur["present"],
                    "absences_justifiees": compteur["justifiee"],
                    "absences_injustifiees": compteur["injustifiee"],
                    "retards": compteur["retard"],
                    "taux_presence": taux(compteur["present"], total),
                }
            )
            membre["assiduite"] = compteur

    ctx.enregistrer("periode_assiduite", code_periode, id_periode)

    await ctx.inserer(Seance, seances)
    await ctx.inserer(Presence, presences)
    await ctx.inserer(SyntheseAssiduite, syntheses)


def _libelle_niveau(code: str) -> str:
    for code_niveau, libelle, _, _ in scolaire.NIVEAUX:
        if code_niveau == code:
            return libelle
    return code
