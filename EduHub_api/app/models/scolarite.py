"""Domaine 06 — Années académiques, niveaux, séries, filières, matières, classes."""

from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.apprenant import Apprenant
    from app.models.etablissement import Etablissement, Salle
    from app.models.personnel import Enseignant
    from app.models.referentiel import Cycle, Diplome


class TypePeriode(StrEnum):
    TRIMESTRE = "TRIMESTRE"
    SEMESTRE = "SEMESTRE"
    SESSION = "SESSION"
    MODULE = "MODULE"


class StatutInscription(StrEnum):
    DEMANDE = "DEMANDE"
    DOSSIER_DEPOSE = "DOSSIER_DEPOSE"
    EN_VERIFICATION = "EN_VERIFICATION"
    VALIDEE = "VALIDEE"
    REJETEE = "REJETEE"
    INSCRIT = "INSCRIT"
    TRANSFERE = "TRANSFERE"
    ABANDON = "ABANDON"
    EXCLU = "EXCLU"


class RegimeScolarite(StrEnum):
    EXTERNE = "EXTERNE"
    DEMI_PENSIONNAIRE = "DEMI_PENSIONNAIRE"
    INTERNE = "INTERNE"


class DecisionFinAnnee(StrEnum):
    PASSAGE = "PASSAGE"
    REDOUBLEMENT = "REDOUBLEMENT"
    ORIENTATION = "ORIENTATION"
    EXCLUSION = "EXCLUSION"
    EN_ATTENTE = "EN_ATTENTE"


class AnneeAcademique(Base):
    """Année scolaire ou académique, par exemple 2026-2027."""

    __tablename__ = "annees_academiques"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(80), nullable=False)
    annee_debut: Mapped[int] = mapped_column(nullable=False)
    annee_fin: Mapped[int] = mapped_column(nullable=False)
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)
    courante: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    cloturee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    periodes: Mapped[list[Periode]] = relationship(
        back_populates="annee", cascade="all, delete-orphan", order_by="Periode.numero"
    )


class Periode(Base):
    """Période d'évaluation : trimestre, semestre ou session."""

    __tablename__ = "periodes"

    annee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("annees_academiques.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    libelle: Mapped[str] = mapped_column(String(80), nullable=False)
    type_periode: Mapped[TypePeriode] = mapped_column(
        Enum(TypePeriode, native_enum=False), default=TypePeriode.TRIMESTRE, nullable=False
    )
    numero: Mapped[int] = mapped_column(default=1, nullable=False)
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)
    coefficient: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    saisie_ouverte: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes_publiees: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    annee: Mapped[AnneeAcademique] = relationship(back_populates="periodes", lazy="selectin")

    __table_args__ = (UniqueConstraint("annee_id", "code", name="uq_periodes_annee_code"),)


class Niveau(Base):
    """Niveau d'études : CI, CP, 6e, Terminale, Licence 1…"""

    __tablename__ = "niveaux"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(120), nullable=False)
    cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cycles.id", ondelete="SET NULL"), index=True
    )
    rang: Mapped[int] = mapped_column(default=0, nullable=False)
    niveau_examen_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("types_examen.id", ondelete="SET NULL")
    )
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    cycle: Mapped[Cycle | None] = relationship(lazy="selectin")


class Serie(Base):
    """Série d'enseignement : A1, A2, B, C, D, E, F1…, G1…"""

    __tablename__ = "series"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cycles.id", ondelete="SET NULL"), index=True
    )
    technique: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    cycle: Mapped[Cycle | None] = relationship(lazy="selectin")


class Filiere(Base):
    """Filière de formation, notamment dans le technique et le supérieur."""

    __tablename__ = "filieres"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    diplome_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("diplomes_referentiel.id", ondelete="SET NULL")
    )
    duree_annees: Mapped[int] = mapped_column(default=3, nullable=False)
    debouches: Mapped[str | None] = mapped_column(Text)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    diplome: Mapped[Diplome | None] = relationship(lazy="selectin")


class Matiere(Base):
    """Matière ou discipline enseignée."""

    __tablename__ = "matieres"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(180), nullable=False)
    abreviation: Mapped[str | None] = mapped_column(String(16))
    domaine: Mapped[str | None] = mapped_column(String(120))
    coefficient_defaut: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    volume_horaire_defaut: Mapped[int] = mapped_column(default=0, nullable=False)
    couleur: Mapped[str | None] = mapped_column(String(16))
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    affectations: Mapped[list[MatiereNiveau]] = relationship(
        back_populates="matiere", cascade="all, delete-orphan"
    )


class MatiereNiveau(Base):
    """Paramétrage d'une matière pour un niveau et une série donnés."""

    __tablename__ = "matieres_niveaux"

    matiere_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matieres.id", ondelete="CASCADE"), index=True, nullable=False
    )
    niveau_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("niveaux.id", ondelete="CASCADE"), index=True, nullable=False
    )
    serie_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("series.id", ondelete="CASCADE"), index=True
    )
    coefficient: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    volume_horaire: Mapped[int] = mapped_column(default=0, nullable=False)
    obligatoire: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    matiere: Mapped[Matiere] = relationship(back_populates="affectations", lazy="selectin")
    niveau: Mapped[Niveau] = relationship(lazy="selectin")
    serie: Mapped[Serie | None] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("matiere_id", "niveau_id", "serie_id", name="uq_matieres_niveaux"),
    )


