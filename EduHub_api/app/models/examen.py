"""Domaine 09 — Examens et concours.

Couvre l'intégralité de la chaîne décrite dans les documents de référence :
création de l'examen, sessions, séries, matières, pièces jointes, candidatures,
étude des dossiers, répartition des candidats, centres et salles de composition,
surveillants, chefs de centre, correcteurs, copies, saisie des notes, calcul des
moyennes, jurys et délibérations, résultats, contentieux, budget et archives.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
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
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import Sexe, StatutPaiement, TypeHandicap

if TYPE_CHECKING:
    from app.models.apprenant import Apprenant
    from app.models.etablissement import Etablissement, Salle
    from app.models.organisation import Structure
    from app.models.personnel import Enseignant
    from app.models.referentiel import Commune, Departement, TypeDocument, TypeExamen
    from app.models.scolarite import Matiere, Serie


# ------------------------------------------------------------------
#  Énumérations
# ------------------------------------------------------------------


class NatureExamen(StrEnum):
    EXAMEN = "EXAMEN"
    CONCOURS = "CONCOURS"
    CERTIFICATION = "CERTIFICATION"
    EXAMEN_BLANC = "EXAMEN_BLANC"


class TypeSession(StrEnum):
    NORMALE = "NORMALE"
    RATTRAPAGE = "RATTRAPAGE"
    SPECIALE = "SPECIALE"
    ANTICIPEE = "ANTICIPEE"


class StatutSession(StrEnum):
    PREPARATION = "PREPARATION"
    INSCRIPTIONS_OUVERTES = "INSCRIPTIONS_OUVERTES"
    INSCRIPTIONS_CLOSES = "INSCRIPTIONS_CLOSES"
    ETUDE_DOSSIERS = "ETUDE_DOSSIERS"
    REPARTITION = "REPARTITION"
    CONVOCATIONS_EMISES = "CONVOCATIONS_EMISES"
    EN_COURS = "EN_COURS"
    CORRECTION = "CORRECTION"
    DELIBERATION = "DELIBERATION"
    RESULTATS_PUBLIES = "RESULTATS_PUBLIES"
    CLOTUREE = "CLOTUREE"
    ARCHIVEE = "ARCHIVEE"


class StatutDossier(StrEnum):
    """Cycle de vie du dossier d'un candidat."""

    BROUILLON = "BROUILLON"
    SOUMIS = "SOUMIS"
    EN_ETUDE = "EN_ETUDE"
    INCOMPLET = "INCOMPLET"
    REJETE = "REJETE"
    VALIDE = "VALIDE"
    CONVOQUE = "CONVOQUE"
    COMPOSE = "COMPOSE"
    CORRIGE = "CORRIGE"
    ADMIS = "ADMIS"
    NON_ADMIS = "NON_ADMIS"


class TypeCandidature(StrEnum):
    OFFICIEL = "OFFICIEL"
    LIBRE = "LIBRE"
    REDOUBLANT = "REDOUBLANT"
    TRANSFERT = "TRANSFERT"


class StatutPiece(StrEnum):
    EN_ATTENTE = "EN_ATTENTE"
    VALIDEE = "VALIDEE"
    REJETEE = "REJETEE"
    A_CORRIGER = "A_CORRIGER"


class MotifRejetPiece(StrEnum):
    ILLISIBLE = "ILLISIBLE"
    INCORRECT = "INCORRECT"
    EXPIRE = "EXPIRE"
    MAUVAIS_FORMAT = "MAUVAIS_FORMAT"
    MANQUANT = "MANQUANT"
    NON_CONFORME = "NON_CONFORME"


class StatutNoteExamen(StrEnum):
    SAISIE = "SAISIE"
    ABSENT = "ABSENT"
    COPIE_ABSENTE = "COPIE_ABSENTE"
    NOTE_ELIMINATOIRE = "NOTE_ELIMINATOIRE"
    FRAUDE = "FRAUDE"
    DISPENSE = "DISPENSE"


class DecisionExamen(StrEnum):
    ADMIS = "ADMIS"
    ADMISSIBLE = "ADMISSIBLE"
    AJOURNE = "AJOURNE"
    NON_ADMIS = "NON_ADMIS"
    ABSENT = "ABSENT"
    EXCLU = "EXCLU"
    EN_ATTENTE = "EN_ATTENTE"


class RoleSurveillance(StrEnum):
    CHEF_CENTRE = "CHEF_CENTRE"
    CHEF_CENTRE_ADJOINT = "CHEF_CENTRE_ADJOINT"
    SECRETAIRE = "SECRETAIRE"
    SURVEILLANT = "SURVEILLANT"
    SURVEILLANT_GENERAL = "SURVEILLANT_GENERAL"
    OPERATEUR_SAISIE = "OPERATEUR_SAISIE"
    PERSONNEL_SOUTIEN = "PERSONNEL_SOUTIEN"
    SECURITE = "SECURITE"
    SANTE = "SANTE"


class StatutProposition(StrEnum):
    PROPOSEE = "PROPOSEE"
    RETENUE = "RETENUE"
    REJETEE = "REJETEE"
    REMPLACEE = "REMPLACEE"


