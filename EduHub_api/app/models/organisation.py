"""Domaine 02 — Organisation institutionnelle.

Représente la chaîne : État → Ministère → Direction (DEC/DOB) → Direction
départementale (DDEPS) → Établissement, sous forme d'un arbre unique de
structures, conformément à l'organigramme du projet Examen et Concours.
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import NiveauScope
from app.core.mixins import CodeMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.referentiel import Departement, OrdreEnseignement


class CategorieStructure(StrEnum):
    """Nature d'un nœud de la hiérarchie institutionnelle."""

    ETAT = "ETAT"
    MINISTERE = "MINISTERE"
    DIRECTION = "DIRECTION"
    DIRECTION_EXAMENS = "DIRECTION_EXAMENS"
    DIRECTION_ORIENTATION = "DIRECTION_ORIENTATION"
    DIRECTION_DEPARTEMENTALE = "DIRECTION_DEPARTEMENTALE"
    STRUCTURE_RATTACHEE = "STRUCTURE_RATTACHEE"
    PARTENAIRE = "PARTENAIRE"
    ENTREPRISE = "ENTREPRISE"


class Structure(Base, CodeMixin, SoftDeleteMixin):
    """Nœud de la hiérarchie institutionnelle.

    - `MEMP`, `MESFTP`, `MESRS` sont des structures de catégorie `MINISTERE` ;
    - `DEC/MEMP`, `DEC/MESFTP`, `DOB` sont des directions rattachées ;
    - les `DDEPS` sont des directions départementales rattachées à une direction.
    """

    __tablename__ = "structures"

    categorie: Mapped[CategorieStructure] = mapped_column(
        Enum(CategorieStructure, native_enum=False), index=True, nullable=False
    )
    niveau_scope: Mapped[NiveauScope] = mapped_column(
        Enum(NiveauScope, native_enum=False), default=NiveauScope.MINISTERE, nullable=False
    )
    sigle: Mapped[str | None] = mapped_column(String(40), index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("structures.id", ondelete="CASCADE"), index=True
    )
    departement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departements.id", ondelete="SET NULL"), index=True
    )
    ordre_enseignement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ordres_enseignement.id", ondelete="SET NULL"), index=True
    )

    responsable_nom: Mapped[str | None] = mapped_column(String(180))
    telephone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(180))
    adresse: Mapped[str | None] = mapped_column(String(255))
    site_web: Mapped[str | None] = mapped_column(String(255))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    missions: Mapped[str | None] = mapped_column(Text)

    parent: Mapped[Structure | None] = relationship(
        remote_side="Structure.id", back_populates="enfants", lazy="selectin"
    )
    enfants: Mapped[list[Structure]] = relationship(back_populates="parent")
    departement: Mapped[Departement | None] = relationship(lazy="selectin")
    ordre_enseignement: Mapped[OrdreEnseignement | None] = relationship(lazy="selectin")

    @property
    def est_ministere(self) -> bool:
        return self.categorie == CategorieStructure.MINISTERE

    @property
    def chemin(self) -> str:
        """Chemin hiérarchique lisible, par exemple `MEMP / DEC-MEMP / DDEPS-ATL`."""
        elements: list[str] = []
        noeud: Structure | None = self
        vus: set[uuid.UUID] = set()
        while noeud is not None and noeud.id not in vus:
            vus.add(noeud.id)
            elements.append(noeud.sigle or noeud.code)
            noeud = noeud.parent
        return " / ".join(reversed(elements))
