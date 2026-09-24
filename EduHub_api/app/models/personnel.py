"""Domaine 05 — Enseignants, personnel et carrières."""

from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import Sexe, TypeHandicap
from app.core.mixins import SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.etablissement import Etablissement
    from app.models.identity import Utilisateur
    from app.models.scolarite import Matiere


class StatutAgent(StrEnum):
    FONCTIONNAIRE = "FONCTIONNAIRE"
    CONTRACTUEL_ETAT = "CONTRACTUEL_ETAT"
    CONTRACTUEL_LOCAL = "CONTRACTUEL_LOCAL"
    VACATAIRE = "VACATAIRE"
    COMMUNAUTAIRE = "COMMUNAUTAIRE"
    BENEVOLE = "BENEVOLE"
    STAGIAIRE = "STAGIAIRE"


class SituationAgent(StrEnum):
    EN_SERVICE = "EN_SERVICE"
    DISPONIBILITE = "DISPONIBILITE"
    DETACHEMENT = "DETACHEMENT"
    FORMATION = "FORMATION"
    CONGE = "CONGE"
    SUSPENDU = "SUSPENDU"
    RETRAITE = "RETRAITE"


class TypeEvenementCarriere(StrEnum):
    RECRUTEMENT = "RECRUTEMENT"
    AFFECTATION = "AFFECTATION"
    PRISE_SERVICE = "PRISE_SERVICE"
    MUTATION = "MUTATION"
    PROMOTION = "PROMOTION"
    FORMATION = "FORMATION"
    EVALUATION = "EVALUATION"
    SANCTION = "SANCTION"
    DEPART = "DEPART"


class CategoriePersonnel(StrEnum):
    ENSEIGNANT = "ENSEIGNANT"
    DIRECTION = "DIRECTION"
    ADMINISTRATIF = "ADMINISTRATIF"
    SURVEILLANCE = "SURVEILLANCE"
    TECHNIQUE = "TECHNIQUE"
    SANTE = "SANTE"
    BIBLIOTHEQUE = "BIBLIOTHEQUE"
    SECURITE = "SECURITE"
    ENTRETIEN = "ENTRETIEN"


class Enseignant(Base, SoftDeleteMixin):
    """Enseignant du système éducatif."""

    __tablename__ = "enseignants"

    matricule: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    utilisateur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL"), unique=True, index=True
    )

    nom: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    prenoms: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    sexe: Mapped[Sexe] = mapped_column(Enum(Sexe, native_enum=False), nullable=False)
    date_naissance: Mapped[date | None] = mapped_column(Date)
    telephone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(180))
    photo_url: Mapped[str | None] = mapped_column(String(500))

    # --- Qualification ---
    diplome_le_plus_eleve: Mapped[str | None] = mapped_column(String(180))
    specialite: Mapped[str | None] = mapped_column(String(180))
    grade: Mapped[str | None] = mapped_column(String(120))
    echelon: Mapped[int | None] = mapped_column()

    # --- Carrière ---
    statut_agent: Mapped[StatutAgent] = mapped_column(
        Enum(StatutAgent, native_enum=False), default=StatutAgent.CONTRACTUEL_ETAT, nullable=False
    )
    situation: Mapped[SituationAgent] = mapped_column(
        Enum(SituationAgent, native_enum=False),
        default=SituationAgent.EN_SERVICE,
        nullable=False,
        index=True,
    )
    date_recrutement: Mapped[date | None] = mapped_column(Date)
    date_prise_service: Mapped[date | None] = mapped_column(Date)
    etablissement_principal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    heures_hebdomadaires: Mapped[int] = mapped_column(default=18, nullable=False)

    # --- Aptitudes examens ---
    peut_surveiller: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    peut_corriger: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    peut_presider_jury: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    type_handicap: Mapped[TypeHandicap] = mapped_column(
        Enum(TypeHandicap, native_enum=False), default=TypeHandicap.AUCUN, nullable=False
    )
    observations: Mapped[str | None] = mapped_column(Text)

    utilisateur: Mapped[Utilisateur | None] = relationship(lazy="selectin")
    etablissement_principal: Mapped[Etablissement | None] = relationship(lazy="selectin")
    matieres: Mapped[list[EnseignantMatiere]] = relationship(
        back_populates="enseignant", cascade="all, delete-orphan"
    )
    affectations: Mapped[list[AffectationEnseignant]] = relationship(
        back_populates="enseignant", cascade="all, delete-orphan"
    )
    carriere: Mapped[list[EvenementCarriere]] = relationship(
        back_populates="enseignant", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_enseignants_nom_prenoms", "nom", "prenoms"),)

    @property
    def nom_complet(self) -> str:
        return f"{self.prenoms} {self.nom}".strip()

    @property
    def anciennete_annees(self) -> int:
        if not self.date_prise_service:
            return 0
        return max(0, date.today().year - self.date_prise_service.year)


class EnseignantMatiere(Base):
    """Matière qu'un enseignant est habilité à enseigner."""

    __tablename__ = "enseignants_matieres"

    enseignant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enseignants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    matiere_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matieres.id", ondelete="CASCADE"), index=True, nullable=False
    )
    principale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    enseignant: Mapped[Enseignant] = relationship(back_populates="matieres")
    matiere: Mapped[Matiere] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("enseignant_id", "matiere_id", name="uq_enseignants_matieres"),
    )


