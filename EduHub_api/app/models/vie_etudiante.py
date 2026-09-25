"""Domaines 12 et 13 — Bourses, aides, transport, logement, restauration, santé, bibliothèque."""

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
from app.core.enums import StatutPaiement

if TYPE_CHECKING:
    from app.models.apprenant import Apprenant
    from app.models.etablissement import Etablissement
    from app.models.referentiel import Commune, TypeBourse


# ------------------------------------------------------------------
#  Bourses et aides sociales
# ------------------------------------------------------------------


class StatutCandidatureBourse(StrEnum):
    BROUILLON = "BROUILLON"
    SOUMISE = "SOUMISE"
    EN_EVALUATION = "EN_EVALUATION"
    INCOMPLETE = "INCOMPLETE"
    PRESELECTIONNEE = "PRESELECTIONNEE"
    ATTRIBUEE = "ATTRIBUEE"
    REJETEE = "REJETEE"
    SUSPENDUE = "SUSPENDUE"
    CLOTUREE = "CLOTUREE"


class TypeAideSociale(StrEnum):
    TRANSPORT = "TRANSPORT"
    LOGEMENT = "LOGEMENT"
    RESTAURATION = "RESTAURATION"
    EXCEPTIONNELLE = "EXCEPTIONNELLE"
    HANDICAP = "HANDICAP"
    MATERIEL = "MATERIEL"
    SANTE = "SANTE"
    FOURNITURES = "FOURNITURES"


class ProgrammeBourse(Base):
    """Programme de bourses ouvert par une structure ou un partenaire."""

    __tablename__ = "programmes_bourse"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    intitule: Mapped[str] = mapped_column(String(255), nullable=False)
    type_bourse_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("types_bourse.id", ondelete="SET NULL"), index=True
    )
    structure_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("structures.id", ondelete="SET NULL"), index=True
    )
    annee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("annees_academiques.id", ondelete="SET NULL"), index=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    criteres_eligibilite: Mapped[str | None] = mapped_column(Text)
    montant_mensuel: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duree_mois: Mapped[int] = mapped_column(default=12, nullable=False)
    places: Mapped[int] = mapped_column(default=0, nullable=False)
    places_attribuees: Mapped[int] = mapped_column(default=0, nullable=False)
    moyenne_minimale: Mapped[float | None] = mapped_column(Float)
    date_ouverture: Mapped[date] = mapped_column(Date, nullable=False)
    date_cloture: Mapped[date] = mapped_column(Date, nullable=False)
    ouvert: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reserve_handicap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    type_bourse: Mapped[TypeBourse | None] = relationship(lazy="selectin")
    candidatures: Mapped[list[CandidatureBourse]] = relationship(
        back_populates="programme", cascade="all, delete-orphan"
    )


class CandidatureBourse(Base):
    """Candidature d'un apprenant à un programme de bourses."""

    __tablename__ = "candidatures_bourse"

    numero: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    programme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programmes_bourse.id", ondelete="CASCADE"), index=True, nullable=False
    )
    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    statut: Mapped[StatutCandidatureBourse] = mapped_column(
        Enum(StatutCandidatureBourse, native_enum=False),
        default=StatutCandidatureBourse.BROUILLON,
        nullable=False,
        index=True,
    )
    moyenne_reference: Mapped[float | None] = mapped_column(Float)
    score_evaluation: Mapped[float | None] = mapped_column(Float)
    rang: Mapped[int | None] = mapped_column()
    revenu_familial_declare: Mapped[float | None] = mapped_column(Float)
    motivation: Mapped[str | None] = mapped_column(Text)
    date_soumission: Mapped[date | None] = mapped_column(Date)
    date_decision: Mapped[date | None] = mapped_column(Date)
    motif_rejet: Mapped[str | None] = mapped_column(String(500))
    montant_attribue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    date_debut_versement: Mapped[date | None] = mapped_column(Date)
    date_fin_versement: Mapped[date | None] = mapped_column(Date)

    programme: Mapped[ProgrammeBourse] = relationship(
        back_populates="candidatures", lazy="selectin"
    )
    apprenant: Mapped[Apprenant] = relationship(lazy="selectin")
    versements: Mapped[list[VersementBourse]] = relationship(
        back_populates="candidature", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("programme_id", "apprenant_id", name="uq_candidatures_bourse"),
    )