class StatutContentieux(StrEnum):
    DEPOSEE = "DEPOSEE"
    RECEVABLE = "RECEVABLE"
    IRRECEVABLE = "IRRECEVABLE"
    EN_INSTRUCTION = "EN_INSTRUCTION"
    TRANCHEE_FAVORABLE = "TRANCHEE_FAVORABLE"
    TRANCHEE_DEFAVORABLE = "TRANCHEE_DEFAVORABLE"
    CLOTUREE = "CLOTUREE"


class TypeContentieux(StrEnum):
    ERREUR_NOTE = "ERREUR_NOTE"
    ERREUR_IDENTITE = "ERREUR_IDENTITE"
    COPIE_NON_CORRIGEE = "COPIE_NON_CORRIGEE"
    ABSENCE_INJUSTIFIEE = "ABSENCE_INJUSTIFIEE"
    FRAUDE_CONTESTEE = "FRAUDE_CONTESTEE"
    DOSSIER_REJETE = "DOSSIER_REJETE"
    AUTRE = "AUTRE"


class TypeConvocation(StrEnum):
    CANDIDAT = "CANDIDAT"
    SURVEILLANT = "SURVEILLANT"
    CORRECTEUR = "CORRECTEUR"
    CHEF_CENTRE = "CHEF_CENTRE"
    MEMBRE_JURY = "MEMBRE_JURY"
    OPERATEUR_SAISIE = "OPERATEUR_SAISIE"


# ------------------------------------------------------------------
#  Configuration de l'examen
# ------------------------------------------------------------------


class Examen(Base):
    """Examen ou concours au niveau national (CEP, BEPC, BAC, concours…)."""

    __tablename__ = "examens"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    sigle: Mapped[str | None] = mapped_column(String(32))
    nature: Mapped[NatureExamen] = mapped_column(
        Enum(NatureExamen, native_enum=False),
        default=NatureExamen.EXAMEN,
        nullable=False,
        index=True,
    )
    type_examen_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("types_examen.id", ondelete="SET NULL"), index=True
    )
    ministere_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("structures.id", ondelete="SET NULL"), index=True
    )
    direction_responsable_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("structures.id", ondelete="SET NULL"), index=True
    )
    niveau_requis_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("niveaux.id", ondelete="SET NULL")
    )
    diplome_delivre_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("diplomes_referentiel.id", ondelete="SET NULL")
    )

    conditions_admission: Mapped[str | None] = mapped_column(Text)
    reglement: Mapped[str | None] = mapped_column(Text)
    frais_officiel: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    frais_candidat_libre: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    age_minimum: Mapped[int | None] = mapped_column()
    age_maximum: Mapped[int | None] = mapped_column()
    moyenne_admission: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    note_eliminatoire: Mapped[float | None] = mapped_column(Float)
    places_offertes: Mapped[int | None] = mapped_column()
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    type_examen: Mapped[TypeExamen | None] = relationship(lazy="selectin")
    ministere: Mapped[Structure | None] = relationship(foreign_keys=[ministere_id], lazy="selectin")
    direction_responsable: Mapped[Structure | None] = relationship(
        foreign_keys=[direction_responsable_id], lazy="selectin"
    )
    sessions: Mapped[list[SessionExamen]] = relationship(
        back_populates="examen", cascade="all, delete-orphan"
    )
    regles_mention: Mapped[list[RegleMention]] = relationship(
        back_populates="examen", cascade="all, delete-orphan", order_by="RegleMention.seuil_min"
    )


class RegleMention(Base):
    """Règle d'attribution des mentions, configurable par examen."""

    __tablename__ = "regles_mention"

    examen_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("examens.id", ondelete="CASCADE"), index=True, nullable=False
    )
    libelle: Mapped[str] = mapped_column(String(64), nullable=False)
    seuil_min: Mapped[float] = mapped_column(Float, nullable=False)
    seuil_max: Mapped[float] = mapped_column(Float, default=20.0, nullable=False)
    ordre: Mapped[int] = mapped_column(default=0, nullable=False)

    examen: Mapped[Examen] = relationship(back_populates="regles_mention")


