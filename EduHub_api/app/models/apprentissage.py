"""Domaine 13 — Ressources pédagogiques et apprentissage en ligne."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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
from app.core.enums import Langue

if TYPE_CHECKING:
    from app.models.apprenant import Apprenant
    from app.models.personnel import Enseignant
    from app.models.scolarite import Matiere, Niveau


class TypeRessource(StrEnum):
    PDF = "PDF"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    IMAGE = "IMAGE"
    PRESENTATION = "PRESENTATION"
    EXERCICE = "EXERCICE"
    QUIZ = "QUIZ"
    LIVRE = "LIVRE"
    COURS = "COURS"
    LIEN = "LIEN"
    INTERACTIF = "INTERACTIF"


class StatutPublication(StrEnum):
    BROUILLON = "BROUILLON"
    EN_RELECTURE = "EN_RELECTURE"
    PUBLIE = "PUBLIE"
    ARCHIVE = "ARCHIVE"
    RETIRE = "RETIRE"


class Cours(Base):
    """Cours en ligne structuré en modules et chapitres."""

    __tablename__ = "cours"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    titre: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    matiere_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("matieres.id", ondelete="SET NULL"), index=True
    )
    niveau_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("niveaux.id", ondelete="SET NULL"), index=True
    )
    enseignant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enseignants.id", ondelete="SET NULL"), index=True
    )
    langue: Mapped[Langue] = mapped_column(
        Enum(Langue, native_enum=False), default=Langue.FR, nullable=False
    )
    duree_heures: Mapped[int] = mapped_column(default=0, nullable=False)
    statut: Mapped[StatutPublication] = mapped_column(
        Enum(StatutPublication, native_enum=False),
        default=StatutPublication.BROUILLON,
        nullable=False,
        index=True,
    )
    image_url: Mapped[str | None] = mapped_column(String(500))
    disponible_hors_ligne: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    transcription_disponible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sous_titres_disponibles: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version_audio: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    nombre_inscrits: Mapped[int] = mapped_column(default=0, nullable=False)
    note_moyenne: Mapped[float | None] = mapped_column(Float)

    matiere: Mapped[Matiere | None] = relationship(lazy="selectin")
    niveau: Mapped[Niveau | None] = relationship(lazy="selectin")
    enseignant: Mapped[Enseignant | None] = relationship(lazy="selectin")
    modules: Mapped[list[ModuleCours]] = relationship(
        back_populates="cours", cascade="all, delete-orphan", order_by="ModuleCours.ordre"
    )


class ModuleCours(Base):
    """Module d'un cours."""

    __tablename__ = "modules_cours"

    cours_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cours.id", ondelete="CASCADE"), index=True, nullable=False
    )
    titre: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    ordre: Mapped[int] = mapped_column(default=0, nullable=False)
    duree_minutes: Mapped[int] = mapped_column(default=0, nullable=False)

    cours: Mapped[Cours] = relationship(back_populates="modules")
    lecons: Mapped[list[Lecon]] = relationship(
        back_populates="module", cascade="all, delete-orphan", order_by="Lecon.ordre"
    )


class Lecon(Base):
    """Leçon d'un module."""

    __tablename__ = "lecons"

    module_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("modules_cours.id", ondelete="CASCADE"), index=True, nullable=False
    )
    titre: Mapped[str] = mapped_column(String(255), nullable=False)
    contenu: Mapped[str | None] = mapped_column(Text)
    contenu_simplifie: Mapped[str | None] = mapped_column(Text)
    ordre: Mapped[int] = mapped_column(default=0, nullable=False)
    duree_minutes: Mapped[int] = mapped_column(default=0, nullable=False)
    audio_url: Mapped[str | None] = mapped_column(String(500))
    video_url: Mapped[str | None] = mapped_column(String(500))
    transcription: Mapped[str | None] = mapped_column(Text)

    module: Mapped[ModuleCours] = relationship(back_populates="lecons")
    ressources: Mapped[list[RessourcePedagogique]] = relationship(back_populates="lecon")


class RessourcePedagogique(Base):
    """Ressource pédagogique consultable ou téléchargeable."""

    __tablename__ = "ressources_pedagogiques"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    titre: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    type_ressource: Mapped[TypeRessource] = mapped_column(
        Enum(TypeRessource, native_enum=False), nullable=False, index=True
    )
    lecon_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lecons.id", ondelete="SET NULL"), index=True
    )
    matiere_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("matieres.id", ondelete="SET NULL"), index=True
    )
    niveau_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("niveaux.id", ondelete="SET NULL"), index=True
    )
    auteur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )
    fichier_url: Mapped[str | None] = mapped_column(String(500))
    taille_ko: Mapped[int] = mapped_column(default=0, nullable=False)
    duree_secondes: Mapped[int | None] = mapped_column()
    langue: Mapped[Langue] = mapped_column(
        Enum(Langue, native_enum=False), default=Langue.FR, nullable=False
    )
    statut: Mapped[StatutPublication] = mapped_column(
        Enum(StatutPublication, native_enum=False),
        default=StatutPublication.PUBLIE,
        nullable=False,
    )
    licence: Mapped[str | None] = mapped_column(String(120))
    mots_cles: Mapped[str | None] = mapped_column(String(500))
    nombre_vues: Mapped[int] = mapped_column(default=0, nullable=False)
    nombre_telechargements: Mapped[int] = mapped_column(default=0, nullable=False)
    poids_leger: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    lecon: Mapped[Lecon | None] = relationship(back_populates="ressources")
    matiere: Mapped[Matiere | None] = relationship(lazy="selectin")

    __table_args__ = (Index("ix_ressources_matiere_type", "matiere_id", "type_ressource"),)