class VersementBourse(Base):
    """Versement mensuel d'une bourse attribuée."""

    __tablename__ = "versements_bourse"

    candidature_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidatures_bourse.id", ondelete="CASCADE"), index=True, nullable=False
    )
    periode_libelle: Mapped[str] = mapped_column(String(64), nullable=False)
    montant: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    date_prevue: Mapped[date] = mapped_column(Date, nullable=False)
    date_versement: Mapped[date | None] = mapped_column(Date)
    statut: Mapped[StatutPaiement] = mapped_column(
        Enum(StatutPaiement, native_enum=False), default=StatutPaiement.EN_ATTENTE, nullable=False
    )
    reference: Mapped[str | None] = mapped_column(String(80))

    candidature: Mapped[CandidatureBourse] = relationship(back_populates="versements")


class AideSociale(Base):
    """Aide sociale ponctuelle ou récurrente accordée à un apprenant."""

    __tablename__ = "aides_sociales"

    numero: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type_aide: Mapped[TypeAideSociale] = mapped_column(
        Enum(TypeAideSociale, native_enum=False), nullable=False, index=True
    )
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    motif: Mapped[str | None] = mapped_column(Text)
    montant: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    en_nature: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    date_demande: Mapped[date] = mapped_column(Date, nullable=False)
    date_attribution: Mapped[date | None] = mapped_column(Date)
    statut: Mapped[StatutCandidatureBourse] = mapped_column(
        Enum(StatutCandidatureBourse, native_enum=False),
        default=StatutCandidatureBourse.SOUMISE,
        nullable=False,
    )

    apprenant: Mapped[Apprenant] = relationship(lazy="selectin")

    @property
    def beneficiaire_nom(self) -> str | None:
        return self.apprenant.nom_complet if self.apprenant else None

    @property
    def identifiant_educatif(self) -> str | None:
        return self.apprenant.identifiant_educatif if self.apprenant else None


# ------------------------------------------------------------------
#  Transport
# ------------------------------------------------------------------


class TypeVehicule(StrEnum):
    BUS = "BUS"
    MINIBUS = "MINIBUS"
    NAVETTE = "NAVETTE"
    TRICYCLE = "TRICYCLE"
    MOTO = "MOTO"
    VOITURE = "VOITURE"


class StatutVehicule(StrEnum):
    EN_SERVICE = "EN_SERVICE"
    EN_MAINTENANCE = "EN_MAINTENANCE"
    HORS_SERVICE = "HORS_SERVICE"
    RESERVE = "RESERVE"


class StatutTrajet(StrEnum):
    PLANIFIE = "PLANIFIE"
    EN_COURS = "EN_COURS"
    TERMINE = "TERMINE"
    ANNULE = "ANNULE"
    RETARDE = "RETARDE"


class LigneTransport(Base):
    """Ligne de transport scolaire ou universitaire."""

    __tablename__ = "lignes_transport"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    commune_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communes.id", ondelete="SET NULL"), index=True
    )
    origine: Mapped[str] = mapped_column(String(180), nullable=False)
    destination: Mapped[str] = mapped_column(String(180), nullable=False)
    distance_km: Mapped[float | None] = mapped_column(Float)
    duree_minutes: Mapped[int | None] = mapped_column()
    tarif: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tarif_abonnement: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    couleur: Mapped[str | None] = mapped_column(String(16))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    etablissement: Mapped[Etablissement | None] = relationship(lazy="selectin")
    commune: Mapped[Commune | None] = relationship(lazy="selectin")
    arrets: Mapped[list[ArretTransport]] = relationship(
        back_populates="ligne", cascade="all, delete-orphan", order_by="ArretTransport.ordre"
    )
    trajets: Mapped[list[Trajet]] = relationship(back_populates="ligne")


