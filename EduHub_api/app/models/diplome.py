"""Domaine 10 — Diplômes, certifications et vérification."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.apprenant import Apprenant
    from app.models.examen import Candidat, SessionExamen
    from app.models.referentiel import Diplome as DiplomeReferentiel


class StatutDiplome(StrEnum):
    EN_PREPARATION = "EN_PREPARATION"
    EMIS = "EMIS"
    REMIS = "REMIS"
    SUSPENDU = "SUSPENDU"
    ANNULE = "ANNULE"
    DUPLICATA = "DUPLICATA"


class TypeAttestation(StrEnum):
    ATTESTATION_REUSSITE = "ATTESTATION_REUSSITE"
    RELEVE_NOTES = "RELEVE_NOTES"
    CERTIFICAT_SCOLARITE = "CERTIFICAT_SCOLARITE"
    ATTESTATION_INSCRIPTION = "ATTESTATION_INSCRIPTION"
    CERTIFICAT_COMPETENCE = "CERTIFICAT_COMPETENCE"
    ATTESTATION_STAGE = "ATTESTATION_STAGE"


class DiplomeDelivre(Base):
    """Diplôme délivré à un lauréat, vérifiable par QR code."""

    __tablename__ = "diplomes_delivres"

    numero: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    code_verification: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )

    apprenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("apprenants.id", ondelete="SET NULL"), index=True
    )
    candidat_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("candidats.id", ondelete="SET NULL"), index=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sessions_examen.id", ondelete="SET NULL"), index=True
    )
    diplome_ref_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("diplomes_referentiel.id", ondelete="SET NULL"), index=True
    )
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )

    titulaire_nom: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    titulaire_date_naissance: Mapped[date | None] = mapped_column(Date)
    titulaire_lieu_naissance: Mapped[str | None] = mapped_column(String(180))
    intitule: Mapped[str] = mapped_column(String(255), nullable=False)
    serie_libelle: Mapped[str | None] = mapped_column(String(180))
    session_libelle: Mapped[str | None] = mapped_column(String(180))
    annee: Mapped[int] = mapped_column(nullable=False, index=True)
    moyenne: Mapped[float | None] = mapped_column(Float)
    mention: Mapped[str | None] = mapped_column(String(64))

    statut: Mapped[StatutDiplome] = mapped_column(
        Enum(StatutDiplome, native_enum=False),
        default=StatutDiplome.EMIS,
        nullable=False,
        index=True,
    )
    date_delivrance: Mapped[date] = mapped_column(Date, nullable=False)
    date_remise: Mapped[date | None] = mapped_column(Date)
    signataire: Mapped[str | None] = mapped_column(String(180))
    qualite_signataire: Mapped[str | None] = mapped_column(String(180))

    pdf_url: Mapped[str | None] = mapped_column(String(500))
    qr_code_url: Mapped[str | None] = mapped_column(String(500))
    empreinte_numerique: Mapped[str | None] = mapped_column(String(128))
    duplicata_de_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("diplomes_delivres.id", ondelete="SET NULL")
    )
    motif_annulation: Mapped[str | None] = mapped_column(Text)
    nombre_verifications: Mapped[int] = mapped_column(default=0, nullable=False)

    apprenant: Mapped[Apprenant | None] = relationship(lazy="selectin")
    candidat: Mapped[Candidat | None] = relationship(lazy="selectin")
    session: Mapped[SessionExamen | None] = relationship(lazy="selectin")
    diplome_ref: Mapped[DiplomeReferentiel | None] = relationship(lazy="selectin")


class Attestation(Base):
    """Attestation, certificat ou relevé délivré à un apprenant."""

    __tablename__ = "attestations"

    numero: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    code_verification: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    type_attestation: Mapped[TypeAttestation] = mapped_column(
        Enum(TypeAttestation, native_enum=False), nullable=False, index=True
    )
    apprenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("apprenants.id", ondelete="SET NULL"), index=True
    )
    candidat_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("candidats.id", ondelete="SET NULL")
    )
    etablissement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("etablissements.id", ondelete="SET NULL"), index=True
    )
    annee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("annees_academiques.id", ondelete="SET NULL")
    )

    titulaire_nom: Mapped[str] = mapped_column(String(180), nullable=False)
    objet: Mapped[str] = mapped_column(String(500), nullable=False)
    contenu: Mapped[str | None] = mapped_column(Text)
    date_delivrance: Mapped[date] = mapped_column(Date, nullable=False)
    valable_jusqu_au: Mapped[date | None] = mapped_column(Date)
    signataire: Mapped[str | None] = mapped_column(String(180))
    pdf_url: Mapped[str | None] = mapped_column(String(500))
    qr_code_url: Mapped[str | None] = mapped_column(String(500))
    annulee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class VerificationDocument(Base):
    """Trace d'une vérification d'authenticité d'un diplôme ou d'une attestation."""

    __tablename__ = "verifications_document"

    code_verification: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    type_document: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column()
    resultat_valide: Mapped[bool] = mapped_column(Boolean, nullable=False)
    adresse_ip: Mapped[str | None] = mapped_column(String(64))
    agent_utilisateur: Mapped[str | None] = mapped_column(String(400))
    verifie_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
