"""Domaines 14 et 15 — Projets, recherche, stages et emploi."""

from __future__ import annotations

import uuid
from datetime import date
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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.apprenant import Apprenant
    from app.models.etablissement import Etablissement
    from app.models.personnel import Enseignant


# ------------------------------------------------------------------
#  Projets collaboratifs
# ------------------------------------------------------------------


class StatutProjet(StrEnum):
    IDEE = "IDEE"
    BROUILLON = "BROUILLON"
    SOUMIS = "SOUMIS"
    VALIDE = "VALIDE"
    EN_COURS = "EN_COURS"
    SUSPENDU = "SUSPENDU"
    TERMINE = "TERMINE"
    ABANDONNE = "ABANDONNE"


class RoleMembreProjet(StrEnum):
    PORTEUR = "PORTEUR"
    COORDINATEUR = "COORDINATEUR"
    MEMBRE = "MEMBRE"
    ENCADREUR = "ENCADREUR"
    MENTOR = "MENTOR"
    PARTENAIRE = "PARTENAIRE"
    OBSERVATEUR = "OBSERVATEUR"


class Projet(Base):
    """Projet collaboratif porté par des apprenants, enseignants ou partenaires."""

    __tablename__ = "projets"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    titre: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    resume: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    domaine: Mapped[str | None] = mapped_column(String(180), index=True)
    objectifs: Mapped[str | None] = mapped_column(Text)
    impact_attendu: Mapped[str | None] = mapped_column(Text)

    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    structure_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("structures.id", ondelete="SET NULL"), index=True
    )
    porteur_utilisateur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL"), index=True
    )

    statut: Mapped[StatutProjet] = mapped_column(
        Enum(StatutProjet, native_enum=False),
        default=StatutProjet.IDEE,
        nullable=False,
        index=True,
    )
    date_debut: Mapped[date | None] = mapped_column(Date)
    date_fin_prevue: Mapped[date | None] = mapped_column(Date)
    date_fin_reelle: Mapped[date | None] = mapped_column(Date)
    budget_prevu: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    budget_obtenu: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    competences_recherchees: Mapped[str | None] = mapped_column(String(500))
    places_disponibles: Mapped[int] = mapped_column(default=0, nullable=False)
    avancement_pourcentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ouvert_candidatures: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500))

    etablissement: Mapped[Etablissement | None] = relationship(lazy="selectin")
    membres: Mapped[list[MembreProjet]] = relationship(
        back_populates="projet", cascade="all, delete-orphan"
    )
    jalons: Mapped[list[JalonProjet]] = relationship(
        back_populates="projet", cascade="all, delete-orphan", order_by="JalonProjet.echeance"
    )


class MembreProjet(Base):
    """Membre d'une équipe projet."""

    __tablename__ = "membres_projet"

    projet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    utilisateur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True
    )
    apprenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True
    )
    enseignant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enseignants.id", ondelete="CASCADE"), index=True
    )
    nom_complet: Mapped[str] = mapped_column(String(180), nullable=False)
    role: Mapped[RoleMembreProjet] = mapped_column(
        Enum(RoleMembreProjet, native_enum=False), default=RoleMembreProjet.MEMBRE, nullable=False
    )
    competences: Mapped[str | None] = mapped_column(String(500))
    date_adhesion: Mapped[date | None] = mapped_column(Date)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    projet: Mapped[Projet] = relationship(back_populates="membres")


class JalonProjet(Base):
    """Jalon ou livrable d'un projet."""

    __tablename__ = "jalons_projet"

    projet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    echeance: Mapped[date] = mapped_column(Date, nullable=False)
    date_realisation: Mapped[date | None] = mapped_column(Date)
    atteint: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    livrable_url: Mapped[str | None] = mapped_column(String(500))

    projet: Mapped[Projet] = relationship(back_populates="jalons")


# ------------------------------------------------------------------
#  Recherche
# ------------------------------------------------------------------


