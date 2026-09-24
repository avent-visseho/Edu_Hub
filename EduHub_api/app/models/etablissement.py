"""Domaines 03 et 16 — Établissements, infrastructures et équipements."""

from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.mixins import SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.organisation import Structure
    from app.models.referentiel import (
        Commune,
        StatutEtablissement,
        TypeEtablissement,
        TypeSalle,
    )


class NiveauAccessibilite(StrEnum):
    """Degré d'accessibilité d'un lieu aux personnes en situation de handicap."""

    NON_ACCESSIBLE = "NON_ACCESSIBLE"
    PARTIELLEMENT = "PARTIELLEMENT"
    ACCESSIBLE = "ACCESSIBLE"
    ADAPTE = "ADAPTE"


class EtatEquipement(StrEnum):
    NEUF = "NEUF"
    BON = "BON"
    MOYEN = "MOYEN"
    MAUVAIS = "MAUVAIS"
    HORS_SERVICE = "HORS_SERVICE"


class TypeEquipement(StrEnum):
    ORDINATEUR = "ORDINATEUR"
    VIDEOPROJECTEUR = "VIDEOPROJECTEUR"
    TABLEAU = "TABLEAU"
    IMPRIMANTE = "IMPRIMANTE"
    MOBILIER = "MOBILIER"
    SCIENTIFIQUE = "SCIENTIFIQUE"
    SPORTIF = "SPORTIF"
    ACCESSIBILITE = "ACCESSIBILITE"
    RESEAU = "RESEAU"
    AUTRE = "AUTRE"


class Etablissement(Base, SoftDeleteMixin):
    """Établissement scolaire, universitaire ou centre de formation."""

    __tablename__ = "etablissements"

    # --- Identité ---
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    sigle: Mapped[str | None] = mapped_column(String(40))
    devise: Mapped[str | None] = mapped_column(String(255))
    logo_url: Mapped[str | None] = mapped_column(String(500))

    # --- Rattachements ---
    type_etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("types_etablissement.id", ondelete="SET NULL"), index=True
    )
    statut_etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("statuts_etablissement.id", ondelete="SET NULL"), index=True
    )
    ministere_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("structures.id", ondelete="SET NULL"), index=True
    )
    direction_departementale_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("structures.id", ondelete="SET NULL"), index=True
    )
    commune_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communes.id", ondelete="SET NULL"), index=True
    )
    arrondissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("arrondissements.id", ondelete="SET NULL"), index=True
    )

    # --- Localisation ---
    adresse: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    zone_rurale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Contacts et direction ---
    directeur_nom: Mapped[str | None] = mapped_column(String(180))
    directeur_telephone: Mapped[str | None] = mapped_column(String(40))
    telephone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(180))
    site_web: Mapped[str | None] = mapped_column(String(255))

    # --- Caractéristiques ---
    annee_creation: Mapped[int | None] = mapped_column()
    capacite_accueil: Mapped[int] = mapped_column(default=0, nullable=False)
    effectif_actuel: Mapped[int] = mapped_column(default=0, nullable=False)
    est_centre_examen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    internat: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cantine: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    electricite: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    eau_potable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    connexion_internet: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accessibilite: Mapped[NiveauAccessibilite] = mapped_column(
        Enum(NiveauAccessibilite, native_enum=False),
        default=NiveauAccessibilite.NON_ACCESSIBLE,
        nullable=False,
    )
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    observations: Mapped[str | None] = mapped_column(Text)

    # --- Relations ---
    type_etablissement: Mapped[TypeEtablissement | None] = relationship(lazy="selectin")
    statut_etablissement: Mapped[StatutEtablissement | None] = relationship(lazy="selectin")
    commune: Mapped[Commune | None] = relationship(back_populates="etablissements", lazy="selectin")
    ministere: Mapped[Structure | None] = relationship(foreign_keys=[ministere_id], lazy="selectin")
    direction_departementale: Mapped[Structure | None] = relationship(
        foreign_keys=[direction_departementale_id], lazy="selectin"
    )
    batiments: Mapped[list[Batiment]] = relationship(
        back_populates="etablissement", cascade="all, delete-orphan"
    )
    salles: Mapped[list[Salle]] = relationship(
        back_populates="etablissement", cascade="all, delete-orphan"
    )
    equipements: Mapped[list[Equipement]] = relationship(
        back_populates="etablissement", cascade="all, delete-orphan"
    )
    historique_directeurs: Mapped[list[HistoriqueDirecteur]] = relationship(
        back_populates="etablissement", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_etablissements_commune_type", "commune_id", "type_etablissement_id"),
    )


