"""Schémas de la scolarité : années, classes, inscriptions, emploi du temps."""

from __future__ import annotations

import uuid
from datetime import date, time

from pydantic import Field

from app.models.pedagogie import JourSemaine, StatutPresence
from app.models.scolarite import (
    DecisionFinAnnee,
    RegimeScolarite,
    StatutInscription,
    TypePeriode,
)
from app.schemas.base import SchemaBase, SchemaEntree


class PeriodeLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    type_periode: TypePeriode
    numero: int
    date_debut: date
    date_fin: date
    coefficient: float
    saisie_ouverte: bool
    notes_publiees: bool


class AnneeLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    annee_debut: int
    annee_fin: int
    date_debut: date
    date_fin: date
    courante: bool
    cloturee: bool
    periodes: list[PeriodeLecture] = Field(default_factory=list)


class AnneeEcriture(SchemaEntree):
    code: str = Field(min_length=4, max_length=32)
    libelle: str = Field(min_length=1, max_length=80)
    annee_debut: int = Field(ge=1990, le=2100)
    annee_fin: int = Field(ge=1990, le=2100)
    date_debut: date
    date_fin: date
    courante: bool = False


class ClasseLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    etablissement_id: uuid.UUID
    annee_id: uuid.UUID
    niveau_id: uuid.UUID
    serie_id: uuid.UUID | None = None
    filiere_id: uuid.UUID | None = None
    salle_id: uuid.UUID | None = None
    professeur_principal_id: uuid.UUID | None = None
    effectif: int = 0
    effectif_max: int = 60
    moyenne_classe: float | None = None


class ClasseEcriture(SchemaEntree):
    code: str = Field(min_length=1, max_length=64)
    libelle: str = Field(min_length=1, max_length=120)
    etablissement_id: uuid.UUID
    annee_id: uuid.UUID
    niveau_id: uuid.UUID
    serie_id: uuid.UUID | None = None
    filiere_id: uuid.UUID | None = None
    salle_id: uuid.UUID | None = None
    professeur_principal_id: uuid.UUID | None = None
    effectif_max: int = Field(default=60, ge=1, le=200)


class ClasseMiseAJour(SchemaEntree):
    libelle: str | None = None
    salle_id: uuid.UUID | None = None
    professeur_principal_id: uuid.UUID | None = None
    effectif_max: int | None = Field(default=None, ge=1, le=200)


class InscriptionLecture(SchemaBase):
    id: uuid.UUID
    numero: str
    apprenant_id: uuid.UUID
    etablissement_id: uuid.UUID
    annee_id: uuid.UUID
    classe_id: uuid.UUID | None = None
    statut: StatutInscription
    regime: RegimeScolarite
    redoublant: bool
    boursier: bool
    date_demande: date
    date_validation: date | None = None
    frais_scolarite: float
    montant_paye: float
    moyenne_annuelle: float | None = None
    rang_annuel: int | None = None
    decision: DecisionFinAnnee
    motif_rejet: str | None = None
    # Libellés joints : une liste d'inscriptions n'a pas à recharger quatre
    # référentiels pour afficher un nom d'élève et une classe.
    apprenant_nom: str | None = None
    identifiant_educatif: str | None = None
    etablissement_nom: str | None = None
    classe_libelle: str | None = None
    annee_libelle: str | None = None


class InscriptionCreation(SchemaEntree):
    apprenant_id: uuid.UUID
    etablissement_id: uuid.UUID
    annee_id: uuid.UUID
    classe_id: uuid.UUID | None = None
    regime: RegimeScolarite = RegimeScolarite.EXTERNE
    redoublant: bool = False
    frais_scolarite: float = Field(default=0.0, ge=0)


class TransitionDemande(SchemaEntree):
    """Action de workflow appliquée à une entité."""

    action: str = Field(min_length=1, max_length=64)
    commentaire: str | None = Field(default=None, max_length=1000)
    motif: str | None = Field(default=None, max_length=500)


class CreneauLecture(SchemaBase):
    id: uuid.UUID
    classe_id: uuid.UUID
    matiere_id: uuid.UUID
    enseignant_id: uuid.UUID | None = None
    salle_id: uuid.UUID | None = None
    jour: JourSemaine
    heure_debut: time
    heure_fin: time


class CreneauEcriture(SchemaEntree):
    classe_id: uuid.UUID
    matiere_id: uuid.UUID
    enseignant_id: uuid.UUID | None = None
    salle_id: uuid.UUID | None = None
    jour: JourSemaine
    heure_debut: time
    heure_fin: time


class PresenceLecture(SchemaBase):
    id: uuid.UUID
    seance_id: uuid.UUID
    apprenant_id: uuid.UUID
    statut: StatutPresence
    minutes_retard: int
    justification: str | None = None
    nom_complet: str | None = None
    identifiant_educatif: str | None = None


class AppelLigne(SchemaEntree):
    apprenant_id: uuid.UUID
    statut: StatutPresence
    minutes_retard: int = Field(default=0, ge=0, le=240)
    justification: str | None = Field(default=None, max_length=500)


class AppelDemande(SchemaEntree):
    """Saisie de l'appel d'une séance."""

    lignes: list[AppelLigne] = Field(min_length=1)
