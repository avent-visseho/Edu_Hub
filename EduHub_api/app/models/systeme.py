"""Domaines 17 et 18 — Documents, communication, audit, règles et gouvernance."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Any

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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.enums import StatutGenerique

# ------------------------------------------------------------------
#  Moteur de documents
# ------------------------------------------------------------------


class Document(Base):
    """Document générique géré par le moteur de documents.

    Le même moteur sert les candidatures, bourses, examens, diplômes, stages
    et actes administratifs, via `entite_type` et `entite_id`.
    """

    __tablename__ = "documents"

    reference: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    type_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("types_document.id", ondelete="SET NULL"), index=True
    )
    entite_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entite_id: Mapped[uuid.UUID | None] = mapped_column(index=True)

    nom_fichier: Mapped[str] = mapped_column(String(255), nullable=False)
    chemin_stockage: Mapped[str] = mapped_column(String(500), nullable=False)
    type_mime: Mapped[str | None] = mapped_column(String(120))
    taille_octets: Mapped[int] = mapped_column(default=0, nullable=False)
    empreinte: Mapped[str | None] = mapped_column(String(128), index=True)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    document_parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )

    statut: Mapped[StatutGenerique] = mapped_column(
        Enum(StatutGenerique, native_enum=False),
        default=StatutGenerique.SOUMIS,
        nullable=False,
        index=True,
    )
    proprietaire_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL"), index=True
    )
    auteur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )
    confidentiel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    signature_numerique: Mapped[str | None] = mapped_column(String(255))
    code_verification: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    date_expiration: Mapped[date | None] = mapped_column(Date)
    archive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    metadonnees: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    __table_args__ = (Index("ix_documents_entite", "entite_type", "entite_id"),)


# ------------------------------------------------------------------
#  Moteur de workflow
# ------------------------------------------------------------------


class TransitionWorkflow(Base):
    """Trace d'une transition de statut appliquée à une entité."""

    __tablename__ = "transitions_workflow"

    entite_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entite_id: Mapped[uuid.UUID] = mapped_column(index=True, nullable=False)
    workflow: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    statut_avant: Mapped[str | None] = mapped_column(String(64))
    statut_apres: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    commentaire: Mapped[str | None] = mapped_column(Text)
    acteur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL"), index=True
    )
    acteur_nom: Mapped[str | None] = mapped_column(String(180))

    __table_args__ = (Index("ix_transitions_entite", "entite_type", "entite_id"),)


# ------------------------------------------------------------------
#  Moteur de notifications et messagerie
# ------------------------------------------------------------------


class TypeNotification(StrEnum):
    INFORMATION = "INFORMATION"
    URGENCE = "URGENCE"
    EXAMEN = "EXAMEN"
    RESULTAT = "RESULTAT"
    ABSENCE = "ABSENCE"
    PAIEMENT = "PAIEMENT"
    BOURSE = "BOURSE"
    TRANSPORT = "TRANSPORT"
    COURS = "COURS"
    PROJET = "PROJET"
    BULLETIN = "BULLETIN"
    INSCRIPTION = "INSCRIPTION"
    DOCUMENT = "DOCUMENT"
    SYSTEME = "SYSTEME"


class CanalNotification(StrEnum):
    APPLICATION = "APPLICATION"
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    VOCAL = "VOCAL"


class Notification(Base):
    """Notification adressée à un utilisateur."""

    __tablename__ = "notifications"

    destinataire_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type_notification: Mapped[TypeNotification] = mapped_column(
        Enum(TypeNotification, native_enum=False),
        default=TypeNotification.INFORMATION,
        nullable=False,
        index=True,
    )
    canal: Mapped[CanalNotification] = mapped_column(
        Enum(CanalNotification, native_enum=False),
        default=CanalNotification.APPLICATION,
        nullable=False,
    )
    titre: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    message_simplifie: Mapped[str | None] = mapped_column(String(500))
    audio_url: Mapped[str | None] = mapped_column(String(500))
    pictogramme: Mapped[str | None] = mapped_column(String(32))
    lien: Mapped[str | None] = mapped_column(String(500))
    entite_type: Mapped[str | None] = mapped_column(String(64))
    entite_id: Mapped[uuid.UUID | None] = mapped_column()
    priorite: Mapped[int] = mapped_column(default=0, nullable=False)
    lue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    lue_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    envoyee: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (Index("ix_notifications_destinataire_lue", "destinataire_id", "lue"),)


class Message(Base):
    """Message échangé entre deux utilisateurs de la plateforme."""

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(index=True, nullable=False)
    expediteur_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    destinataire_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    objet: Mapped[str | None] = mapped_column(String(255))
    corps: Mapped[str] = mapped_column(Text, nullable=False)
    piece_jointe_url: Mapped[str | None] = mapped_column(String(500))
    audio_url: Mapped[str | None] = mapped_column(String(500))
    lu: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lu_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archive_expediteur: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archive_destinataire: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Annonce(Base):
    """Annonce publiée à destination d'un public large."""

    __tablename__ = "annonces"

    titre: Mapped[str] = mapped_column(String(255), nullable=False)
    contenu: Mapped[str] = mapped_column(Text, nullable=False)
    contenu_simplifie: Mapped[str | None] = mapped_column(Text)
    audio_url: Mapped[str | None] = mapped_column(String(500))
    image_url: Mapped[str | None] = mapped_column(String(500))
    structure_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("structures.id", ondelete="CASCADE"), index=True
    )
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="CASCADE"), index=True
    )
    public_cible: Mapped[str | None] = mapped_column(String(255))
    urgente: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    date_publication: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    date_expiration: Mapped[date | None] = mapped_column(Date)
    publiee: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    nombre_vues: Mapped[int] = mapped_column(default=0, nullable=False)