class Classe(Base):
    """Classe d'un établissement pour une année académique."""

    __tablename__ = "classes"

    etablissement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("etablissements.id", ondelete="CASCADE"), index=True, nullable=False
    )
    annee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("annees_academiques.id", ondelete="CASCADE"), index=True, nullable=False
    )
    niveau_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("niveaux.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    serie_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("series.id", ondelete="SET NULL"), index=True
    )
    filiere_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("filieres.id", ondelete="SET NULL"), index=True
    )
    salle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("salles.id", ondelete="SET NULL"), index=True
    )
    professeur_principal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enseignants.id", ondelete="SET NULL"), index=True
    )

    code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(120), nullable=False)
    effectif_max: Mapped[int] = mapped_column(default=60, nullable=False)
    effectif: Mapped[int] = mapped_column(default=0, nullable=False)
    moyenne_classe: Mapped[float | None] = mapped_column(Float)

    etablissement: Mapped[Etablissement] = relationship(lazy="selectin")
    annee: Mapped[AnneeAcademique] = relationship(lazy="selectin")
    niveau: Mapped[Niveau] = relationship(lazy="selectin")
    serie: Mapped[Serie | None] = relationship(lazy="selectin")
    filiere: Mapped[Filiere | None] = relationship(lazy="selectin")
    salle: Mapped[Salle | None] = relationship(lazy="selectin")
    professeur_principal: Mapped[Enseignant | None] = relationship(lazy="selectin")
    inscriptions: Mapped[list[Inscription]] = relationship(back_populates="classe")

    __table_args__ = (
        UniqueConstraint("etablissement_id", "annee_id", "code", name="uq_classes_code_annee"),
        Index("ix_classes_etab_annee_niveau", "etablissement_id", "annee_id", "niveau_id"),
    )


class Inscription(Base):
    """Inscription d'un apprenant dans une classe pour une année académique."""

    __tablename__ = "inscriptions"

    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    etablissement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("etablissements.id", ondelete="CASCADE"), index=True, nullable=False
    )
    annee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("annees_academiques.id", ondelete="CASCADE"), index=True, nullable=False
    )
    classe_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("classes.id", ondelete="SET NULL"), index=True
    )

    numero: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    statut: Mapped[StatutInscription] = mapped_column(
        Enum(StatutInscription, native_enum=False),
        default=StatutInscription.DEMANDE,
        nullable=False,
        index=True,
    )
    regime: Mapped[RegimeScolarite] = mapped_column(
        Enum(RegimeScolarite, native_enum=False), default=RegimeScolarite.EXTERNE, nullable=False
    )
    redoublant: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    boursier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    date_demande: Mapped[date] = mapped_column(Date, nullable=False)
    date_validation: Mapped[date | None] = mapped_column(Date)
    frais_scolarite: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    montant_paye: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    moyenne_annuelle: Mapped[float | None] = mapped_column(Float)
    rang_annuel: Mapped[int | None] = mapped_column()
    decision: Mapped[DecisionFinAnnee] = mapped_column(
        Enum(DecisionFinAnnee, native_enum=False),
        default=DecisionFinAnnee.EN_ATTENTE,
        nullable=False,
    )
    motif_rejet: Mapped[str | None] = mapped_column(String(500))
    observations: Mapped[str | None] = mapped_column(Text)

    apprenant: Mapped[Apprenant] = relationship(back_populates="inscriptions", lazy="selectin")
    etablissement: Mapped[Etablissement] = relationship(lazy="selectin")
    annee: Mapped[AnneeAcademique] = relationship(lazy="selectin")
    classe: Mapped[Classe | None] = relationship(back_populates="inscriptions", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("apprenant_id", "annee_id", name="uq_inscriptions_apprenant_annee"),
        Index("ix_inscriptions_etab_annee", "etablissement_id", "annee_id"),
    )


class Transfert(Base):
    """Demande de transfert d'un apprenant entre deux établissements."""

    __tablename__ = "transferts"

    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    etablissement_origine_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("etablissements.id", ondelete="CASCADE"), index=True, nullable=False
    )
    etablissement_destination_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("etablissements.id", ondelete="CASCADE"), index=True, nullable=False
    )
    annee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("annees_academiques.id", ondelete="CASCADE"), index=True, nullable=False
    )
    motif: Mapped[str] = mapped_column(String(500), nullable=False)
    statut: Mapped[StatutInscription] = mapped_column(
        Enum(StatutInscription, native_enum=False),
        default=StatutInscription.DEMANDE,
        nullable=False,
    )
    date_demande: Mapped[date] = mapped_column(Date, nullable=False)
    date_decision: Mapped[date | None] = mapped_column(Date)
    decide_par_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )
    observations: Mapped[str | None] = mapped_column(Text)

    apprenant: Mapped[Apprenant] = relationship(lazy="selectin")
    etablissement_origine: Mapped[Etablissement] = relationship(
        foreign_keys=[etablissement_origine_id], lazy="selectin"
    )
    etablissement_destination: Mapped[Etablissement] = relationship(
        foreign_keys=[etablissement_destination_id], lazy="selectin"
    )
