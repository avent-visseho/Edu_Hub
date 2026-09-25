"""Schémas des évaluations, notes, bulletins et conseils de classe."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import Field, field_validator

from app.models.evaluation import (
    DecisionConseil,
    StatutEvaluation,
    StatutNote,
    TypeEvaluation,
)
from app.schemas.base import SchemaBase, SchemaEntree


class EvaluationLecture(SchemaBase):
    id: uuid.UUID
    code: str
    intitule: str
    classe_id: uuid.UUID
    classe_libelle: str | None = None
    matiere_id: uuid.UUID
    matiere_libelle: str | None = None
    periode_id: uuid.UUID
    periode_libelle: str | None = None
    enseignant_id: uuid.UUID | None = None
    type_evaluation: TypeEvaluation
    date_evaluation: date
    bareme: float
    coefficient: float
    duree_minutes: int | None = None
    statut: StatutEvaluation
    moyenne: float | None = None
    note_min: float | None = None
    note_max: float | None = None
    ecart_type: float | None = None
    nombre_notes: int


class EvaluationCreation(SchemaEntree):
    code: str | None = Field(default=None, max_length=64)
    intitule: str = Field(min_length=1, max_length=255)
    classe_id: uuid.UUID
    classe_libelle: str | None = None
    matiere_id: uuid.UUID
    matiere_libelle: str | None = None
    periode_id: uuid.UUID
    periode_libelle: str | None = None
    enseignant_id: uuid.UUID | None = None
    type_evaluation: TypeEvaluation = TypeEvaluation.DEVOIR
    date_evaluation: date
    bareme: float = Field(default=20.0, gt=0, le=100)
    coefficient: float = Field(default=1.0, gt=0, le=20)
    duree_minutes: int | None = Field(default=None, ge=5, le=480)
    consignes: str | None = None


class EvaluationMiseAJour(SchemaEntree):
    intitule: str | None = None
    date_evaluation: date | None = None
    bareme: float | None = Field(default=None, gt=0, le=100)
    coefficient: float | None = Field(default=None, gt=0, le=20)
    duree_minutes: int | None = Field(default=None, ge=5, le=480)
    consignes: str | None = None
    statut: StatutEvaluation | None = None


class NoteLecture(SchemaBase):
    id: uuid.UUID
    evaluation_id: uuid.UUID
    apprenant_id: uuid.UUID
    valeur: float | None = None
    statut: StatutNote
    appreciation: str | None = None
    rang: int | None = None
    modifiee: bool


class NoteSaisie(SchemaEntree):
    """Note saisie pour un apprenant."""

    apprenant_id: uuid.UUID
    valeur: float | None = Field(default=None, ge=0, le=100)
    statut: StatutNote = StatutNote.SAISIE
    appreciation: str | None = Field(default=None, max_length=500)

    @field_validator("valeur")
    @classmethod
    def _valeur_requise(cls, valeur: float | None, info) -> float | None:
        statut = info.data.get("statut", StatutNote.SAISIE)
        if statut is StatutNote.SAISIE and valeur is None:
            raise ValueError("Une note est requise lorsque le statut est « saisie ».")
        return valeur


class SaisieNotesDemande(SchemaEntree):
    """Saisie groupée des notes d'une évaluation."""

    notes: list[NoteSaisie] = Field(min_length=1)


class MoyenneMatiereLecture(SchemaBase):
    matiere_id: uuid.UUID
    matiere_libelle: str | None = None
    moyenne: float | None = None
    coefficient: float
    rang: int | None = None
    moyenne_classe: float | None = None
    note_min_classe: float | None = None
    note_max_classe: float | None = None
    appreciation: str | None = None


class BulletinLigne(SchemaBase):
    matiere_id: uuid.UUID
    matiere_libelle: str | None = None
    enseignant_nom: str | None = None
    moyenne: float | None = None
    coefficient: float
    points: float | None = None
    rang: int | None = None
    moyenne_classe: float | None = None
    note_min: float | None = None
    note_max: float | None = None
    appreciation: str | None = None


class BulletinLecture(SchemaBase):
    id: uuid.UUID
    numero: str
    apprenant_id: uuid.UUID
    classe_id: uuid.UUID
    periode_id: uuid.UUID
    etablissement_id: uuid.UUID
    moyenne_generale: float | None = None
    total_points: float | None = None
    total_coefficients: float | None = None
    rang: int | None = None
    effectif_classe: int | None = None
    moyenne_classe: float | None = None
    moyenne_premier: float | None = None
    moyenne_dernier: float | None = None
    absences_heures: int
    absences_justifiees: int
    retards: int
    appreciation_generale: str | None = None
    appreciation_conduite: str | None = None
    decision: DecisionConseil | None = None
    mention: str | None = None
    publie: bool
    code_verification: str | None = None


class BulletinDetail(BulletinLecture):
    """Bulletin complet, prêt à être imprimé."""

    apprenant_nom: str | None = None
    apprenant_identifiant: str | None = None
    classe_libelle: str | None = None
    etablissement_nom: str | None = None
    periode_libelle: str | None = None
    annee_libelle: str | None = None
    lignes: list[BulletinLigne] = Field(default_factory=list)


class GenerationBulletins(SchemaEntree):
    """Demande de calcul des bulletins d'une classe pour une période."""

    classe_id: uuid.UUID
    periode_id: uuid.UUID
    publier: bool = False


class ConseilClasseLecture(SchemaBase):
    id: uuid.UUID
    classe_id: uuid.UUID
    periode_id: uuid.UUID
    date_conseil: date
    president_nom: str | None = None
    moyenne_classe: float | None = None
    taux_reussite: float | None = None
    observations: str | None = None
    cloture: bool
    # Libellés joints : la liste des conseils se lit sans recharger les classes.
    classe_libelle: str | None = None
    periode_libelle: str | None = None


class StatistiquesClasse(SchemaBase):
    """Indicateurs consolidés d'une classe sur une période."""

    classe_id: uuid.UUID
    classe_libelle: str
    periode_libelle: str
    effectif: int
    moyenne_classe: float | None = None
    moyenne_maximale: float | None = None
    moyenne_minimale: float | None = None
    nombre_moyennes_superieures_10: int = 0
    taux_reussite: float = 0.0
    distribution: list[dict] = Field(default_factory=list)
    par_matiere: list[dict] = Field(default_factory=list)