class ArretTransport(Base):
    """Arrêt d'une ligne de transport."""

    __tablename__ = "arrets_transport"

    ligne_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lignes_transport.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    nom: Mapped[str] = mapped_column(String(180), nullable=False)
    ordre: Mapped[int] = mapped_column(default=0, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    heure_passage_aller: Mapped[time | None] = mapped_column(Time)
    heure_passage_retour: Mapped[time | None] = mapped_column(Time)
    abri: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accessible_handicap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    ligne: Mapped[LigneTransport] = relationship(back_populates="arrets")


class Vehicule(Base):
    """Véhicule affecté au transport."""

    __tablename__ = "vehicules"

    immatriculation: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    type_vehicule: Mapped[TypeVehicule] = mapped_column(
        Enum(TypeVehicule, native_enum=False), default=TypeVehicule.BUS, nullable=False
    )
    marque: Mapped[str | None] = mapped_column(String(80))
    modele: Mapped[str | None] = mapped_column(String(80))
    annee: Mapped[int | None] = mapped_column()
    places: Mapped[int] = mapped_column(default=50, nullable=False)
    places_pmr: Mapped[int] = mapped_column(default=0, nullable=False)
    statut: Mapped[StatutVehicule] = mapped_column(
        Enum(StatutVehicule, native_enum=False), default=StatutVehicule.EN_SERVICE, nullable=False
    )
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    derniere_visite_technique: Mapped[date | None] = mapped_column(Date)
    climatise: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    trajets: Mapped[list[Trajet]] = relationship(back_populates="vehicule")


class Conducteur(Base):
    """Conducteur habilité au transport des apprenants."""

    __tablename__ = "conducteurs"

    matricule: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    nom_complet: Mapped[str] = mapped_column(String(180), nullable=False)
    telephone: Mapped[str | None] = mapped_column(String(40))
    numero_permis: Mapped[str | None] = mapped_column(String(64))
    categorie_permis: Mapped[str | None] = mapped_column(String(16))
    date_validite_permis: Mapped[date | None] = mapped_column(Date)
    annees_experience: Mapped[int] = mapped_column(default=0, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    trajets: Mapped[list[Trajet]] = relationship(back_populates="conducteur")


class Trajet(Base):
    """Trajet effectué sur une ligne, avec suivi simulé en temps réel."""

    __tablename__ = "trajets"

    ligne_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lignes_transport.id", ondelete="CASCADE"), index=True, nullable=False
    )
    vehicule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vehicules.id", ondelete="SET NULL"), index=True
    )
    conducteur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conducteurs.id", ondelete="SET NULL"), index=True
    )
    date_trajet: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sens: Mapped[str] = mapped_column(String(16), default="ALLER", nullable=False)
    heure_depart_prevue: Mapped[time] = mapped_column(Time, nullable=False)
    heure_depart_reelle: Mapped[time | None] = mapped_column(Time)
    heure_arrivee_prevue: Mapped[time | None] = mapped_column(Time)
    statut: Mapped[StatutTrajet] = mapped_column(
        Enum(StatutTrajet, native_enum=False), default=StatutTrajet.PLANIFIE, nullable=False
    )
    places_occupees: Mapped[int] = mapped_column(default=0, nullable=False)
    prochain_arret_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("arrets_transport.id", ondelete="SET NULL")
    )
    minutes_avant_prochain_arret: Mapped[int | None] = mapped_column()
    latitude_actuelle: Mapped[float | None] = mapped_column(Float)
    longitude_actuelle: Mapped[float | None] = mapped_column(Float)
    retard_minutes: Mapped[int] = mapped_column(default=0, nullable=False)

    ligne: Mapped[LigneTransport] = relationship(back_populates="trajets", lazy="selectin")
    vehicule: Mapped[Vehicule | None] = relationship(back_populates="trajets", lazy="selectin")
    conducteur: Mapped[Conducteur | None] = relationship(back_populates="trajets", lazy="selectin")


class AbonnementTransport(Base):
    """Abonnement d'un apprenant à une ligne de transport."""

    __tablename__ = "abonnements_transport"

    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ligne_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lignes_transport.id", ondelete="CASCADE"), index=True, nullable=False
    )
    arret_montee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("arrets_transport.id", ondelete="SET NULL")
    )
    numero_carte: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)
    montant: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    statut_paiement: Mapped[StatutPaiement] = mapped_column(
        Enum(StatutPaiement, native_enum=False), default=StatutPaiement.EN_ATTENTE, nullable=False
    )
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    apprenant: Mapped[Apprenant] = relationship(lazy="selectin")
    ligne: Mapped[LigneTransport] = relationship(lazy="selectin")

    @property
    def abonne_nom(self) -> str | None:
        return self.apprenant.nom_complet if self.apprenant else None

    @property
    def ligne_libelle(self) -> str | None:
        return self.ligne.libelle if self.ligne else None


