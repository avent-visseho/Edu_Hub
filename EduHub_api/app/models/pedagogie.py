"""Domaine 07 — Programmes, curricula, emploi du temps et présences."""

from __future__ import annotations

import uuid
from datetime import date, time
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
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.apprenant import Apprenant
    from app.models.etablissement import Salle
    from app.models.personnel import Enseignant
    from app.models.scolarite import Classe, Matiere, Niveau, Serie


class JourSemaine(StrEnum):
    LUNDI = "LUNDI"
    MARDI = "MARDI"
    MERCREDI = "MERCREDI"
    JEUDI = "JEUDI"
    VENDREDI = "VENDREDI"
    SAMEDI = "SAMEDI"
    DIMANCHE = "DIMANCHE"


class StatutPresence(StrEnum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    RETARD = "RETARD"
    ABSENCE_JUSTIFIEE = "ABSENCE_JUSTIFIEE"
    ABSENCE_INJUSTIFIEE = "ABSENCE_INJUSTIFIEE"
    EXCLU_COURS = "EXCLU_COURS"


class StatutSeance(StrEnum):
    PLANIFIEE = "PLANIFIEE"
    TENUE = "TENUE"
    ANNULEE = "ANNULEE"
    REPORTEE = "REPORTEE"


class Programme(Base):
    """Programme officiel d'une matière pour un niveau et une série."""

    __tablename__ = "programmes"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    matiere_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matieres.id", ondelete="CASCADE"), index=True, nullable=False
    )
    niveau_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("niveaux.id", ondelete="CASCADE"), index=True, nullable=False
    )
    serie_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("series.id", ondelete="SET NULL"), index=True
    )
    annee_reference: Mapped[int | None] = mapped_column()
    volume_horaire: Mapped[int] = mapped_column(default=0, nullable=False)
    objectifs_generaux: Mapped[str | None] = mapped_column(Text)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    matiere: Mapped[Matiere] = relationship(lazy="selectin")
    niveau: Mapped[Niveau] = relationship(lazy="selectin")
    serie: Mapped[Serie | None] = relationship(lazy="selectin")
    chapitres: Mapped[list[Chapitre]] = relationship(
        back_populates="programme", cascade="all, delete-orphan", order_by="Chapitre.ordre"
    )


class Chapitre(Base):
    """Chapitre d'un programme."""

    __tablename__ = "chapitres"

    programme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programmes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    titre: Mapped[str] = mapped_column(String(255), nullable=False)
    contenu: Mapped[str | None] = mapped_column(Text)
    ordre: Mapped[int] = mapped_column(default=0, nullable=False)
    duree_heures: Mapped[int] = mapped_column(default=0, nullable=False)

    programme: Mapped[Programme] = relationship(back_populates="chapitres")
    competences: Mapped[list[Competence]] = relationship(
        back_populates="chapitre", cascade="all, delete-orphan"
    )


class Competence(Base):
    """Compétence ou objectif pédagogique rattaché à un chapitre."""

    __tablename__ = "competences"

    chapitre_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chapitres.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(500), nullable=False)
    domaine: Mapped[str | None] = mapped_column(String(180))
    niveau_maitrise: Mapped[str | None] = mapped_column(String(80))
    transversale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    chapitre: Mapped[Chapitre | None] = relationship(back_populates="competences")