class SessionExamen(Base):
    """Occurrence datée d'un examen, par exemple « BEPC 2027 — session normale »."""

    __tablename__ = "sessions_examen"

    examen_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("examens.id", ondelete="CASCADE"), index=True, nullable=False
    )
    annee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("annees_academiques.id", ondelete="SET NULL"), index=True
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    type_session: Mapped[TypeSession] = mapped_column(
        Enum(TypeSession, native_enum=False), default=TypeSession.NORMALE, nullable=False
    )
    annee: Mapped[int] = mapped_column(nullable=False, index=True)
    statut: Mapped[StatutSession] = mapped_column(
        Enum(StatutSession, native_enum=False),
        default=StatutSession.PREPARATION,
        nullable=False,
        index=True,
    )

    inscriptions_debut: Mapped[date | None] = mapped_column(Date)
    inscriptions_fin: Mapped[date | None] = mapped_column(Date)
    date_debut: Mapped[date | None] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date)
    date_publication_resultats: Mapped[date | None] = mapped_column(Date)
    date_limite_contentieux: Mapped[date | None] = mapped_column(Date)

    # --- Statistiques consolidées ---
    nombre_inscrits: Mapped[int] = mapped_column(default=0, nullable=False)
    nombre_presents: Mapped[int] = mapped_column(default=0, nullable=False)
    nombre_absents: Mapped[int] = mapped_column(default=0, nullable=False)
    nombre_admis: Mapped[int] = mapped_column(default=0, nullable=False)
    taux_reussite: Mapped[float | None] = mapped_column(Float)
    moyenne_generale: Mapped[float | None] = mapped_column(Float)

    resultats_publies_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observations: Mapped[str | None] = mapped_column(Text)

    examen: Mapped[Examen] = relationship(back_populates="sessions", lazy="selectin")
    series: Mapped[list[SerieExamen]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    epreuves: Mapped[list[EpreuveExamen]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    pieces_requises: Mapped[list[PieceRequise]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    candidats: Mapped[list[Candidat]] = relationship(back_populates="session")
    centres: Mapped[list[CentreComposition]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class SerieExamen(Base):
    """Série ouverte pour une session donnée."""

    __tablename__ = "series_examen"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    serie_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("series.id", ondelete="CASCADE"), index=True, nullable=False
    )
    places: Mapped[int | None] = mapped_column()
    moyenne_admission: Mapped[float | None] = mapped_column(Float)
    ouverte: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    session: Mapped[SessionExamen] = relationship(back_populates="series")
    serie: Mapped[Serie] = relationship(lazy="selectin")

    __table_args__ = (UniqueConstraint("session_id", "serie_id", name="uq_series_examen"),)


class EpreuveExamen(Base):
    """Épreuve d'une session : matière, série, date, durée, barème, coefficient."""

    __tablename__ = "epreuves_examen"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    serie_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("series.id", ondelete="CASCADE"), index=True
    )
    matiere_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matieres.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    date_epreuve: Mapped[date | None] = mapped_column(Date, index=True)
    heure_debut: Mapped[time | None] = mapped_column(Time)
    duree_minutes: Mapped[int] = mapped_column(default=120, nullable=False)
    bareme: Mapped[float] = mapped_column(Float, default=20.0, nullable=False)
    coefficient: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    note_eliminatoire: Mapped[float | None] = mapped_column(Float)
    obligatoire: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    facultative: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pratique: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    orale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sujet_url: Mapped[str | None] = mapped_column(String(500))
    corrige_url: Mapped[str | None] = mapped_column(String(500))
    instructions: Mapped[str | None] = mapped_column(Text)

    session: Mapped[SessionExamen] = relationship(back_populates="epreuves", lazy="selectin")
    matiere: Mapped[Matiere] = relationship(lazy="selectin")
    serie: Mapped[Serie | None] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("session_id", "serie_id", "matiere_id", name="uq_epreuves_examen"),
    )


class PieceRequise(Base):
    """Pièce justificative exigée pour une candidature."""

    __tablename__ = "pieces_requises"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("types_document.id", ondelete="CASCADE"), index=True, nullable=False
    )
    serie_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("series.id", ondelete="CASCADE"))
    type_candidature: Mapped[TypeCandidature | None] = mapped_column(
        Enum(TypeCandidature, native_enum=False)
    )
    obligatoire: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    consignes: Mapped[str | None] = mapped_column(String(500))
    ordre: Mapped[int] = mapped_column(default=0, nullable=False)

    session: Mapped[SessionExamen] = relationship(back_populates="pieces_requises")
    type_document: Mapped[TypeDocument] = relationship(lazy="selectin")


# ------------------------------------------------------------------
#  Candidatures et dossiers
# ------------------------------------------------------------------


