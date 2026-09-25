"""Domaine 04 — Apprenants, parents et dossier scolaire."""

from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import Langue, Sexe, TypeHandicap
from app.core.mixins import SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.etablissement import Etablissement
    from app.models.identity import Utilisateur
    from app.models.referentiel import Commune
    from app.models.scolarite import Inscription


class StatutApprenant(StrEnum):
    ACTIF = "ACTIF"
    DIPLOME = "DIPLOME"
    TRANSFERE = "TRANSFERE"
    ABANDON = "ABANDON"
    EXCLU = "EXCLU"
    SUSPENDU = "SUSPENDU"


class LienParente(StrEnum):
    PERE = "PERE"
    MERE = "MERE"
    TUTEUR = "TUTEUR"
    FRERE_SOEUR = "FRERE_SOEUR"
    AUTRE = "AUTRE"


class TypeSanction(StrEnum):
    AVERTISSEMENT = "AVERTISSEMENT"
    BLAME = "BLAME"
    EXCLUSION_TEMPORAIRE = "EXCLUSION_TEMPORAIRE"
    EXCLUSION_DEFINITIVE = "EXCLUSION_DEFINITIVE"
    TRAVAIL_INTERET_GENERAL = "TRAVAIL_INTERET_GENERAL"


class TypeRecompense(StrEnum):
    FELICITATIONS = "FELICITATIONS"
    ENCOURAGEMENTS = "ENCOURAGEMENTS"
    TABLEAU_HONNEUR = "TABLEAU_HONNEUR"
    PRIX_EXCELLENCE = "PRIX_EXCELLENCE"
    PRIX_ASSIDUITE = "PRIX_ASSIDUITE"


class Apprenant(Base, SoftDeleteMixin):
    """Élève, étudiant ou apprenant — entité centrale du système.

    Porte l'identifiant éducatif national unique au format `EDU-AAAA-NNNNNN`.
    """

    __tablename__ = "apprenants"

    # --- Identifiant éducatif ---
    identifiant_educatif: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    matricule: Mapped[str | None] = mapped_column(String(64), index=True)

    utilisateur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL"), unique=True, index=True
    )

    # --- État civil ---
    nom: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    prenoms: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    sexe: Mapped[Sexe] = mapped_column(Enum(Sexe, native_enum=False), nullable=False, index=True)
    date_naissance: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    lieu_naissance: Mapped[str | None] = mapped_column(String(180))
    nationalite: Mapped[str] = mapped_column(String(80), default="Béninoise", nullable=False)
    numero_acte_naissance: Mapped[str | None] = mapped_column(String(80))

    # --- Coordonnées ---
    commune_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communes.id", ondelete="SET NULL"), index=True
    )
    adresse: Mapped[str | None] = mapped_column(String(255))
    telephone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(180))
    photo_url: Mapped[str | None] = mapped_column(String(500))

    # --- Situation ---
    etablissement_actuel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    statut: Mapped[StatutApprenant] = mapped_column(
        Enum(StatutApprenant, native_enum=False),
        default=StatutApprenant.ACTIF,
        nullable=False,
        index=True,
    )
    langue_principale: Mapped[Langue] = mapped_column(
        Enum(Langue, native_enum=False), default=Langue.FR, nullable=False
    )

    # --- Besoins spécifiques et inclusion ---
    type_handicap: Mapped[TypeHandicap] = mapped_column(
        Enum(TypeHandicap, native_enum=False),
        default=TypeHandicap.AUCUN,
        nullable=False,
        index=True,
    )
    besoins_specifiques: Mapped[str | None] = mapped_column(Text)
    amenagements_examen: Mapped[str | None] = mapped_column(Text)
    tiers_temps: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Santé et social ---
    groupe_sanguin: Mapped[str | None] = mapped_column(String(8))
    allergies: Mapped[str | None] = mapped_column(String(500))
    orphelin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    situation_vulnerable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    observations: Mapped[str | None] = mapped_column(Text)

    # --- Relations ---
    utilisateur: Mapped[Utilisateur | None] = relationship(lazy="selectin")
    commune: Mapped[Commune | None] = relationship(lazy="selectin")
    etablissement_actuel: Mapped[Etablissement | None] = relationship(lazy="selectin")
    inscriptions: Mapped[list[Inscription]] = relationship(
        back_populates="apprenant", order_by="Inscription.created_at"
    )
    parents: Mapped[list[ApprenantParent]] = relationship(
        back_populates="apprenant", cascade="all, delete-orphan"
    )
    sanctions: Mapped[list[Sanction]] = relationship(
        back_populates="apprenant", cascade="all, delete-orphan"
    )
    recompenses: Mapped[list[Recompense]] = relationship(
        back_populates="apprenant", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_apprenants_nom_prenoms", "nom", "prenoms"),
        Index("ix_apprenants_etab_statut", "etablissement_actuel_id", "statut"),
    )

    @property
    def nom_complet(self) -> str:
        return f"{self.prenoms} {self.nom}".strip()

    def age_au(self, reference: date | None = None) -> int:
        ref = reference or date.today()
        return (
            ref.year
            - self.date_naissance.year
            - ((ref.month, ref.day) < (self.date_naissance.month, self.date_naissance.day))
        )


