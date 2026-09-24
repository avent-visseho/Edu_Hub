"""Référentiels centralisés : découpage territorial et nomenclatures."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import TypeHandicap
from app.core.mixins import CodeMixin

if TYPE_CHECKING:
    from app.models.etablissement import Etablissement


# ------------------------------------------------------------------
#  Découpage territorial : Département > Commune > Arrondissement > Village
# ------------------------------------------------------------------


class Departement(Base, CodeMixin):
    """Département administratif (12 au Bénin)."""

    __tablename__ = "departements"

    chef_lieu: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    population: Mapped[int | None] = mapped_column()

    communes: Mapped[list[Commune]] = relationship(
        back_populates="departement", cascade="all, delete-orphan"
    )


class Commune(Base, CodeMixin):
    """Commune rattachée à un département (77 au Bénin)."""

    __tablename__ = "communes"

    departement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("departements.id", ondelete="CASCADE"), index=True, nullable=False
    )
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    population: Mapped[int | None] = mapped_column()

    departement: Mapped[Departement] = relationship(back_populates="communes", lazy="selectin")
    arrondissements: Mapped[list[Arrondissement]] = relationship(
        back_populates="commune", cascade="all, delete-orphan"
    )
    etablissements: Mapped[list[Etablissement]] = relationship(back_populates="commune")


class Arrondissement(Base, CodeMixin):
    """Arrondissement rattaché à une commune."""

    __tablename__ = "arrondissements"

    commune_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    commune: Mapped[Commune] = relationship(back_populates="arrondissements", lazy="selectin")
    villages: Mapped[list[Village]] = relationship(
        back_populates="arrondissement", cascade="all, delete-orphan"
    )


class Village(Base, CodeMixin):
    """Village ou quartier de ville."""

    __tablename__ = "villages"

    arrondissement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("arrondissements.id", ondelete="CASCADE"), index=True, nullable=False
    )
    quartier_ville: Mapped[bool] = mapped_column(default=False, nullable=False)

    arrondissement: Mapped[Arrondissement] = relationship(
        back_populates="villages", lazy="selectin"
    )


# ------------------------------------------------------------------
#  Nomenclatures
# ------------------------------------------------------------------


class OrdreEnseignement(Base, CodeMixin):
    """Ordre d'enseignement : maternel, primaire, secondaire, technique, supérieur."""

    __tablename__ = "ordres_enseignement"


class Cycle(Base, CodeMixin):
    """Cycle d'études rattaché à un ordre d'enseignement."""

    __tablename__ = "cycles"

    ordre_enseignement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ordres_enseignement.id", ondelete="SET NULL"), index=True
    )
    duree_annees: Mapped[int | None] = mapped_column()

    ordre_enseignement: Mapped[OrdreEnseignement | None] = relationship(lazy="selectin")


class TypeEtablissement(Base, CodeMixin):
    """Type d'établissement : EPP, CEG, Lycée, CFP, Université, Centre d'alphabétisation…"""

    __tablename__ = "types_etablissement"

    ordre_enseignement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ordres_enseignement.id", ondelete="SET NULL"), index=True
    )

    ordre_enseignement: Mapped[OrdreEnseignement | None] = relationship(lazy="selectin")


class StatutEtablissement(Base, CodeMixin):
    """Statut juridique : public, privé confessionnel, privé laïc, communautaire."""

    __tablename__ = "statuts_etablissement"


class TypeExamen(Base, CodeMixin):
    """Type d'examen ou de concours : CEP, BEPC, BAC, concours de recrutement…"""

    __tablename__ = "types_examen"

    est_concours: Mapped[bool] = mapped_column(default=False, nullable=False)
    ordre_enseignement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ordres_enseignement.id", ondelete="SET NULL"), index=True
    )

    ordre_enseignement: Mapped[OrdreEnseignement | None] = relationship(lazy="selectin")


class TypeSalle(Base, CodeMixin):
    """Type de salle : classe, laboratoire, salle informatique, bibliothèque…"""

    __tablename__ = "types_salle"


class TypeDocument(Base, CodeMixin):
    """Type de pièce justificative ou de document administratif."""

    __tablename__ = "types_document"

    extensions_autorisees: Mapped[str] = mapped_column(
        String(255), default="pdf,jpg,jpeg,png", nullable=False
    )
    taille_max_ko: Mapped[int] = mapped_column(default=5120, nullable=False)


class TypeBourse(Base, CodeMixin):
    """Type de bourse ou d'aide sociale."""

    __tablename__ = "types_bourse"

    montant_indicatif: Mapped[float | None] = mapped_column(Float)


class TypeFormation(Base, CodeMixin):
    """Type de formation : initiale, continue, professionnelle, alternance, alphabétisation."""

    __tablename__ = "types_formation"


class TypeHandicapRef(Base, CodeMixin):
    """Référentiel des besoins spécifiques et aménagements associés."""

    __tablename__ = "types_handicap"

    categorie: Mapped[TypeHandicap] = mapped_column(
        Enum(TypeHandicap, native_enum=False), default=TypeHandicap.AUCUN, nullable=False
    )
    amenagements: Mapped[str | None] = mapped_column(String(1000))


class Diplome(Base, CodeMixin):
    """Référentiel des diplômes délivrés par le système."""

    __tablename__ = "diplomes_referentiel"

    niveau_qualification: Mapped[str | None] = mapped_column(String(80))
    cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cycles.id", ondelete="SET NULL"), index=True
    )

    cycle: Mapped[Cycle | None] = relationship(lazy="selectin")