class Candidat(Base):
    """Candidature d'une personne à une session d'examen ou de concours."""

    __tablename__ = "candidats"

    numero_candidat: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    numero_table: Mapped[str | None] = mapped_column(String(32), index=True)

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    serie_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("series.id", ondelete="SET NULL"), index=True
    )
    apprenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("apprenants.id", ondelete="SET NULL"), index=True
    )
    utilisateur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL"), index=True
    )
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    departement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departements.id", ondelete="SET NULL"), index=True
    )

    # --- État civil (dénormalisé : un candidat libre n'est pas un apprenant) ---
    nom: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    prenoms: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    sexe: Mapped[Sexe] = mapped_column(Enum(Sexe, native_enum=False), nullable=False)
    date_naissance: Mapped[date] = mapped_column(Date, nullable=False)
    lieu_naissance: Mapped[str | None] = mapped_column(String(180))
    nationalite: Mapped[str] = mapped_column(String(80), default="Béninoise", nullable=False)
    telephone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(180))
    photo_url: Mapped[str | None] = mapped_column(String(500))

    # --- Candidature ---
    type_candidature: Mapped[TypeCandidature] = mapped_column(
        Enum(TypeCandidature, native_enum=False),
        default=TypeCandidature.OFFICIEL,
        nullable=False,
        index=True,
    )
    statut_dossier: Mapped[StatutDossier] = mapped_column(
        Enum(StatutDossier, native_enum=False),
        default=StatutDossier.BROUILLON,
        nullable=False,
        index=True,
    )
    date_soumission: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    date_validation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valide_par_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )
    motif_rejet: Mapped[str | None] = mapped_column(String(1000))

    # --- Frais ---
    montant_frais: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    statut_paiement: Mapped[StatutPaiement] = mapped_column(
        Enum(StatutPaiement, native_enum=False), default=StatutPaiement.PENDING, nullable=False
    )
    reference_paiement: Mapped[str | None] = mapped_column(String(80))
    date_paiement: Mapped[date | None] = mapped_column(Date)

    # --- Affectation ---
    centre_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("centres_composition.id", ondelete="SET NULL"), index=True
    )
    salle_composition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("salles_composition.id", ondelete="SET NULL"), index=True
    )
    numero_place: Mapped[int | None] = mapped_column()

    # --- Inclusion ---
    type_handicap: Mapped[TypeHandicap] = mapped_column(
        Enum(TypeHandicap, native_enum=False), default=TypeHandicap.AUCUN, nullable=False
    )
    amenagements_demandes: Mapped[str | None] = mapped_column(Text)
    tiers_temps: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accompagnateur_requis: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    observations: Mapped[str | None] = mapped_column(Text)

    session: Mapped[SessionExamen] = relationship(back_populates="candidats", lazy="selectin")
    serie: Mapped[Serie | None] = relationship(lazy="selectin")
    apprenant: Mapped[Apprenant | None] = relationship(lazy="selectin")
    etablissement: Mapped[Etablissement | None] = relationship(lazy="selectin")
    departement: Mapped[Departement | None] = relationship(lazy="selectin")
    centre: Mapped[CentreComposition | None] = relationship(
        back_populates="candidats", lazy="selectin"
    )
    salle_composition: Mapped[SalleComposition | None] = relationship(
        back_populates="candidats", lazy="selectin"
    )
    documents: Mapped[list[DocumentCandidat]] = relationship(
        back_populates="candidat", cascade="all, delete-orphan"
    )
    notes: Mapped[list[NoteExamen]] = relationship(
        back_populates="candidat", cascade="all, delete-orphan"
    )
    resultat: Mapped[ResultatExamen | None] = relationship(
        back_populates="candidat", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        UniqueConstraint("session_id", "numero_table", name="uq_candidats_session_table"),
        Index("ix_candidats_session_statut", "session_id", "statut_dossier"),
        Index("ix_candidats_nom_prenoms", "nom", "prenoms"),
    )

    @property
    def nom_complet(self) -> str:
        return f"{self.prenoms} {self.nom}".strip()


class DocumentCandidat(Base):
    """Pièce jointe déposée par un candidat, avec son cycle de validation."""

    __tablename__ = "documents_candidat"

    candidat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidats.id", ondelete="CASCADE"), index=True, nullable=False
    )
    piece_requise_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pieces_requises.id", ondelete="SET NULL"), index=True
    )
    type_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("types_document.id", ondelete="SET NULL"), index=True
    )

    nom_fichier: Mapped[str] = mapped_column(String(255), nullable=False)
    chemin_stockage: Mapped[str] = mapped_column(String(500), nullable=False)
    type_mime: Mapped[str | None] = mapped_column(String(120))
    taille_octets: Mapped[int] = mapped_column(default=0, nullable=False)
    empreinte: Mapped[str | None] = mapped_column(String(128))
    version: Mapped[int] = mapped_column(default=1, nullable=False)

    statut: Mapped[StatutPiece] = mapped_column(
        Enum(StatutPiece, native_enum=False),
        default=StatutPiece.EN_ATTENTE,
        nullable=False,
        index=True,
    )
    motif_rejet: Mapped[MotifRejetPiece | None] = mapped_column(
        Enum(MotifRejetPiece, native_enum=False)
    )
    commentaire: Mapped[str | None] = mapped_column(String(1000))
    verifie_par_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )
    verifie_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    candidat: Mapped[Candidat] = relationship(back_populates="documents")
    type_document: Mapped[TypeDocument | None] = relationship(lazy="selectin")


# ------------------------------------------------------------------
#  Centres, salles et répartition
# ------------------------------------------------------------------


class CentreComposition(Base):
    """Centre de composition d'une session d'examen."""

    __tablename__ = "centres_composition"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    departement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departements.id", ondelete="SET NULL"), index=True
    )
    commune_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communes.id", ondelete="SET NULL"), index=True
    )

    code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    adresse: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    capacite: Mapped[int] = mapped_column(default=0, nullable=False)
    nombre_candidats: Mapped[int] = mapped_column(default=0, nullable=False)
    nombre_salles: Mapped[int] = mapped_column(default=0, nullable=False)

    chef_centre_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enseignants.id", ondelete="SET NULL")
    )
    chef_centre_nom: Mapped[str | None] = mapped_column(String(180))
    chef_centre_telephone: Mapped[str | None] = mapped_column(String(40))
    accessible_handicap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    observations: Mapped[str | None] = mapped_column(Text)

    session: Mapped[SessionExamen] = relationship(back_populates="centres", lazy="selectin")
    etablissement: Mapped[Etablissement | None] = relationship(lazy="selectin")
    departement: Mapped[Departement | None] = relationship(lazy="selectin")
    commune: Mapped[Commune | None] = relationship(lazy="selectin")
    salles: Mapped[list[SalleComposition]] = relationship(
        back_populates="centre", cascade="all, delete-orphan"
    )
    candidats: Mapped[list[Candidat]] = relationship(back_populates="centre")
    affectations: Mapped[list[AffectationSurveillance]] = relationship(
        back_populates="centre", cascade="all, delete-orphan"
    )
    incidents: Mapped[list[IncidentExamen]] = relationship(
        back_populates="centre", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("session_id", "code", name="uq_centres_session_code"),)