class Quiz(Base):
    """Quiz d'auto-évaluation rattaché à une leçon ou à une matière."""

    __tablename__ = "quiz"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    titre: Mapped[str] = mapped_column(String(255), nullable=False)
    lecon_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lecons.id", ondelete="CASCADE"), index=True
    )
    matiere_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("matieres.id", ondelete="SET NULL"), index=True
    )
    niveau_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("niveaux.id", ondelete="SET NULL")
    )
    duree_minutes: Mapped[int] = mapped_column(default=10, nullable=False)
    note_passage: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    tentatives_max: Mapped[int] = mapped_column(default=3, nullable=False)
    aleatoire: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    questions: Mapped[list[QuestionQuiz]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan", order_by="QuestionQuiz.ordre"
    )


class QuestionQuiz(Base):
    """Question d'un quiz."""

    __tablename__ = "questions_quiz"

    quiz_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quiz.id", ondelete="CASCADE"), index=True, nullable=False
    )
    enonce: Mapped[str] = mapped_column(Text, nullable=False)
    type_question: Mapped[str] = mapped_column(String(32), default="CHOIX_UNIQUE", nullable=False)
    propositions: Mapped[str | None] = mapped_column(Text)
    reponse_correcte: Mapped[str] = mapped_column(String(500), nullable=False)
    explication: Mapped[str | None] = mapped_column(Text)
    points: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    ordre: Mapped[int] = mapped_column(default=0, nullable=False)
    audio_url: Mapped[str | None] = mapped_column(String(500))

    quiz: Mapped[Quiz] = relationship(back_populates="questions")


class ProgressionApprentissage(Base):
    """Progression d'un apprenant dans un cours."""

    __tablename__ = "progressions_apprentissage"

    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    cours_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cours.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lecons_terminees: Mapped[int] = mapped_column(default=0, nullable=False)
    lecons_totales: Mapped[int] = mapped_column(default=0, nullable=False)
    pourcentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    temps_passe_minutes: Mapped[int] = mapped_column(default=0, nullable=False)
    derniere_activite: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    termine: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note_finale: Mapped[float | None] = mapped_column(Float)
    certificat_delivre: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    apprenant: Mapped[Apprenant] = relationship(lazy="selectin")
    cours: Mapped[Cours] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("apprenant_id", "cours_id", name="uq_progressions_apprenant_cours"),
    )


class TentativeQuiz(Base):
    """Tentative d'un apprenant sur un quiz."""

    __tablename__ = "tentatives_quiz"

    quiz_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quiz.id", ondelete="CASCADE"), index=True, nullable=False
    )
    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    numero_tentative: Mapped[int] = mapped_column(default=1, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    score_max: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reussi: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duree_secondes: Mapped[int] = mapped_column(default=0, nullable=False)
    reponses: Mapped[str | None] = mapped_column(Text)
    termine_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CentreAlphabetisation(Base):
    """Centre d'alphabétisation et d'éducation non formelle."""

    __tablename__ = "centres_alphabetisation"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    commune_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communes.id", ondelete="SET NULL"), index=True
    )
    langue_enseignement: Mapped[Langue] = mapped_column(
        Enum(Langue, native_enum=False), default=Langue.FON, nullable=False
    )
    responsable: Mapped[str | None] = mapped_column(String(180))
    telephone: Mapped[str | None] = mapped_column(String(40))
    nombre_formateurs: Mapped[int] = mapped_column(default=0, nullable=False)
    nombre_apprenants: Mapped[int] = mapped_column(default=0, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ParcoursAlphabetisation(Base):
    """Parcours d'un apprenant en alphabétisation."""

    __tablename__ = "parcours_alphabetisation"

    centre_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("centres_alphabetisation.id", ondelete="CASCADE"), index=True, nullable=False
    )
    apprenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("apprenants.id", ondelete="SET NULL"), index=True
    )
    nom_complet: Mapped[str] = mapped_column(String(180), nullable=False)
    age: Mapped[int | None] = mapped_column()
    langue: Mapped[Langue] = mapped_column(
        Enum(Langue, native_enum=False), default=Langue.FON, nullable=False
    )
    niveau_initial: Mapped[str] = mapped_column(String(64), default="DEBUTANT", nullable=False)
    niveau_atteint: Mapped[str | None] = mapped_column(String(64))
    progression_pourcentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    certifie: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