# ------------------------------------------------------------------
#  Moteur d'audit
# ------------------------------------------------------------------


class JournalAudit(Base):
    """Journal d'audit des opérations sensibles."""

    __tablename__ = "journal_audit"

    utilisateur_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL"), index=True
    )
    utilisateur_email: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entite_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entite_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    entite_libelle: Mapped[str | None] = mapped_column(String(255))
    valeurs_avant: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    valeurs_apres: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    adresse_ip: Mapped[str | None] = mapped_column(String(64))
    agent_utilisateur: Mapped[str | None] = mapped_column(String(400))
    succes: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_journal_audit_entite", "entite_type", "entite_id"),
        Index("ix_journal_audit_date", "created_at"),
    )


# ------------------------------------------------------------------
#  Moteur de règles et alertes
# ------------------------------------------------------------------


class RegleMetier(Base):
    """Règle métier configurable : SI <condition> ALORS <conséquence>."""

    __tablename__ = "regles_metier"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    domaine: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entite_cible: Mapped[str] = mapped_column(String(64), nullable=False)
    conditions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    consequences: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    priorite: Mapped[int] = mapped_column(default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    derniere_execution: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    nombre_declenchements: Mapped[int] = mapped_column(default=0, nullable=False)


class NiveauAlerte(StrEnum):
    INFO = "INFO"
    ATTENTION = "ATTENTION"
    CRITIQUE = "CRITIQUE"


class Alerte(Base):
    """Alerte produite par le moteur de règles ou l'analytique."""

    __tablename__ = "alertes"

    code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    titre: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    niveau: Mapped[NiveauAlerte] = mapped_column(
        Enum(NiveauAlerte, native_enum=False),
        default=NiveauAlerte.ATTENTION,
        nullable=False,
        index=True,
    )
    domaine: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    regle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("regles_metier.id", ondelete="SET NULL")
    )
    entite_type: Mapped[str | None] = mapped_column(String(64))
    entite_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="CASCADE"), index=True
    )
    valeur_mesuree: Mapped[float | None] = mapped_column(Float)
    seuil: Mapped[float | None] = mapped_column(Float)
    traitee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    traitee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    traitee_par_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )


# ------------------------------------------------------------------
#  Recherche avancée et rapports
# ------------------------------------------------------------------


class RequeteEnregistree(Base):
    """Requête du constructeur visuel, sauvegardée pour réutilisation."""

    __tablename__ = "requetes_enregistrees"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    entite_cible: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    filtres: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    colonnes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    tri: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    proprietaire_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True
    )
    partagee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requete_naturelle: Mapped[str | None] = mapped_column(Text)
    nombre_executions: Mapped[int] = mapped_column(default=0, nullable=False)
    derniere_execution: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Rapport(Base):
    """Rapport généré : annuel, établissement, département, examen, inclusion…"""

    __tablename__ = "rapports"

    reference: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    titre: Mapped[str] = mapped_column(String(255), nullable=False)
    type_rapport: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    perimetre: Mapped[str | None] = mapped_column(String(255))
    annee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("annees_academiques.id", ondelete="SET NULL"), index=True
    )
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    structure_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("structures.id", ondelete="SET NULL"), index=True
    )
    parametres: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    donnees: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    fichier_url: Mapped[str | None] = mapped_column(String(500))
    format_export: Mapped[str] = mapped_column(String(16), default="PDF", nullable=False)
    genere_par_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )
    genere_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IndicateurStatistique(Base):
    """Indicateur consolidé, précalculé pour les tableaux de bord."""

    __tablename__ = "indicateurs_statistiques"

    code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    categorie: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    perimetre_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    perimetre_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    perimetre_libelle: Mapped[str | None] = mapped_column(String(255))
    annee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("annees_academiques.id", ondelete="CASCADE"), index=True
    )
    valeur: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    valeur_precedente: Mapped[float | None] = mapped_column(Float)
    variation_pourcentage: Mapped[float | None] = mapped_column(Float)
    unite: Mapped[str | None] = mapped_column(String(32))
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    calcule_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_indicateurs_perimetre", "code", "perimetre_type", "perimetre_id", "annee_id"),
    )


class ConversationAssistant(Base):
    """Échange avec l'assistant intelligent de la plateforme."""

    __tablename__ = "conversations_assistant"

    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    profil_assistant: Mapped[str] = mapped_column(
        String(32), default="ETUDIANT", nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reponse: Mapped[str | None] = mapped_column(Text)
    filtres_generes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    entite_cible: Mapped[str | None] = mapped_column(String(64))
    nombre_resultats: Mapped[int | None] = mapped_column()
    duree_ms: Mapped[int | None] = mapped_column()
    utile: Mapped[bool | None] = mapped_column(Boolean)


class ParametreSysteme(Base):
    """Paramètre de configuration modifiable sans redéploiement."""

    __tablename__ = "parametres_systeme"

    cle: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    valeur: Mapped[str] = mapped_column(Text, nullable=False)
    type_valeur: Mapped[str] = mapped_column(String(32), default="TEXTE", nullable=False)
    categorie: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    modifiable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