class SalleComposition(Base):
    """Salle de composition rattachée à un centre."""

    __tablename__ = "salles_composition"

    centre_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("centres_composition.id", ondelete="CASCADE"), index=True, nullable=False
    )
    salle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("salles.id", ondelete="SET NULL"), index=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    nom: Mapped[str] = mapped_column(String(180), nullable=False)
    batiment: Mapped[str | None] = mapped_column(String(120))
    capacite: Mapped[int] = mapped_column(default=30, nullable=False)
    nombre_candidats: Mapped[int] = mapped_column(default=0, nullable=False)
    place_debut: Mapped[int | None] = mapped_column()
    place_fin: Mapped[int | None] = mapped_column()
    accessible_handicap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    salle_amenagee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    centre: Mapped[CentreComposition] = relationship(back_populates="salles", lazy="selectin")
    salle: Mapped[Salle | None] = relationship(lazy="selectin")
    candidats: Mapped[list[Candidat]] = relationship(back_populates="salle_composition")

    __table_args__ = (UniqueConstraint("centre_id", "code", name="uq_salles_composition_code"),)


# ------------------------------------------------------------------
#  Personnels d'examen
# ------------------------------------------------------------------


class PropositionPersonnel(Base):
    """Proposition d'un établissement pour un rôle d'examen.

    Les établissements proposent surveillants, correcteurs et opérateurs de
    saisie ; la direction des examens retient ou rejette chaque proposition.
    """

    __tablename__ = "propositions_personnel"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    etablissement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("etablissements.id", ondelete="CASCADE"), index=True, nullable=False
    )
    enseignant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enseignants.id", ondelete="SET NULL"), index=True
    )
    personnel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("personnels.id", ondelete="SET NULL"), index=True
    )
    role_propose: Mapped[RoleSurveillance] = mapped_column(
        Enum(RoleSurveillance, native_enum=False), nullable=False, index=True
    )
    matiere_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("matieres.id", ondelete="SET NULL")
    )
    nom_complet: Mapped[str] = mapped_column(String(180), nullable=False)
    telephone: Mapped[str | None] = mapped_column(String(40))
    statut: Mapped[StatutProposition] = mapped_column(
        Enum(StatutProposition, native_enum=False),
        default=StatutProposition.PROPOSEE,
        nullable=False,
        index=True,
    )
    motif_rejet: Mapped[str | None] = mapped_column(String(500))
    decide_par_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )
    decide_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    enseignant: Mapped[Enseignant | None] = relationship(lazy="selectin")
    etablissement: Mapped[Etablissement] = relationship(lazy="selectin")


class AffectationSurveillance(Base):
    """Affectation d'un agent à un centre — chef de centre, surveillant, secrétaire…"""

    __tablename__ = "affectations_surveillance"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    centre_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("centres_composition.id", ondelete="CASCADE"), index=True, nullable=False
    )
    salle_composition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("salles_composition.id", ondelete="SET NULL"), index=True
    )
    enseignant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enseignants.id", ondelete="SET NULL"), index=True
    )
    personnel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("personnels.id", ondelete="SET NULL")
    )
    proposition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("propositions_personnel.id", ondelete="SET NULL")
    )

    role: Mapped[RoleSurveillance] = mapped_column(
        Enum(RoleSurveillance, native_enum=False), nullable=False, index=True
    )
    nom_complet: Mapped[str] = mapped_column(String(180), nullable=False)
    telephone: Mapped[str | None] = mapped_column(String(40))
    date_debut: Mapped[date | None] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date)
    heure_prise_service: Mapped[time | None] = mapped_column(Time)
    indemnite: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    present: Mapped[bool | None] = mapped_column(Boolean)
    responsabilites: Mapped[str | None] = mapped_column(Text)

    centre: Mapped[CentreComposition] = relationship(back_populates="affectations")
    salle_composition: Mapped[SalleComposition | None] = relationship(lazy="selectin")
    enseignant: Mapped[Enseignant | None] = relationship(lazy="selectin")


class Correcteur(Base):
    """Correcteur affecté à une épreuve d'une session."""

    __tablename__ = "correcteurs"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    epreuve_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("epreuves_examen.id", ondelete="CASCADE"), index=True
    )
    enseignant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enseignants.id", ondelete="SET NULL"), index=True
    )
    matiere_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("matieres.id", ondelete="SET NULL"), index=True
    )
    serie_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("series.id", ondelete="SET NULL"))
    centre_correction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("centres_composition.id", ondelete="SET NULL")
    )

    code_correcteur: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    nom_complet: Mapped[str] = mapped_column(String(180), nullable=False)
    telephone: Mapped[str | None] = mapped_column(String(40))
    est_chef_correcteur: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    copies_attribuees: Mapped[int] = mapped_column(default=0, nullable=False)
    copies_corrigees: Mapped[int] = mapped_column(default=0, nullable=False)
    indemnite: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    enseignant: Mapped[Enseignant | None] = relationship(lazy="selectin")
    matiere: Mapped[Matiere | None] = relationship(lazy="selectin")
    copies: Mapped[list[Copie]] = relationship(back_populates="correcteur")

    __table_args__ = (
        UniqueConstraint("session_id", "code_correcteur", name="uq_correcteurs_session_code"),
    )


