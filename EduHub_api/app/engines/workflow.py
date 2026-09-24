"""Moteur de workflow — transitions de statut gouvernées par des machines à états.

Un même moteur pilote les candidatures d'examen, les inscriptions, les bourses,
les transferts, les contentieux, les projets et les validations de notes.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import WorkflowError
from app.models.examen import StatutDossier
from app.models.scolarite import StatutInscription
from app.models.systeme import TransitionWorkflow
from app.models.vie_etudiante import StatutCandidatureBourse


@dataclass(frozen=True, slots=True)
class Transition:
    """Transition autorisée d'un statut vers un autre."""

    action: str
    depuis: str
    vers: str
    libelle: str
    roles_autorises: frozenset[str] = field(default_factory=frozenset)


class MachineEtats:
    """Machine à états générique, partagée par tous les workflows."""

    def __init__(self, nom: str, transitions: Iterable[Transition]) -> None:
        self.nom = nom
        self.transitions = list(transitions)
        self._index: dict[tuple[str, str], Transition] = {
            (t.depuis, t.action): t for t in self.transitions
        }

    def transitions_possibles(self, statut: str) -> list[Transition]:
        return [t for t in self.transitions if t.depuis == statut]

    def resoudre(self, statut_actuel: str, action: str) -> Transition:
        transition = self._index.get((statut_actuel, action))
        if transition is None:
            possibles = ", ".join(
                sorted({t.action for t in self.transitions_possibles(statut_actuel)})
            )
            raise WorkflowError(
                f"Action « {action} » impossible depuis le statut « {statut_actuel} ».",
                details={"statut_actuel": statut_actuel, "actions_possibles": possibles},
            )
        return transition

    def peut(self, statut_actuel: str, action: str, roles: set[str] | None = None) -> bool:
        transition = self._index.get((statut_actuel, action))
        if transition is None:
            return False
        if not transition.roles_autorises:
            return True
        return bool(roles and roles & set(transition.roles_autorises))


def _t(action: str, depuis: StrEnum, vers: StrEnum, libelle: str, *roles: str) -> Transition:
    return Transition(action, depuis.value, vers.value, libelle, frozenset(roles))


# ------------------------------------------------------------------
#  Workflow : dossier de candidature à un examen ou un concours
# ------------------------------------------------------------------

WORKFLOW_DOSSIER_EXAMEN = MachineEtats(
    "dossier_examen",
    [
        _t("soumettre", StatutDossier.BROUILLON, StatutDossier.SOUMIS, "Soumettre le dossier"),
        _t("instruire", StatutDossier.SOUMIS, StatutDossier.EN_ETUDE, "Ouvrir l'étude du dossier"),
        _t(
            "declarer_incomplet",
            StatutDossier.EN_ETUDE,
            StatutDossier.INCOMPLET,
            "Déclarer le dossier incomplet",
        ),
        _t("completer", StatutDossier.INCOMPLET, StatutDossier.SOUMIS, "Compléter le dossier"),
        _t("valider", StatutDossier.EN_ETUDE, StatutDossier.VALIDE, "Valider le dossier"),
        _t("rejeter", StatutDossier.EN_ETUDE, StatutDossier.REJETE, "Rejeter le dossier"),
        _t("convoquer", StatutDossier.VALIDE, StatutDossier.CONVOQUE, "Émettre la convocation"),
        _t(
            "marquer_compose",
            StatutDossier.CONVOQUE,
            StatutDossier.COMPOSE,
            "Marquer comme composé",
        ),
        _t("marquer_corrige", StatutDossier.COMPOSE, StatutDossier.CORRIGE, "Copies corrigées"),
        _t("admettre", StatutDossier.CORRIGE, StatutDossier.ADMIS, "Déclarer admis"),
        _t("ajourner", StatutDossier.CORRIGE, StatutDossier.NON_ADMIS, "Déclarer non admis"),
        _t(
            "reviser_admis",
            StatutDossier.NON_ADMIS,
            StatutDossier.ADMIS,
            "Révision après contentieux",
        ),
    ],
)


# ------------------------------------------------------------------
#  Workflow : inscription scolaire
# ------------------------------------------------------------------

