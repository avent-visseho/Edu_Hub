"""Domaine 01 — Identité, utilisateurs, rôles et permissions."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import Action, Civilite, Langue, NiveauScope, RoleCode, Sexe, TypeHandicap
from app.core.mixins import CodeMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.etablissement import Etablissement
    from app.models.organisation import Structure


role_permission = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(Base, CodeMixin):
    """Autorisation élémentaire : une action sur une ressource."""

    __tablename__ = "permissions"

    ressource: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    action: Mapped[Action] = mapped_column(Enum(Action, native_enum=False), nullable=False)

    roles: Mapped[list[Role]] = relationship(
        secondary=role_permission, back_populates="permissions", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("ressource", "action", name="uq_permissions_ressource_action"),
    )


class Role(Base, CodeMixin):
    """Rôle métier regroupant un ensemble de permissions."""

    __tablename__ = "roles"

    niveau_scope: Mapped[NiveauScope] = mapped_column(
        Enum(NiveauScope, native_enum=False),
        default=NiveauScope.ETABLISSEMENT,
        nullable=False,
    )
    systeme: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permission, back_populates="roles", lazy="selectin"
    )
    affectations: Mapped[list[UtilisateurRole]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )

    @property
    def role_code(self) -> RoleCode | None:
        try:
            return RoleCode(self.code)
        except ValueError:
            return None


class Utilisateur(Base, SoftDeleteMixin):
    """Compte d'accès à la plateforme."""

    __tablename__ = "utilisateurs"

    # --- Authentification ---
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    mot_de_passe: Mapped[str] = mapped_column(String(255), nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verifie: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    doit_changer_mot_de_passe: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    derniere_connexion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tentatives_echouees: Mapped[int] = mapped_column(default=0, nullable=False)
    verrouille_jusqu_a: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- État civil ---
    civilite: Mapped[Civilite | None] = mapped_column(Enum(Civilite, native_enum=False))
    nom: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    prenoms: Mapped[str] = mapped_column(String(180), nullable=False)
    sexe: Mapped[Sexe | None] = mapped_column(Enum(Sexe, native_enum=False))
    date_naissance: Mapped[date | None] = mapped_column(Date)
    lieu_naissance: Mapped[str | None] = mapped_column(String(180))
    nationalite: Mapped[str] = mapped_column(String(80), default="Béninoise", nullable=False)
    telephone: Mapped[str | None] = mapped_column(String(40), index=True)
    adresse: Mapped[str | None] = mapped_column(String(255))
    photo_url: Mapped[str | None] = mapped_column(String(500))

    # --- Accessibilité et inclusion ---
    langue: Mapped[Langue] = mapped_column(
        Enum(Langue, native_enum=False), default=Langue.FR, nullable=False
    )
    type_handicap: Mapped[TypeHandicap] = mapped_column(
        Enum(TypeHandicap, native_enum=False), default=TypeHandicap.AUCUN, nullable=False
    )
    mode_simplifie: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    contraste_eleve: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    grande_police: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lecture_vocale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes_accessibilite: Mapped[str | None] = mapped_column(Text)

    # --- Relations ---
    affectations: Mapped[list[UtilisateurRole]] = relationship(
        back_populates="utilisateur",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sessions: Mapped[list[SessionUtilisateur]] = relationship(
        back_populates="utilisateur", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_utilisateurs_nom_prenoms", "nom", "prenoms"),)

    @property
    def nom_complet(self) -> str:
        return f"{self.prenoms} {self.nom}".strip()

    @property
    def codes_roles(self) -> set[str]:
        return {a.role.code for a in self.affectations if a.actif and a.role is not None}

    @property
    def est_super_admin(self) -> bool:
        return RoleCode.SUPER_ADMIN.value in self.codes_roles


class UtilisateurRole(Base):
    """Affectation d'un rôle à un utilisateur, dans une portée institutionnelle donnée."""

    __tablename__ = "utilisateur_roles"

    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    structure_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("structures.id", ondelete="CASCADE"), index=True
    )
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="CASCADE"), index=True
    )
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    debut: Mapped[date | None] = mapped_column(Date)
    fin: Mapped[date | None] = mapped_column(Date)

    utilisateur: Mapped[Utilisateur] = relationship(back_populates="affectations")
    role: Mapped[Role] = relationship(back_populates="affectations", lazy="selectin")
    structure: Mapped[Structure | None] = relationship(lazy="selectin")
    etablissement: Mapped[Etablissement | None] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "utilisateur_id",
            "role_id",
            "structure_id",
            "etablissement_id",
            name="uq_utilisateur_roles_portee",
        ),
    )


class SessionUtilisateur(Base):
    """Session d'authentification adossée à un jeton de rafraîchissement."""

    __tablename__ = "sessions_utilisateur"

    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    jeton_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    adresse_ip: Mapped[str | None] = mapped_column(String(64))
    agent_utilisateur: Mapped[str | None] = mapped_column(String(400))
    expire_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoquee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    utilisateur: Mapped[Utilisateur] = relationship(back_populates="sessions")
