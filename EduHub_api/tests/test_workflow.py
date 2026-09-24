"""Tests du moteur de workflow."""

from __future__ import annotations

import pytest

from app.core.exceptions import WorkflowError
from app.engines.workflow import (
    WORKFLOW_BOURSE,
    WORKFLOW_DOSSIER_EXAMEN,
    WORKFLOW_INSCRIPTION,
)
from app.models.examen import StatutDossier


def test_transition_valide_mene_au_statut_attendu():
    transition = WORKFLOW_DOSSIER_EXAMEN.resoudre(StatutDossier.BROUILLON.value, "soumettre")
    assert transition.vers == StatutDossier.SOUMIS.value


def test_transition_impossible_est_refusee():
    with pytest.raises(WorkflowError) as erreur:
        WORKFLOW_DOSSIER_EXAMEN.resoudre(StatutDossier.BROUILLON.value, "admettre")
    assert "impossible" in str(erreur.value).lower()


def test_les_actions_possibles_dependent_du_statut_courant():
    actions = {
        t.action
        for t in WORKFLOW_DOSSIER_EXAMEN.transitions_possibles(StatutDossier.EN_ETUDE.value)
    }
    assert actions == {"declarer_incomplet", "valider", "rejeter"}


def test_la_chaine_complete_du_dossier_est_parcourable():
    statut = StatutDossier.BROUILLON.value
    for action in (
        "soumettre",
        "instruire",
        "valider",
        "convoquer",
        "marquer_compose",
        "marquer_corrige",
        "admettre",
    ):
        statut = WORKFLOW_DOSSIER_EXAMEN.resoudre(statut, action).vers
    assert statut == StatutDossier.ADMIS.value


def test_un_dossier_incomplet_peut_etre_complete():
    statut = WORKFLOW_DOSSIER_EXAMEN.resoudre(
        StatutDossier.EN_ETUDE.value, "declarer_incomplet"
    ).vers
    assert WORKFLOW_DOSSIER_EXAMEN.resoudre(statut, "completer").vers == StatutDossier.SOUMIS.value


def test_les_autres_workflows_exposent_leurs_transitions():
    assert WORKFLOW_INSCRIPTION.transitions_possibles("DEMANDE")
    assert WORKFLOW_BOURSE.transitions_possibles("BROUILLON")
