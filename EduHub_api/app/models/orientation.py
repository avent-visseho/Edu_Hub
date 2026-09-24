"""Domaine 11 — Orientation, formations et affectation post-examen."""

from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.apprenant import Apprenant
    from app.models.etablissement import Etablissement
    from app.models.referentiel import Diplome
    from app.models.scolarite import Filiere, Serie


class StatutVoeu(StrEnum):
    BROUILLON = "BROUILLON"
    SOUMIS = "SOUMIS"
    EN_ETUDE = "EN_ETUDE"
    ACCEPTE = "ACCEPTE"
    LISTE_ATTENTE = "LISTE_ATTENTE"
    REFUSE = "REFUSE"
    DESISTE = "DESISTE"


class Formation(Base):
    """Formation proposée par un établissement."""

    __tablename__ = "formations"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    intitule: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="CASCADE"), index=True
    )
    filiere_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("filieres.id", ondelete="SET NULL"), index=True
    )
    diplome_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("diplomes_referentiel.id", ondelete="SET NULL"), index=True
    )
    type_formation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("types_formation.id", ondelete="SET NULL")
    )
    niveau_entree: Mapped[str | None] = mapped_column(String(120))
    duree_annees: Mapped[int] = mapped_column(default=3, nullable=False)
    credits_total: Mapped[int | None] = mapped_column()
    places_offertes: Mapped[int] = mapped_column(default=0, nullable=False)
    places_pourvues: Mapped[int] = mapped_column(default=0, nullable=False)
    moyenne_minimale: Mapped[float | None] = mapped_column(Float)
    series_admises: Mapped[str | None] = mapped_column(String(255))
    conditions: Mapped[str | None] = mapped_column(Text)
    competences_visees: Mapped[str | None] = mapped_column(Text)
    debouches: Mapped[str | None] = mapped_column(Text)
    frais_annuels: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ouverte: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    etablissement: Mapped[Etablissement | None] = relationship(lazy="selectin")
    filiere: Mapped[Filiere | None] = relationship(lazy="selectin")
    diplome: Mapped[Diplome | None] = relationship(lazy="selectin")


class CampagneOrientation(Base):
    """Campagne d'orientation ouverte pour une année donnée."""

    __tablename__ = "campagnes_orientation"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    annee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("annees_academiques.id", ondelete="SET NULL"), index=True
    )
    date_ouverture: Mapped[date] = mapped_column(Date, nullable=False)
    date_fermeture: Mapped[date] = mapped_column(Date, nullable=False)
    date_resultats: Mapped[date | None] = mapped_column(Date)
    nombre_voeux_max: Mapped[int] = mapped_column(default=5, nullable=False)
    ouverte: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DossierOrientation(Base):
    """Dossier d'orientation d'un apprenant pour une campagne."""

    __tablename__ = "dossiers_orientation"

    campagne_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campagnes_orientation.id", ondelete="CASCADE"), index=True, nullable=False
    )
    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    serie_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("series.id", ondelete="SET NULL"))
    moyenne_bac: Mapped[float | None] = mapped_column(Float)
    mention: Mapped[str | None] = mapped_column(String(64))
    profil_detecte: Mapped[str | None] = mapped_column(String(255))
    formation_affectee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("formations.id", ondelete="SET NULL"), index=True
    )
    date_affectation: Mapped[date | None] = mapped_column(Date)
    statut: Mapped[StatutVoeu] = mapped_column(
        Enum(StatutVoeu, native_enum=False), default=StatutVoeu.BROUILLON, nullable=False
    )

    apprenant: Mapped[Apprenant] = relationship(lazy="selectin")
    serie: Mapped[Serie | None] = relationship(lazy="selectin")
    formation_affectee: Mapped[Formation | None] = relationship(lazy="selectin")
    voeux: Mapped[list[VoeuOrientation]] = relationship(
        back_populates="dossier", cascade="all, delete-orphan", order_by="VoeuOrientation.rang"
    )

    __table_args__ = (
        UniqueConstraint("campagne_id", "apprenant_id", name="uq_dossiers_orientation"),
    )


class VoeuOrientation(Base):
    """Vœu formulé par un apprenant, classé par ordre de préférence."""

    __tablename__ = "voeux_orientation"

    dossier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dossiers_orientation.id", ondelete="CASCADE"), index=True, nullable=False
    )
    formation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("formations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rang: Mapped[int] = mapped_column(default=1, nullable=False)
    statut: Mapped[StatutVoeu] = mapped_column(
        Enum(StatutVoeu, native_enum=False), default=StatutVoeu.SOUMIS, nullable=False
    )
    rang_liste_attente: Mapped[int | None] = mapped_column()
    motif: Mapped[str | None] = mapped_column(String(500))

    dossier: Mapped[DossierOrientation] = relationship(back_populates="voeux")
    formation: Mapped[Formation] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("dossier_id", "formation_id", name="uq_voeux_dossier_formation"),
    )