# ------------------------------------------------------------------
#  Copies, notes et délibération
# ------------------------------------------------------------------


class Copie(Base):
    """Copie anonymée d'un candidat pour une épreuve."""

    __tablename__ = "copies"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    epreuve_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("epreuves_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    candidat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidats.id", ondelete="CASCADE"), index=True, nullable=False
    )
    correcteur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("correcteurs.id", ondelete="SET NULL"), index=True
    )
    correcteur_second_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("correcteurs.id", ondelete="SET NULL")
    )

    code_anonymat: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    lot: Mapped[str | None] = mapped_column(String(32), index=True)
    nombre_feuillets: Mapped[int] = mapped_column(default=1, nullable=False)

    note_correcteur: Mapped[float | None] = mapped_column(Float)
    note_second_correcteur: Mapped[float | None] = mapped_column(Float)
    note_finale: Mapped[float | None] = mapped_column(Float)
    double_correction: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ecart_significatif: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    corrigee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    corrigee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    validee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    observations: Mapped[str | None] = mapped_column(Text)

    correcteur: Mapped[Correcteur | None] = relationship(
        foreign_keys=[correcteur_id], back_populates="copies", lazy="selectin"
    )
    candidat: Mapped[Candidat] = relationship(lazy="selectin")
    epreuve: Mapped[EpreuveExamen] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("epreuve_id", "candidat_id", name="uq_copies_epreuve_candidat"),
        UniqueConstraint("session_id", "code_anonymat", name="uq_copies_session_anonymat"),
    )


class NoteExamen(Base):
    """Note définitive d'un candidat à une épreuve, après correction."""

    __tablename__ = "notes_examen"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    candidat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidats.id", ondelete="CASCADE"), index=True, nullable=False
    )
    epreuve_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("epreuves_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    copie_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("copies.id", ondelete="SET NULL"))

    valeur: Mapped[float | None] = mapped_column(Float, index=True)
    valeur_sur_20: Mapped[float | None] = mapped_column(Float)
    coefficient: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    points: Mapped[float | None] = mapped_column(Float)
    statut: Mapped[StatutNoteExamen] = mapped_column(
        Enum(StatutNoteExamen, native_enum=False),
        default=StatutNoteExamen.SAISIE,
        nullable=False,
        index=True,
    )
    saisie_par_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )
    validee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    modifiee_apres_contentieux: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ancienne_valeur: Mapped[float | None] = mapped_column(Float)

    candidat: Mapped[Candidat] = relationship(back_populates="notes")
    epreuve: Mapped[EpreuveExamen] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("candidat_id", "epreuve_id", name="uq_notes_examen_candidat_epreuve"),
    )


class Jury(Base):
    """Jury de délibération d'une session."""

    __tablename__ = "jurys"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    centre_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("centres_composition.id", ondelete="SET NULL"), index=True
    )
    serie_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("series.id", ondelete="SET NULL"), index=True
    )
    code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    president_nom: Mapped[str | None] = mapped_column(String(180))
    president_enseignant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enseignants.id", ondelete="SET NULL")
    )
    date_deliberation: Mapped[date | None] = mapped_column(Date)
    lieu: Mapped[str | None] = mapped_column(String(255))
    nombre_candidats: Mapped[int] = mapped_column(default=0, nullable=False)
    nombre_admis: Mapped[int] = mapped_column(default=0, nullable=False)
    cloture: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proces_verbal_url: Mapped[str | None] = mapped_column(String(500))
    observations: Mapped[str | None] = mapped_column(Text)

    membres: Mapped[list[MembreJury]] = relationship(
        back_populates="jury", cascade="all, delete-orphan"
    )
    resultats: Mapped[list[ResultatExamen]] = relationship(back_populates="jury")

    __table_args__ = (UniqueConstraint("session_id", "code", name="uq_jurys_session_code"),)


class MembreJury(Base):
    """Membre d'un jury de délibération."""

    __tablename__ = "membres_jury"

    jury_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jurys.id", ondelete="CASCADE"), index=True, nullable=False
    )
    enseignant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enseignants.id", ondelete="SET NULL"), index=True
    )
    nom_complet: Mapped[str] = mapped_column(String(180), nullable=False)
    qualite: Mapped[str | None] = mapped_column(String(120))
    est_president: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    est_rapporteur: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    present: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    indemnite: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    jury: Mapped[Jury] = relationship(back_populates="membres")
    enseignant: Mapped[Enseignant | None] = relationship(lazy="selectin")


