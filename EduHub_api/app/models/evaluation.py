"""Domaine 08 — Évaluations, notes, bulletins et conseils de classe."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
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

if TYPE_CHECKING:
    from app.models.apprenant import Apprenant
    from app.models.personnel import Enseignant
    from app.models.scolarite import Classe, Matiere, Periode


class TypeEvaluation(StrEnum):
    DEVOIR = "DEVOIR"
    INTERROGATION = "INTERROGATION"
    TRAVAUX_PRATIQUES = "TRAVAUX_PRATIQUES"
    PROJET = "PROJET"
    EXAMEN_BLANC = "EXAMEN_BLANC"
    EXAMEN = "EXAMEN"
    CONTROLE_CONTINU = "CONTROLE_CONTINU"
    ORAL = "ORAL"
    EVALUATION_PRATIQUE = "EVALUATION_PRATIQUE"


class StatutEvaluation(StrEnum):
    PLANIFIEE = "PLANIFIEE"
    EN_SAISIE = "EN_SAISIE"
    SAISIE_TERMINEE = "SAISIE_TERMINEE"
    VALIDEE_ENSEIGNANT = "VALIDEE_ENSEIGNANT"
    VALIDEE_ETABLISSEMENT = "VALIDEE_ETABLISSEMENT"
    PUBLIEE = "PUBLIEE"
    ANNULEE = "ANNULEE"


class StatutNote(StrEnum):
    SAISIE = "SAISIE"
    ABSENT = "ABSENT"
    ABSENT_JUSTIFIE = "ABSENT_JUSTIFIE"
    DISPENSE = "DISPENSE"
    NON_RENDU = "NON_RENDU"
    FRAUDE = "FRAUDE"


class DecisionConseil(StrEnum):
    PASSAGE = "PASSAGE"
    REDOUBLEMENT = "REDOUBLEMENT"
    ORIENTATION = "ORIENTATION"
    ENCOURAGEMENT = "ENCOURAGEMENT"
    FELICITATIONS = "FELICITATIONS"
    AVERTISSEMENT_TRAVAIL = "AVERTISSEMENT_TRAVAIL"
    AVERTISSEMENT_CONDUITE = "AVERTISSEMENT_CONDUITE"
    BLAME = "BLAME"


class Evaluation(Base):
    """Évaluation organisée pour une classe dans une matière."""

    __tablename__ = "evaluations"

    classe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    matiere_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matieres.id", ondelete="CASCADE"), index=True, nullable=False
    )
    periode_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("periodes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    enseignant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enseignants.id", ondelete="SET NULL"), index=True
    )

    code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    intitule: Mapped[str] = mapped_column(String(255), nullable=False)
    type_evaluation: Mapped[TypeEvaluation] = mapped_column(
        Enum(TypeEvaluation, native_enum=False), default=TypeEvaluation.DEVOIR, nullable=False
    )
    date_evaluation: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    bareme: Mapped[float] = mapped_column(Float, default=20.0, nullable=False)
    coefficient: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    duree_minutes: Mapped[int | None] = mapped_column()
    statut: Mapped[StatutEvaluation] = mapped_column(
        Enum(StatutEvaluation, native_enum=False),
        default=StatutEvaluation.PLANIFIEE,
        nullable=False,
        index=True,
    )
    consignes: Mapped[str | None] = mapped_column(Text)
    sujet_url: Mapped[str | None] = mapped_column(String(500))

    # --- Statistiques calculées ---
    moyenne: Mapped[float | None] = mapped_column(Float)
    note_min: Mapped[float | None] = mapped_column(Float)
    note_max: Mapped[float | None] = mapped_column(Float)
    ecart_type: Mapped[float | None] = mapped_column(Float)
    nombre_notes: Mapped[int] = mapped_column(default=0, nullable=False)

    valide_enseignant_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valide_etablissement_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    publiee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    classe: Mapped[Classe] = relationship(lazy="selectin")
    matiere: Mapped[Matiere] = relationship(lazy="selectin")
    periode: Mapped[Periode] = relationship(lazy="selectin")
    enseignant: Mapped[Enseignant | None] = relationship(lazy="selectin")
    notes: Mapped[list[Note]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_evaluations_classe_periode", "classe_id", "periode_id", "matiere_id"),
    )

    @property
    def classe_libelle(self) -> str | None:
        return self.classe.libelle if self.classe else None

    @property
    def matiere_libelle(self) -> str | None:
        return self.matiere.libelle if self.matiere else None

    @property
    def periode_libelle(self) -> str | None:
        return self.periode.libelle if self.periode else None


class Note(Base):
    """Note obtenue par un apprenant à une évaluation."""

    __tablename__ = "notes"

    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    valeur: Mapped[float | None] = mapped_column(Float)
    statut: Mapped[StatutNote] = mapped_column(
        Enum(StatutNote, native_enum=False), default=StatutNote.SAISIE, nullable=False
    )
    appreciation: Mapped[str | None] = mapped_column(String(500))
    rang: Mapped[int | None] = mapped_column()
    saisie_par_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )
    modifiee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ancienne_valeur: Mapped[float | None] = mapped_column(Float)

    evaluation: Mapped[Evaluation] = relationship(back_populates="notes")
    apprenant: Mapped[Apprenant] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("evaluation_id", "apprenant_id", name="uq_notes_evaluation_apprenant"),
    )

    @property
    def note_sur_20(self) -> float | None:
        if self.valeur is None or not self.evaluation or not self.evaluation.bareme:
            return self.valeur
        return round(self.valeur * 20 / self.evaluation.bareme, 2)


class MoyenneMatiere(Base):
    """Moyenne d'un apprenant dans une matière pour une période."""

    __tablename__ = "moyennes_matiere"

    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    classe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    matiere_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matieres.id", ondelete="CASCADE"), index=True, nullable=False
    )
    periode_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("periodes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    moyenne: Mapped[float | None] = mapped_column(Float, index=True)
    coefficient: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    rang: Mapped[int | None] = mapped_column()
    moyenne_classe: Mapped[float | None] = mapped_column(Float)
    note_min_classe: Mapped[float | None] = mapped_column(Float)
    note_max_classe: Mapped[float | None] = mapped_column(Float)
    appreciation: Mapped[str | None] = mapped_column(String(500))

    __table_args__ = (
        UniqueConstraint("apprenant_id", "matiere_id", "periode_id", name="uq_moyennes_matiere"),
        Index("ix_moyennes_matiere_recherche", "matiere_id", "periode_id", "moyenne"),
    )


class Bulletin(Base):
    """Bulletin de notes d'un apprenant pour une période."""

    __tablename__ = "bulletins"

    numero: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    classe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    periode_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("periodes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    etablissement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("etablissements.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # --- Résultats ---
    moyenne_generale: Mapped[float | None] = mapped_column(Float, index=True)
    total_points: Mapped[float | None] = mapped_column(Float)
    total_coefficients: Mapped[float | None] = mapped_column(Float)
    rang: Mapped[int | None] = mapped_column()
    effectif_classe: Mapped[int | None] = mapped_column()
    moyenne_classe: Mapped[float | None] = mapped_column(Float)
    moyenne_premier: Mapped[float | None] = mapped_column(Float)
    moyenne_dernier: Mapped[float | None] = mapped_column(Float)

    # --- Assiduité ---
    absences_heures: Mapped[int] = mapped_column(default=0, nullable=False)
    absences_justifiees: Mapped[int] = mapped_column(default=0, nullable=False)
    retards: Mapped[int] = mapped_column(default=0, nullable=False)

    # --- Appréciations et décision ---
    appreciation_generale: Mapped[str | None] = mapped_column(Text)
    appreciation_conduite: Mapped[str | None] = mapped_column(String(255))
    decision: Mapped[DecisionConseil | None] = mapped_column(
        Enum(DecisionConseil, native_enum=False)
    )
    mention: Mapped[str | None] = mapped_column(String(64))

    # --- Publication ---
    publie: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    publie_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pdf_url: Mapped[str | None] = mapped_column(String(500))
    code_verification: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    qr_code_url: Mapped[str | None] = mapped_column(String(500))
    signature_numerique: Mapped[str | None] = mapped_column(String(255))

    apprenant: Mapped[Apprenant] = relationship(lazy="selectin")
    classe: Mapped[Classe] = relationship(lazy="selectin")
    periode: Mapped[Periode] = relationship(lazy="selectin")
    lignes: Mapped[list[BulletinMatiere]] = relationship(
        back_populates="bulletin", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("apprenant_id", "periode_id", name="uq_bulletins_apprenant_periode"),
    )


class BulletinMatiere(Base):
    """Ligne d'un bulletin, correspondant à une matière."""

    __tablename__ = "bulletins_matieres"

    bulletin_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bulletins.id", ondelete="CASCADE"), index=True, nullable=False
    )
    matiere_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matieres.id", ondelete="CASCADE"), index=True, nullable=False
    )
    enseignant_nom: Mapped[str | None] = mapped_column(String(180))
    moyenne: Mapped[float | None] = mapped_column(Float)
    coefficient: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    points: Mapped[float | None] = mapped_column(Float)
    rang: Mapped[int | None] = mapped_column()
    moyenne_classe: Mapped[float | None] = mapped_column(Float)
    note_min: Mapped[float | None] = mapped_column(Float)
    note_max: Mapped[float | None] = mapped_column(Float)
    appreciation: Mapped[str | None] = mapped_column(String(500))
    ordre: Mapped[int] = mapped_column(default=0, nullable=False)

    bulletin: Mapped[Bulletin] = relationship(back_populates="lignes")
    matiere: Mapped[Matiere] = relationship(lazy="selectin")

    __table_args__ = (UniqueConstraint("bulletin_id", "matiere_id", name="uq_bulletins_matieres"),)