class CreneauEmploiDuTemps(Base):
    """Créneau récurrent de l'emploi du temps d'une classe."""

    __tablename__ = "creneaux_emploi_du_temps"

    classe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    matiere_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matieres.id", ondelete="CASCADE"), index=True, nullable=False
    )
    enseignant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enseignants.id", ondelete="SET NULL"), index=True
    )
    salle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("salles.id", ondelete="SET NULL"), index=True
    )
    jour: Mapped[JourSemaine] = mapped_column(
        Enum(JourSemaine, native_enum=False), nullable=False, index=True
    )
    heure_debut: Mapped[time] = mapped_column(Time, nullable=False)
    heure_fin: Mapped[time] = mapped_column(Time, nullable=False)
    semaine_paire: Mapped[bool | None] = mapped_column(Boolean)

    classe: Mapped[Classe] = relationship(lazy="selectin")
    matiere: Mapped[Matiere] = relationship(lazy="selectin")
    enseignant: Mapped[Enseignant | None] = relationship(lazy="selectin")
    salle: Mapped[Salle | None] = relationship(lazy="selectin")

    __table_args__ = (
        Index("ix_creneaux_enseignant_jour", "enseignant_id", "jour", "heure_debut"),
        Index("ix_creneaux_salle_jour", "salle_id", "jour", "heure_debut"),
    )


class Seance(Base):
    """Séance de cours effectivement programmée à une date donnée."""

    __tablename__ = "seances"

    creneau_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("creneaux_emploi_du_temps.id", ondelete="SET NULL"), index=True
    )
    classe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    matiere_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matieres.id", ondelete="CASCADE"), index=True, nullable=False
    )
    enseignant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enseignants.id", ondelete="SET NULL"), index=True
    )
    salle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("salles.id", ondelete="SET NULL"))
    periode_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("periodes.id", ondelete="SET NULL"), index=True
    )
    date_seance: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    heure_debut: Mapped[time] = mapped_column(Time, nullable=False)
    heure_fin: Mapped[time] = mapped_column(Time, nullable=False)
    statut: Mapped[StatutSeance] = mapped_column(
        Enum(StatutSeance, native_enum=False), default=StatutSeance.PLANIFIEE, nullable=False
    )
    chapitre_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chapitres.id", ondelete="SET NULL")
    )
    contenu_seance: Mapped[str | None] = mapped_column(Text)
    appel_fait: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    classe: Mapped[Classe] = relationship(lazy="selectin")
    matiere: Mapped[Matiere] = relationship(lazy="selectin")
    enseignant: Mapped[Enseignant | None] = relationship(lazy="selectin")
    presences: Mapped[list[Presence]] = relationship(
        back_populates="seance", cascade="all, delete-orphan"
    )


class Presence(Base):
    """Relevé de présence d'un apprenant à une séance."""

    __tablename__ = "presences"

    seance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("seances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    statut: Mapped[StatutPresence] = mapped_column(
        Enum(StatutPresence, native_enum=False),
        default=StatutPresence.PRESENT,
        nullable=False,
        index=True,
    )
    minutes_retard: Mapped[int] = mapped_column(default=0, nullable=False)
    justification: Mapped[str | None] = mapped_column(String(500))
    justificatif_url: Mapped[str | None] = mapped_column(String(500))
    saisi_par_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )

    seance: Mapped[Seance] = relationship(back_populates="presences")
    apprenant: Mapped[Apprenant] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("seance_id", "apprenant_id", name="uq_presences_seance_apprenant"),
    )

    @property
    def nom_complet(self) -> str | None:
        return self.apprenant.nom_complet if self.apprenant else None

    @property
    def identifiant_educatif(self) -> str | None:
        return self.apprenant.identifiant_educatif if self.apprenant else None


class SyntheseAssiduite(Base):
    """Synthèse d'assiduité d'un apprenant sur une période."""

    __tablename__ = "syntheses_assiduite"

    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    classe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    periode_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("periodes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    seances_totales: Mapped[int] = mapped_column(default=0, nullable=False)
    presences: Mapped[int] = mapped_column(default=0, nullable=False)
    absences_justifiees: Mapped[int] = mapped_column(default=0, nullable=False)
    absences_injustifiees: Mapped[int] = mapped_column(default=0, nullable=False)
    retards: Mapped[int] = mapped_column(default=0, nullable=False)
    taux_presence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    __table_args__ = (
        UniqueConstraint("apprenant_id", "classe_id", "periode_id", name="uq_syntheses_assiduite"),
    )