class ResultatExamen(Base):
    """Résultat consolidé d'un candidat à l'issue de la délibération."""

    __tablename__ = "resultats_examen"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    candidat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidats.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    jury_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jurys.id", ondelete="SET NULL"), index=True
    )
    serie_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("series.id", ondelete="SET NULL"), index=True
    )
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    departement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departements.id", ondelete="SET NULL"), index=True
    )

    total_points: Mapped[float | None] = mapped_column(Float)
    total_coefficients: Mapped[float | None] = mapped_column(Float)
    moyenne: Mapped[float | None] = mapped_column(Float, index=True)
    mention: Mapped[str | None] = mapped_column(String(64), index=True)
    decision: Mapped[DecisionExamen] = mapped_column(
        Enum(DecisionExamen, native_enum=False),
        default=DecisionExamen.EN_ATTENTE,
        nullable=False,
        index=True,
    )
    rang_national: Mapped[int | None] = mapped_column()
    rang_departemental: Mapped[int | None] = mapped_column()
    rang_centre: Mapped[int | None] = mapped_column()
    rang_etablissement: Mapped[int | None] = mapped_column()

    repeche: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    points_jury: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    motivation_jury: Mapped[str | None] = mapped_column(Text)

    publie: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    publie_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    code_verification: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    releve_notes_url: Mapped[str | None] = mapped_column(String(500))

    candidat: Mapped[Candidat] = relationship(back_populates="resultat")
    jury: Mapped[Jury | None] = relationship(back_populates="resultats")

    __table_args__ = (
        Index("ix_resultats_session_decision", "session_id", "decision"),
        Index("ix_resultats_etab_session", "etablissement_id", "session_id"),
    )


# ------------------------------------------------------------------
#  Convocations, incidents, contentieux
# ------------------------------------------------------------------


class Convocation(Base):
    """Convocation générée pour un candidat ou un agent d'examen."""

    __tablename__ = "convocations"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type_convocation: Mapped[TypeConvocation] = mapped_column(
        Enum(TypeConvocation, native_enum=False), nullable=False, index=True
    )
    candidat_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("candidats.id", ondelete="CASCADE"), index=True
    )
    affectation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("affectations_surveillance.id", ondelete="CASCADE"), index=True
    )
    correcteur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("correcteurs.id", ondelete="CASCADE"), index=True
    )
    membre_jury_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("membres_jury.id", ondelete="CASCADE")
    )

    numero: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    destinataire: Mapped[str] = mapped_column(String(180), nullable=False)
    centre_nom: Mapped[str | None] = mapped_column(String(255))
    salle_nom: Mapped[str | None] = mapped_column(String(180))
    numero_place: Mapped[int | None] = mapped_column()
    date_convocation: Mapped[date | None] = mapped_column(Date)
    heure_convocation: Mapped[time | None] = mapped_column(Time)
    consignes: Mapped[str | None] = mapped_column(Text)

    pdf_url: Mapped[str | None] = mapped_column(String(500))
    code_verification: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    qr_code_url: Mapped[str | None] = mapped_column(String(500))
    imprimee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    telechargee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IncidentExamen(Base):
    """Incident survenu pendant les épreuves — fraude, retard, malaise, litige."""

    __tablename__ = "incidents_examen"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    centre_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("centres_composition.id", ondelete="CASCADE"), index=True
    )
    salle_composition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("salles_composition.id", ondelete="SET NULL")
    )
    candidat_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("candidats.id", ondelete="SET NULL"), index=True
    )
    epreuve_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("epreuves_examen.id", ondelete="SET NULL")
    )

    reference: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    categorie: Mapped[str] = mapped_column(String(80), nullable=False)
    gravite: Mapped[str] = mapped_column(String(32), default="MOYENNE", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    date_incident: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    declare_par: Mapped[str | None] = mapped_column(String(180))
    mesures_prises: Mapped[str | None] = mapped_column(Text)
    sanction_appliquee: Mapped[str | None] = mapped_column(String(255))
    clos: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    centre: Mapped[CentreComposition | None] = relationship(back_populates="incidents")


class Contentieux(Base):
    """Réclamation d'un candidat et son instruction."""

    __tablename__ = "contentieux"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    candidat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidats.id", ondelete="CASCADE"), index=True, nullable=False
    )
    epreuve_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("epreuves_examen.id", ondelete="SET NULL"), index=True
    )

    numero: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    type_contentieux: Mapped[TypeContentieux] = mapped_column(
        Enum(TypeContentieux, native_enum=False), nullable=False, index=True
    )
    objet: Mapped[str] = mapped_column(String(500), nullable=False)
    expose: Mapped[str] = mapped_column(Text, nullable=False)
    statut: Mapped[StatutContentieux] = mapped_column(
        Enum(StatutContentieux, native_enum=False),
        default=StatutContentieux.DEPOSEE,
        nullable=False,
        index=True,
    )

    date_depot: Mapped[date] = mapped_column(Date, nullable=False)
    date_recevabilite: Mapped[date | None] = mapped_column(Date)
    date_instruction: Mapped[date | None] = mapped_column(Date)
    date_decision: Mapped[date | None] = mapped_column(Date)

    instructeur_nom: Mapped[str | None] = mapped_column(String(180))
    instruit_par_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )
    conclusion: Mapped[str | None] = mapped_column(Text)
    note_avant: Mapped[float | None] = mapped_column(Float)
    note_apres: Mapped[float | None] = mapped_column(Float)
    decision_revisee: Mapped[DecisionExamen | None] = mapped_column(
        Enum(DecisionExamen, native_enum=False)
    )
    frais_dossier: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    notifie_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    candidat: Mapped[Candidat] = relationship(lazy="selectin")
    pieces: Mapped[list[PieceContentieux]] = relationship(
        back_populates="contentieux", cascade="all, delete-orphan"
    )