class AffectationEnseignant(Base):
    """Affectation d'un enseignant à un établissement pour une année donnée."""

    __tablename__ = "affectations_enseignant"

    enseignant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enseignants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    etablissement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("etablissements.id", ondelete="CASCADE"), index=True, nullable=False
    )
    annee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("annees_academiques.id", ondelete="CASCADE"), index=True, nullable=False
    )
    principale: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    heures_semaine: Mapped[int] = mapped_column(default=0, nullable=False)
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date | None] = mapped_column(Date)
    reference_acte: Mapped[str | None] = mapped_column(String(180))

    enseignant: Mapped[Enseignant] = relationship(back_populates="affectations")
    etablissement: Mapped[Etablissement] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "enseignant_id", "etablissement_id", "annee_id", name="uq_affectations_enseignant"
        ),
    )


class EvenementCarriere(Base):
    """Événement du parcours professionnel d'un enseignant."""

    __tablename__ = "evenements_carriere"

    enseignant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enseignants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type_evenement: Mapped[TypeEvenementCarriere] = mapped_column(
        Enum(TypeEvenementCarriere, native_enum=False), nullable=False
    )
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    date_evenement: Mapped[date] = mapped_column(Date, nullable=False)
    reference_acte: Mapped[str | None] = mapped_column(String(180))
    note_evaluation: Mapped[float | None] = mapped_column(Float)
    details: Mapped[str | None] = mapped_column(Text)

    enseignant: Mapped[Enseignant] = relationship(back_populates="carriere")


class Personnel(Base, SoftDeleteMixin):
    """Personnel non enseignant d'un établissement ou d'une structure."""

    __tablename__ = "personnels"

    matricule: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    utilisateur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL"), unique=True, index=True
    )
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    structure_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("structures.id", ondelete="SET NULL"), index=True
    )

    nom: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    prenoms: Mapped[str] = mapped_column(String(180), nullable=False)
    sexe: Mapped[Sexe] = mapped_column(Enum(Sexe, native_enum=False), nullable=False)
    categorie: Mapped[CategoriePersonnel] = mapped_column(
        Enum(CategoriePersonnel, native_enum=False),
        default=CategoriePersonnel.ADMINISTRATIF,
        nullable=False,
        index=True,
    )
    fonction: Mapped[str] = mapped_column(String(180), nullable=False)
    statut_agent: Mapped[StatutAgent] = mapped_column(
        Enum(StatutAgent, native_enum=False), default=StatutAgent.CONTRACTUEL_LOCAL, nullable=False
    )
    situation: Mapped[SituationAgent] = mapped_column(
        Enum(SituationAgent, native_enum=False), default=SituationAgent.EN_SERVICE, nullable=False
    )
    telephone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(180))
    date_prise_service: Mapped[date | None] = mapped_column(Date)
    peut_saisir_notes: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    utilisateur: Mapped[Utilisateur | None] = relationship(lazy="selectin")
    etablissement: Mapped[Etablissement | None] = relationship(lazy="selectin")

    @property
    def nom_complet(self) -> str:
        return f"{self.prenoms} {self.nom}".strip()