class Parent(Base, SoftDeleteMixin):
    """Parent ou tuteur légal d'un ou plusieurs apprenants."""

    __tablename__ = "parents"

    utilisateur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL"), unique=True, index=True
    )
    nom: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    prenoms: Mapped[str] = mapped_column(String(180), nullable=False)
    sexe: Mapped[Sexe | None] = mapped_column(Enum(Sexe, native_enum=False))
    profession: Mapped[str | None] = mapped_column(String(180))
    telephone: Mapped[str | None] = mapped_column(String(40), index=True)
    telephone_secondaire: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(180))
    adresse: Mapped[str | None] = mapped_column(String(255))
    commune_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communes.id", ondelete="SET NULL")
    )
    niveau_alphabetisation: Mapped[str | None] = mapped_column(String(80))

    utilisateur: Mapped[Utilisateur | None] = relationship(lazy="selectin")
    enfants: Mapped[list[ApprenantParent]] = relationship(
        back_populates="parent", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def nom_complet(self) -> str:
        return f"{self.prenoms} {self.nom}".strip()

    @property
    def nombre_enfants(self) -> int:
        return len(self.enfants)

    @property
    def enfants_scolarises(self) -> list[dict]:
        """Enfants rattachés, avec le lien de parenté et le rôle de contact."""
        return [
            {
                "id": str(lien.apprenant_id),
                "nom_complet": lien.apprenant.nom_complet if lien.apprenant else None,
                "identifiant_educatif": (
                    lien.apprenant.identifiant_educatif if lien.apprenant else None
                ),
                "lien": lien.lien.value,
                "contact_principal": lien.contact_principal,
            }
            for lien in self.enfants
        ]


class ApprenantParent(Base):
    """Lien de parenté entre un apprenant et un parent ou tuteur."""

    __tablename__ = "apprenants_parents"

    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    parent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lien: Mapped[LienParente] = mapped_column(
        Enum(LienParente, native_enum=False), default=LienParente.TUTEUR, nullable=False
    )
    contact_principal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    autorise_sortie: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    apprenant: Mapped[Apprenant] = relationship(back_populates="parents", lazy="selectin")
    parent: Mapped[Parent] = relationship(back_populates="enfants", lazy="selectin")

    __table_args__ = (UniqueConstraint("apprenant_id", "parent_id", name="uq_apprenants_parents"),)


class Sanction(Base):
    """Sanction disciplinaire portée au dossier scolaire."""

    __tablename__ = "sanctions"

    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    annee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("annees_academiques.id", ondelete="SET NULL"), index=True
    )
    type_sanction: Mapped[TypeSanction] = mapped_column(
        Enum(TypeSanction, native_enum=False), nullable=False
    )
    motif: Mapped[str] = mapped_column(String(500), nullable=False)
    date_sanction: Mapped[date] = mapped_column(Date, nullable=False)
    duree_jours: Mapped[int | None] = mapped_column()
    prononcee_par: Mapped[str | None] = mapped_column(String(180))
    levee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    apprenant: Mapped[Apprenant] = relationship(back_populates="sanctions")


class Recompense(Base):
    """Distinction ou récompense attribuée à un apprenant."""

    __tablename__ = "recompenses"

    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    annee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("annees_academiques.id", ondelete="SET NULL"), index=True
    )
    type_recompense: Mapped[TypeRecompense] = mapped_column(
        Enum(TypeRecompense, native_enum=False), nullable=False
    )
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    motif: Mapped[str | None] = mapped_column(String(500))
    date_attribution: Mapped[date] = mapped_column(Date, nullable=False)

    apprenant: Mapped[Apprenant] = relationship(back_populates="recompenses")