# ------------------------------------------------------------------
#  Logement et restauration
# ------------------------------------------------------------------


class Residence(Base):
    """Résidence universitaire ou internat."""

    __tablename__ = "residences"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    commune_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communes.id", ondelete="SET NULL")
    )
    adresse: Mapped[str | None] = mapped_column(String(255))
    capacite: Mapped[int] = mapped_column(default=0, nullable=False)
    places_occupees: Mapped[int] = mapped_column(default=0, nullable=False)
    tarif_mensuel: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    mixte: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accessible_handicap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    chambres: Mapped[list[Chambre]] = relationship(
        back_populates="residence", cascade="all, delete-orphan"
    )


class Chambre(Base):
    """Chambre d'une résidence."""

    __tablename__ = "chambres"

    residence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("residences.id", ondelete="CASCADE"), index=True, nullable=False
    )
    numero: Mapped[str] = mapped_column(String(32), nullable=False)
    batiment: Mapped[str | None] = mapped_column(String(80))
    etage: Mapped[int] = mapped_column(default=0, nullable=False)
    nombre_lits: Mapped[int] = mapped_column(default=2, nullable=False)
    lits_occupes: Mapped[int] = mapped_column(default=0, nullable=False)
    tarif_mensuel: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    accessible_handicap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    residence: Mapped[Residence] = relationship(back_populates="chambres", lazy="selectin")

    __table_args__ = (UniqueConstraint("residence_id", "numero", name="uq_chambres_residence"),)


class AttributionLogement(Base):
    """Attribution d'un lit à un apprenant."""

    __tablename__ = "attributions_logement"

    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chambre_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chambres.id", ondelete="CASCADE"), index=True, nullable=False
    )
    numero_lit: Mapped[int] = mapped_column(default=1, nullable=False)
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date | None] = mapped_column(Date)
    statut: Mapped[StatutCandidatureBourse] = mapped_column(
        Enum(StatutCandidatureBourse, native_enum=False),
        default=StatutCandidatureBourse.ATTRIBUEE,
        nullable=False,
    )
    caution: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    apprenant: Mapped[Apprenant] = relationship(lazy="selectin")
    chambre: Mapped[Chambre] = relationship(lazy="selectin")


class Restaurant(Base):
    """Restaurant universitaire ou cantine scolaire."""

    __tablename__ = "restaurants"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    capacite: Mapped[int] = mapped_column(default=0, nullable=False)
    tarif_repas: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tarif_subventionne: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    horaire_ouverture: Mapped[time | None] = mapped_column(Time)
    horaire_fermeture: Mapped[time | None] = mapped_column(Time)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    menus: Mapped[list[Menu]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )


class Menu(Base):
    """Menu journalier d'un restaurant."""

    __tablename__ = "menus"

    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    date_service: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    service: Mapped[str] = mapped_column(String(32), default="DEJEUNER", nullable=False)
    entree: Mapped[str | None] = mapped_column(String(180))
    plat_principal: Mapped[str] = mapped_column(String(180), nullable=False)
    accompagnement: Mapped[str | None] = mapped_column(String(180))
    dessert: Mapped[str | None] = mapped_column(String(180))
    boisson: Mapped[str | None] = mapped_column(String(180))
    calories: Mapped[int | None] = mapped_column()
    vegetarien: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    repas_servis: Mapped[int] = mapped_column(default=0, nullable=False)

    restaurant: Mapped[Restaurant] = relationship(back_populates="menus")

    __table_args__ = (
        UniqueConstraint("restaurant_id", "date_service", "service", name="uq_menus_service"),
    )


# ------------------------------------------------------------------
#  Santé
# ------------------------------------------------------------------