class Laboratoire(Base):
    """Laboratoire ou unité de recherche."""

    __tablename__ = "laboratoires"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    domaines: Mapped[str | None] = mapped_column(String(500))
    directeur_nom: Mapped[str | None] = mapped_column(String(180))
    annee_creation: Mapped[int | None] = mapped_column()
    nombre_chercheurs: Mapped[int] = mapped_column(default=0, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    chercheurs: Mapped[list[Chercheur]] = relationship(back_populates="laboratoire")


class Chercheur(Base):
    """Chercheur rattaché à un laboratoire."""

    __tablename__ = "chercheurs"

    utilisateur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL"), unique=True, index=True
    )
    enseignant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enseignants.id", ondelete="SET NULL"), index=True
    )
    laboratoire_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("laboratoires.id", ondelete="SET NULL"), index=True
    )
    nom_complet: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    grade: Mapped[str | None] = mapped_column(String(120))
    specialite: Mapped[str | None] = mapped_column(String(180))
    orcid: Mapped[str | None] = mapped_column(String(64))
    indice_h: Mapped[int] = mapped_column(default=0, nullable=False)
    nombre_publications: Mapped[int] = mapped_column(default=0, nullable=False)

    laboratoire: Mapped[Laboratoire | None] = relationship(
        back_populates="chercheurs", lazy="selectin"
    )
    publications: Mapped[list[Publication]] = relationship(back_populates="auteur_principal")


class ProjetRecherche(Base):
    """Projet de recherche scientifique."""

    __tablename__ = "projets_recherche"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    titre: Mapped[str] = mapped_column(String(500), nullable=False)
    laboratoire_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("laboratoires.id", ondelete="SET NULL"), index=True
    )
    responsable_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chercheurs.id", ondelete="SET NULL"), index=True
    )
    domaine: Mapped[str | None] = mapped_column(String(180), index=True)
    resume: Mapped[str | None] = mapped_column(Text)
    date_debut: Mapped[date | None] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date)
    financement: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    bailleur: Mapped[str | None] = mapped_column(String(180))
    statut: Mapped[StatutProjet] = mapped_column(
        Enum(StatutProjet, native_enum=False), default=StatutProjet.EN_COURS, nullable=False
    )


class Publication(Base):
    """Publication scientifique : article, thèse, mémoire, communication."""

    __tablename__ = "publications"

    titre: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    type_publication: Mapped[str] = mapped_column(String(64), default="ARTICLE", nullable=False)
    auteur_principal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chercheurs.id", ondelete="SET NULL"), index=True
    )
    projet_recherche_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projets_recherche.id", ondelete="SET NULL"), index=True
    )
    co_auteurs: Mapped[str | None] = mapped_column(String(1000))
    revue: Mapped[str | None] = mapped_column(String(255))
    editeur: Mapped[str | None] = mapped_column(String(180))
    annee: Mapped[int] = mapped_column(nullable=False, index=True)
    doi: Mapped[str | None] = mapped_column(String(128), index=True)
    resume: Mapped[str | None] = mapped_column(Text)
    mots_cles: Mapped[str | None] = mapped_column(String(500))
    fichier_url: Mapped[str | None] = mapped_column(String(500))
    acces_libre: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    nombre_citations: Mapped[int] = mapped_column(default=0, nullable=False)

    auteur_principal: Mapped[Chercheur | None] = relationship(back_populates="publications")


# ------------------------------------------------------------------
#  Entreprises, stages et emploi
# ------------------------------------------------------------------


class StatutCandidature(StrEnum):
    BROUILLON = "BROUILLON"
    ENVOYEE = "ENVOYEE"
    EN_EXAMEN = "EN_EXAMEN"
    ENTRETIEN = "ENTRETIEN"
    ACCEPTEE = "ACCEPTEE"
    REFUSEE = "REFUSEE"
    RETIREE = "RETIREE"


class TypeContrat(StrEnum):
    STAGE = "STAGE"
    CDD = "CDD"
    CDI = "CDI"
    APPRENTISSAGE = "APPRENTISSAGE"
    INTERIM = "INTERIM"
    FREELANCE = "FREELANCE"
    SERVICE_CIVIQUE = "SERVICE_CIVIQUE"


class Entreprise(Base):
    """Entreprise ou organisation partenaire."""

    __tablename__ = "entreprises"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    raison_sociale: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    sigle: Mapped[str | None] = mapped_column(String(40))
    secteur_activite: Mapped[str | None] = mapped_column(String(180), index=True)
    ifu: Mapped[str | None] = mapped_column(String(64))
    commune_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communes.id", ondelete="SET NULL"), index=True
    )
    adresse: Mapped[str | None] = mapped_column(String(255))
    telephone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(180))
    site_web: Mapped[str | None] = mapped_column(String(255))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    effectif: Mapped[int | None] = mapped_column()
    contact_nom: Mapped[str | None] = mapped_column(String(180))
    utilisateur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )
    partenaire_officiel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accueille_handicap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    offres: Mapped[list[Offre]] = relationship(
        back_populates="entreprise", cascade="all, delete-orphan"
    )