class PieceContentieux(Base):
    """Pièce versée au dossier d'un contentieux."""

    __tablename__ = "pieces_contentieux"

    contentieux_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contentieux.id", ondelete="CASCADE"), index=True, nullable=False
    )
    nom_fichier: Mapped[str] = mapped_column(String(255), nullable=False)
    chemin_stockage: Mapped[str] = mapped_column(String(500), nullable=False)
    type_mime: Mapped[str | None] = mapped_column(String(120))
    taille_octets: Mapped[int] = mapped_column(default=0, nullable=False)
    libelle: Mapped[str | None] = mapped_column(String(255))

    contentieux: Mapped[Contentieux] = relationship(back_populates="pieces")


# ------------------------------------------------------------------
#  Banque d'épreuves, archives et budget
# ------------------------------------------------------------------


class EpreuveArchivee(Base):
    """Banque d'épreuves : sujets archivés et consultables.

    Classement par filière, classe/niveau, matière et année ou session
    d'examen, conformément à la spécification d'archivage.
    """

    __tablename__ = "epreuves_archivees"

    reference: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    titre: Mapped[str] = mapped_column(String(255), nullable=False)
    examen_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("examens.id", ondelete="SET NULL"), index=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="SET NULL"), index=True
    )
    matiere_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("matieres.id", ondelete="SET NULL"), index=True
    )
    serie_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("series.id", ondelete="SET NULL"), index=True
    )
    filiere_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("filieres.id", ondelete="SET NULL"), index=True
    )
    niveau_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("niveaux.id", ondelete="SET NULL"), index=True
    )

    nature: Mapped[NatureExamen] = mapped_column(
        Enum(NatureExamen, native_enum=False), default=NatureExamen.EXAMEN, nullable=False
    )
    annee: Mapped[int] = mapped_column(nullable=False, index=True)
    duree_minutes: Mapped[int | None] = mapped_column()
    bareme: Mapped[float | None] = mapped_column(Float)
    coefficient: Mapped[float | None] = mapped_column(Float)

    sujet_url: Mapped[str | None] = mapped_column(String(500))
    corrige_url: Mapped[str | None] = mapped_column(String(500))
    bareme_url: Mapped[str | None] = mapped_column(String(500))
    mots_cles: Mapped[str | None] = mapped_column(String(500))
    nombre_telechargements: Mapped[int] = mapped_column(default=0, nullable=False)
    public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    matiere: Mapped[Matiere | None] = relationship(lazy="selectin")
    serie: Mapped[Serie | None] = relationship(lazy="selectin")

    __table_args__ = (Index("ix_epreuves_archivees_recherche", "matiere_id", "annee", "serie_id"),)


class BudgetExamen(Base):
    """Budget d'une session d'examen."""

    __tablename__ = "budgets_examen"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    montant_prevu: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    montant_engage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    montant_paye: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    recettes_inscriptions: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    devise: Mapped[str] = mapped_column(String(8), default="XOF", nullable=False)
    valide: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exercice: Mapped[int | None] = mapped_column()

    lignes: Mapped[list[LigneBudgetaire]] = relationship(
        back_populates="budget", cascade="all, delete-orphan"
    )


class LigneBudgetaire(Base):
    """Ligne budgétaire : centres, surveillants, correcteurs, transport, matériel…"""

    __tablename__ = "lignes_budgetaires"

    budget_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("budgets_examen.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    categorie: Mapped[str] = mapped_column(String(80), nullable=False)
    montant_prevu: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    montant_engage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    montant_paye: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    budget: Mapped[BudgetExamen] = relationship(back_populates="lignes")
    depenses: Mapped[list[DepenseExamen]] = relationship(
        back_populates="ligne", cascade="all, delete-orphan"
    )


class DepenseExamen(Base):
    """Dépense imputée à une ligne budgétaire."""

    __tablename__ = "depenses_examen"

    ligne_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lignes_budgetaires.id", ondelete="CASCADE"), index=True, nullable=False
    )
    centre_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("centres_composition.id", ondelete="SET NULL"), index=True
    )
    reference: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    objet: Mapped[str] = mapped_column(String(255), nullable=False)
    beneficiaire: Mapped[str | None] = mapped_column(String(180))
    fournisseur: Mapped[str | None] = mapped_column(String(180))
    montant: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    date_depense: Mapped[date] = mapped_column(Date, nullable=False)
    statut_paiement: Mapped[StatutPaiement] = mapped_column(
        Enum(StatutPaiement, native_enum=False), default=StatutPaiement.PENDING, nullable=False
    )
    justificatif_url: Mapped[str | None] = mapped_column(String(500))

    ligne: Mapped[LigneBudgetaire] = relationship(back_populates="depenses")