class Batiment(Base):
    """Bâtiment d'un établissement."""

    __tablename__ = "batiments"

    etablissement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("etablissements.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(180), nullable=False)
    nombre_etages: Mapped[int] = mapped_column(default=1, nullable=False)
    annee_construction: Mapped[int | None] = mapped_column()
    etat: Mapped[EtatEquipement] = mapped_column(
        Enum(EtatEquipement, native_enum=False), default=EtatEquipement.BON, nullable=False
    )
    accessibilite: Mapped[NiveauAccessibilite] = mapped_column(
        Enum(NiveauAccessibilite, native_enum=False),
        default=NiveauAccessibilite.NON_ACCESSIBLE,
        nullable=False,
    )

    etablissement: Mapped[Etablissement] = relationship(back_populates="batiments")
    salles: Mapped[list[Salle]] = relationship(
        back_populates="batiment", cascade="all, delete-orphan"
    )


class Salle(Base):
    """Salle : salle de classe, laboratoire, salle informatique, salle de composition…"""

    __tablename__ = "salles"

    etablissement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("etablissements.id", ondelete="CASCADE"), index=True, nullable=False
    )
    batiment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("batiments.id", ondelete="SET NULL"), index=True
    )
    type_salle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("types_salle.id", ondelete="SET NULL"), index=True
    )
    code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(180), nullable=False)
    etage: Mapped[int] = mapped_column(default=0, nullable=False)
    capacite: Mapped[int] = mapped_column(default=0, nullable=False)
    capacite_examen: Mapped[int] = mapped_column(default=0, nullable=False)
    superficie_m2: Mapped[float | None] = mapped_column(Float)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    accessibilite: Mapped[NiveauAccessibilite] = mapped_column(
        Enum(NiveauAccessibilite, native_enum=False),
        default=NiveauAccessibilite.NON_ACCESSIBLE,
        nullable=False,
    )
    equipement_resume: Mapped[str | None] = mapped_column(String(500))

    etablissement: Mapped[Etablissement] = relationship(back_populates="salles")
    batiment: Mapped[Batiment | None] = relationship(back_populates="salles", lazy="selectin")
    type_salle: Mapped[TypeSalle | None] = relationship(lazy="selectin")
    equipements: Mapped[list[Equipement]] = relationship(back_populates="salle")


class Equipement(Base):
    """Équipement inventorié d'un établissement."""

    __tablename__ = "equipements"

    etablissement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("etablissements.id", ondelete="CASCADE"), index=True, nullable=False
    )
    salle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("salles.id", ondelete="SET NULL"), index=True
    )
    reference: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    designation: Mapped[str] = mapped_column(String(255), nullable=False)
    type_equipement: Mapped[TypeEquipement] = mapped_column(
        Enum(TypeEquipement, native_enum=False), default=TypeEquipement.AUTRE, nullable=False
    )
    quantite: Mapped[int] = mapped_column(default=1, nullable=False)
    etat: Mapped[EtatEquipement] = mapped_column(
        Enum(EtatEquipement, native_enum=False), default=EtatEquipement.BON, nullable=False
    )
    date_acquisition: Mapped[date | None] = mapped_column(Date)
    valeur_acquisition: Mapped[float | None] = mapped_column(Float)
    derniere_maintenance: Mapped[date | None] = mapped_column(Date)
    prochaine_maintenance: Mapped[date | None] = mapped_column(Date)
    adapte_handicap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    etablissement: Mapped[Etablissement] = relationship(back_populates="equipements")
    salle: Mapped[Salle | None] = relationship(back_populates="equipements", lazy="selectin")


class HistoriqueDirecteur(Base):
    """Historique des directeurs successifs d'un établissement."""

    __tablename__ = "historique_directeurs"

    etablissement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("etablissements.id", ondelete="CASCADE"), index=True, nullable=False
    )
    nom_complet: Mapped[str] = mapped_column(String(180), nullable=False)
    matricule: Mapped[str | None] = mapped_column(String(64))
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date | None] = mapped_column(Date)
    acte_nomination: Mapped[str | None] = mapped_column(String(180))

    etablissement: Mapped[Etablissement] = relationship(back_populates="historique_directeurs")