class Offre(Base):
    """Offre de stage, d'emploi ou d'apprentissage."""

    __tablename__ = "offres"

    reference: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    intitule: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    entreprise_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entreprises.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type_contrat: Mapped[TypeContrat] = mapped_column(
        Enum(TypeContrat, native_enum=False),
        default=TypeContrat.STAGE,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text)
    missions: Mapped[str | None] = mapped_column(Text)
    competences_requises: Mapped[str | None] = mapped_column(String(1000))
    niveau_requis: Mapped[str | None] = mapped_column(String(120))
    domaine: Mapped[str | None] = mapped_column(String(180), index=True)
    lieu: Mapped[str | None] = mapped_column(String(180))
    commune_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communes.id", ondelete="SET NULL"), index=True
    )
    duree_mois: Mapped[int | None] = mapped_column()
    gratification: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    places: Mapped[int] = mapped_column(default=1, nullable=False)
    places_pourvues: Mapped[int] = mapped_column(default=0, nullable=False)
    date_publication: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    date_limite: Mapped[date | None] = mapped_column(Date)
    date_prise_poste: Mapped[date | None] = mapped_column(Date)
    accessible_handicap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ouverte: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    entreprise: Mapped[Entreprise] = relationship(back_populates="offres", lazy="selectin")
    candidatures: Mapped[list[CandidatureOffre]] = relationship(
        back_populates="offre", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_offres_type_ouverte", "type_contrat", "ouverte"),)


class CandidatureOffre(Base):
    """Candidature d'un apprenant à une offre."""

    __tablename__ = "candidatures_offre"

    offre_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offres.id", ondelete="CASCADE"), index=True, nullable=False
    )
    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    statut: Mapped[StatutCandidature] = mapped_column(
        Enum(StatutCandidature, native_enum=False),
        default=StatutCandidature.BROUILLON,
        nullable=False,
        index=True,
    )
    lettre_motivation: Mapped[str | None] = mapped_column(Text)
    cv_url: Mapped[str | None] = mapped_column(String(500))
    date_candidature: Mapped[date | None] = mapped_column(Date)
    date_entretien: Mapped[date | None] = mapped_column(Date)
    date_reponse: Mapped[date | None] = mapped_column(Date)
    commentaire_recruteur: Mapped[str | None] = mapped_column(Text)

    offre: Mapped[Offre] = relationship(back_populates="candidatures", lazy="selectin")
    apprenant: Mapped[Apprenant] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("offre_id", "apprenant_id", name="uq_candidatures_offre_apprenant"),
    )


class Stage(Base):
    """Stage effectué par un apprenant, de la convention à l'attestation."""

    __tablename__ = "stages"

    reference: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    entreprise_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entreprises.id", ondelete="CASCADE"), index=True, nullable=False
    )
    offre_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("offres.id", ondelete="SET NULL"))
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    encadreur_academique_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enseignants.id", ondelete="SET NULL")
    )

    sujet: Mapped[str] = mapped_column(String(500), nullable=False)
    tuteur_entreprise: Mapped[str | None] = mapped_column(String(180))
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)
    gratification: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    convention_url: Mapped[str | None] = mapped_column(String(500))
    convention_signee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rapport_url: Mapped[str | None] = mapped_column(String(500))
    note_entreprise: Mapped[float | None] = mapped_column(Float)
    note_rapport: Mapped[float | None] = mapped_column(Float)
    note_soutenance: Mapped[float | None] = mapped_column(Float)
    note_finale: Mapped[float | None] = mapped_column(Float)
    appreciation: Mapped[str | None] = mapped_column(Text)
    attestation_url: Mapped[str | None] = mapped_column(String(500))
    valide: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    apprenant: Mapped[Apprenant] = relationship(lazy="selectin")
    entreprise: Mapped[Entreprise] = relationship(lazy="selectin")
    encadreur_academique: Mapped[Enseignant | None] = relationship(lazy="selectin")


class CompetenceApprenant(Base):
    """Compétence acquise par un apprenant, alimentant son portfolio."""

    __tablename__ = "competences_apprenant"

    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    libelle: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    categorie: Mapped[str | None] = mapped_column(String(120))
    niveau: Mapped[str] = mapped_column(String(32), default="DEBUTANT", nullable=False)
    source: Mapped[str | None] = mapped_column(String(120))
    validee_par: Mapped[str | None] = mapped_column(String(180))
    date_acquisition: Mapped[date | None] = mapped_column(Date)

    apprenant: Mapped[Apprenant] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("apprenant_id", "libelle", name="uq_competences_apprenant_libelle"),
    )