class CentreSante(Base):
    """Centre de santé, infirmerie scolaire ou universitaire."""

    __tablename__ = "centres_sante"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    commune_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communes.id", ondelete="SET NULL")
    )
    services: Mapped[str | None] = mapped_column(String(500))
    telephone: Mapped[str | None] = mapped_column(String(40))
    nombre_agents: Mapped[int] = mapped_column(default=0, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RendezVousSante(Base):
    """Rendez-vous de santé d'un apprenant (données fictives)."""

    __tablename__ = "rendez_vous_sante"

    centre_sante_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("centres_sante.id", ondelete="CASCADE"), index=True, nullable=False
    )
    apprenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("apprenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    motif: Mapped[str] = mapped_column(String(255), nullable=False)
    date_rdv: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    statut: Mapped[str] = mapped_column(String(32), default="PLANIFIE", nullable=False)
    orientation: Mapped[str | None] = mapped_column(String(255))
    confidentiel: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CampagneSante(Base):
    """Campagne de santé scolaire : vaccination, dépistage, sensibilisation."""

    __tablename__ = "campagnes_sante"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    intitule: Mapped[str] = mapped_column(String(255), nullable=False)
    theme: Mapped[str | None] = mapped_column(String(180))
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)
    beneficiaires_cibles: Mapped[int] = mapped_column(default=0, nullable=False)
    beneficiaires_atteints: Mapped[int] = mapped_column(default=0, nullable=False)


# ------------------------------------------------------------------
#  Bibliothèque
# ------------------------------------------------------------------


class Bibliotheque(Base):
    """Bibliothèque d'un établissement."""

    __tablename__ = "bibliotheques"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    nombre_places: Mapped[int] = mapped_column(default=0, nullable=False)
    duree_pret_jours: Mapped[int] = mapped_column(default=14, nullable=False)
    prets_simultanes_max: Mapped[int] = mapped_column(default=3, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    exemplaires: Mapped[list[Exemplaire]] = relationship(back_populates="bibliotheque")


class Livre(Base):
    """Ouvrage du catalogue."""

    __tablename__ = "livres"

    isbn: Mapped[str | None] = mapped_column(String(32), index=True)
    titre: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    auteur: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    editeur: Mapped[str | None] = mapped_column(String(180))
    annee_publication: Mapped[int | None] = mapped_column()
    categorie: Mapped[str | None] = mapped_column(String(120), index=True)
    langue: Mapped[str] = mapped_column(String(32), default="Français", nullable=False)
    nombre_pages: Mapped[int | None] = mapped_column()
    resume: Mapped[str | None] = mapped_column(Text)
    couverture_url: Mapped[str | None] = mapped_column(String(500))
    format_accessible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    audio_disponible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    braille_disponible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    exemplaires: Mapped[list[Exemplaire]] = relationship(
        back_populates="livre", cascade="all, delete-orphan"
    )


class Exemplaire(Base):
    """Exemplaire physique d'un ouvrage dans une bibliothèque."""

    __tablename__ = "exemplaires"

    livre_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("livres.id", ondelete="CASCADE"), index=True, nullable=False
    )
    bibliotheque_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bibliotheques.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code_barre: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    cote: Mapped[str | None] = mapped_column(String(64))
    etat: Mapped[str] = mapped_column(String(32), default="BON", nullable=False)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    livre: Mapped[Livre] = relationship(back_populates="exemplaires", lazy="selectin")
    bibliotheque: Mapped[Bibliotheque] = relationship(back_populates="exemplaires", lazy="selectin")


class Pret(Base):
    """Prêt d'un exemplaire à un emprunteur."""

    __tablename__ = "prets"

    exemplaire_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exemplaires.id", ondelete="CASCADE"), index=True, nullable=False
    )
    apprenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("apprenants.id", ondelete="SET NULL"), index=True
    )
    enseignant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enseignants.id", ondelete="SET NULL"), index=True
    )
    date_pret: Mapped[date] = mapped_column(Date, nullable=False)
    date_retour_prevue: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    date_retour_effective: Mapped[date | None] = mapped_column(Date)
    jours_retard: Mapped[int] = mapped_column(default=0, nullable=False)
    penalite: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    prolonge: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rendu: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    exemplaire: Mapped[Exemplaire] = relationship(lazy="selectin")
    apprenant: Mapped[Apprenant | None] = relationship(lazy="selectin")

    __table_args__ = (Index("ix_prets_retard", "rendu", "date_retour_prevue"),)

    @property
    def emprunteur_nom(self) -> str | None:
        return self.apprenant.nom_complet if self.apprenant else None

    @property
    def ouvrage_titre(self) -> str | None:
        return self.exemplaire.livre.titre if self.exemplaire and self.exemplaire.livre else None

    @property
    def ouvrage_auteur(self) -> str | None:
        return self.exemplaire.livre.auteur if self.exemplaire and self.exemplaire.livre else None

    @property
    def code_barre(self) -> str | None:
        return self.exemplaire.code_barre if self.exemplaire else None