class ConseilClasse(Base):
    """Conseil de classe tenu à l'issue d'une période."""

    __tablename__ = "conseils_classe"

    classe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    periode_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("periodes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    date_conseil: Mapped[date] = mapped_column(Date, nullable=False)
    president_nom: Mapped[str | None] = mapped_column(String(180))
    participants: Mapped[str | None] = mapped_column(Text)
    moyenne_classe: Mapped[float | None] = mapped_column(Float)
    taux_reussite: Mapped[float | None] = mapped_column(Float)
    observations: Mapped[str | None] = mapped_column(Text)
    cloture: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    decisions: Mapped[list[DecisionConseilApprenant]] = relationship(
        back_populates="conseil", cascade="all, delete-orphan"
    )
    classe: Mapped[Classe] = relationship(lazy="selectin")
    periode: Mapped[Periode] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("classe_id", "periode_id", name="uq_conseils_classe_periode"),
    )

    @property
    def classe_libelle(self) -> str | None:
        return self.classe.libelle if self.classe else None

    @property
    def periode_libelle(self) -> str | None:
        return self.periode.libelle if self.periode else None


class DecisionConseilApprenant(Base):
    """Décision individuelle prise en conseil de classe."""

    __tablename__ = "decisions_conseil"

    conseil_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conseils_classe.id", ondelete="CASCADE"), index=True, nullable=False
    )
    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    decision: Mapped[DecisionConseil] = mapped_column(
        Enum(DecisionConseil, native_enum=False), nullable=False
    )
    motivation: Mapped[str | None] = mapped_column(Text)
    orientation_proposee: Mapped[str | None] = mapped_column(String(255))

    conseil: Mapped[ConseilClasse] = relationship(back_populates="decisions")
    apprenant: Mapped[Apprenant] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("conseil_id", "apprenant_id", name="uq_decisions_conseil_apprenant"),
    )