WORKFLOW_INSCRIPTION = MachineEtats(
    "inscription",
    [
        _t(
            "deposer_dossier",
            StatutInscription.DEMANDE,
            StatutInscription.DOSSIER_DEPOSE,
            "Déposer le dossier",
        ),
        _t(
            "verifier",
            StatutInscription.DOSSIER_DEPOSE,
            StatutInscription.EN_VERIFICATION,
            "Vérifier les pièces",
        ),
        _t(
            "valider",
            StatutInscription.EN_VERIFICATION,
            StatutInscription.VALIDEE,
            "Valider l'inscription",
        ),
        _t(
            "rejeter",
            StatutInscription.EN_VERIFICATION,
            StatutInscription.REJETEE,
            "Rejeter l'inscription",
        ),
        _t(
            "affecter_classe",
            StatutInscription.VALIDEE,
            StatutInscription.INSCRIT,
            "Affecter à une classe",
        ),
        _t("transferer", StatutInscription.INSCRIT, StatutInscription.TRANSFERE, "Transférer"),
        _t(
            "abandonner",
            StatutInscription.INSCRIT,
            StatutInscription.ABANDON,
            "Constater l'abandon",
        ),
        _t("exclure", StatutInscription.INSCRIT, StatutInscription.EXCLU, "Exclure"),
    ],
)


# ------------------------------------------------------------------
#  Workflow : candidature à une bourse
# ------------------------------------------------------------------

WORKFLOW_BOURSE = MachineEtats(
    "bourse",
    [
        _t(
            "soumettre",
            StatutCandidatureBourse.BROUILLON,
            StatutCandidatureBourse.SOUMISE,
            "Soumettre la candidature",
        ),
        _t(
            "evaluer",
            StatutCandidatureBourse.SOUMISE,
            StatutCandidatureBourse.EN_EVALUATION,
            "Évaluer le dossier",
        ),
        _t(
            "declarer_incomplete",
            StatutCandidatureBourse.EN_EVALUATION,
            StatutCandidatureBourse.INCOMPLETE,
            "Déclarer incomplète",
        ),
        _t(
            "completer",
            StatutCandidatureBourse.INCOMPLETE,
            StatutCandidatureBourse.SOUMISE,
            "Compléter",
        ),
        _t(
            "preselectionner",
            StatutCandidatureBourse.EN_EVALUATION,
            StatutCandidatureBourse.PRESELECTIONNEE,
            "Présélectionner",
        ),
        _t(
            "attribuer",
            StatutCandidatureBourse.PRESELECTIONNEE,
            StatutCandidatureBourse.ATTRIBUEE,
            "Attribuer la bourse",
        ),
        _t(
            "rejeter",
            StatutCandidatureBourse.EN_EVALUATION,
            StatutCandidatureBourse.REJETEE,
            "Rejeter",
        ),
        _t(
            "suspendre",
            StatutCandidatureBourse.ATTRIBUEE,
            StatutCandidatureBourse.SUSPENDUE,
            "Suspendre",
        ),
        _t(
            "reactiver",
            StatutCandidatureBourse.SUSPENDUE,
            StatutCandidatureBourse.ATTRIBUEE,
            "Réactiver",
        ),
        _t(
            "cloturer",
            StatutCandidatureBourse.ATTRIBUEE,
            StatutCandidatureBourse.CLOTUREE,
            "Clôturer",
        ),
    ],
)


REGISTRE: dict[str, MachineEtats] = {
    machine.nom: machine
    for machine in (WORKFLOW_DOSSIER_EXAMEN, WORKFLOW_INSCRIPTION, WORKFLOW_BOURSE)
}


async def appliquer(
    session: AsyncSession,
    machine: MachineEtats,
    *,
    entite_type: str,
    entite_id: uuid.UUID,
    statut_actuel: str,
    action: str,
    acteur_id: uuid.UUID | None = None,
    acteur_nom: str | None = None,
    roles: set[str] | None = None,
    commentaire: str | None = None,
) -> Transition:
    """Applique une transition et l'historise."""
    transition = machine.resoudre(statut_actuel, action)

    if transition.roles_autorises and not (roles and roles & set(transition.roles_autorises)):
        raise WorkflowError(
            f"Action « {action} » réservée aux rôles : "
            f"{', '.join(sorted(transition.roles_autorises))}.",
            details={"roles_requis": sorted(transition.roles_autorises)},
        )

    session.add(
        TransitionWorkflow(
            entite_type=entite_type,
            entite_id=entite_id,
            workflow=machine.nom,
            statut_avant=statut_actuel,
            statut_apres=transition.vers,
            action=action,
            commentaire=commentaire,
            acteur_id=acteur_id,
            acteur_nom=acteur_nom,
        )
    )
    return transition
