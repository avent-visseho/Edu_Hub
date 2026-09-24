"""Moteur de documents — dépôt, versionnement et validation des pièces."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import StatutGenerique
from app.core.exceptions import NotFoundError, ValidationError
from app.engines.storage import stockage
from app.models.referentiel import TypeDocument
from app.models.systeme import Document
from app.utils.codes import generer_code_verification, generer_reference


async def _controler_contraintes(
    session: AsyncSession,
    type_document_id: uuid.UUID | None,
    nom_fichier: str,
    taille_octets: int,
) -> None:
    """Vérifie l'extension et la taille par rapport au type de document."""
    if type_document_id is None:
        return
    type_document = await session.get(TypeDocument, type_document_id)
    if type_document is None:
        return

    extension = nom_fichier.rsplit(".", 1)[-1].lower() if "." in nom_fichier else ""
    autorisees = {e.strip().lower() for e in type_document.extensions_autorisees.split(",")}
    if extension not in autorisees:
        raise ValidationError(
            f"Format « {extension or 'inconnu'} » non autorisé pour « {type_document.libelle} ».",
            details={"extensions_autorisees": sorted(autorisees)},
        )

    if taille_octets > type_document.taille_max_ko * 1024:
        raise ValidationError(
            f"Fichier trop volumineux : maximum {type_document.taille_max_ko} Ko.",
            details={"taille_max_ko": type_document.taille_max_ko},
        )


async def deposer(
    session: AsyncSession,
    *,
    entite_type: str,
    entite_id: uuid.UUID | None,
    nom: str,
    nom_fichier: str,
    contenu: bytes,
    type_mime: str | None = None,
    type_document_id: uuid.UUID | None = None,
    proprietaire_id: uuid.UUID | None = None,
    auteur_id: uuid.UUID | None = None,
    confidentiel: bool = False,
    metadonnees: dict[str, Any] | None = None,
) -> Document:
    """Dépose un document et crée automatiquement une nouvelle version si besoin."""
    await _controler_contraintes(session, type_document_id, nom_fichier, len(contenu))

    chemin = stockage.construire_chemin(entite_type, nom_fichier)
    stockage.deposer(chemin, contenu, type_mime)

    version = 1
    parent_id: uuid.UUID | None = None
    if entite_id is not None:
        precedent = (
            await session.execute(
                select(Document)
                .where(
                    Document.entite_type == entite_type,
                    Document.entite_id == entite_id,
                    Document.nom == nom,
                )
                .order_by(Document.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if precedent is not None:
            version = precedent.version + 1
            parent_id = precedent.id

    document = Document(
        reference=generer_reference("DOC"),
        nom=nom,
        type_document_id=type_document_id,
        entite_type=entite_type,
        entite_id=entite_id,
        nom_fichier=nom_fichier,
        chemin_stockage=chemin,
        type_mime=type_mime,
        taille_octets=len(contenu),
        empreinte=stockage.empreinte(contenu),
        version=version,
        document_parent_id=parent_id,
        statut=StatutGenerique.SOUMIS,
        proprietaire_id=proprietaire_id,
        auteur_id=auteur_id,
        confidentiel=confidentiel,
        code_verification=generer_code_verification(),
        metadonnees=metadonnees,
    )
    session.add(document)
    await session.flush()
    return document


async def obtenir(session: AsyncSession, document_id: uuid.UUID) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise NotFoundError("Document introuvable.")
    return document


async def telecharger(session: AsyncSession, document_id: uuid.UUID) -> tuple[Document, bytes]:
    document = await obtenir(session, document_id)
    return document, stockage.lire(document.chemin_stockage)


async def valider(
    session: AsyncSession,
    document_id: uuid.UUID,
    *,
    valide: bool,
    commentaire: str | None = None,
) -> Document:
    document = await obtenir(session, document_id)
    document.statut = StatutGenerique.VALIDE if valide else StatutGenerique.REJETE
    if commentaire:
        metadonnees = dict(document.metadonnees or {})
        metadonnees["commentaire_validation"] = commentaire
        document.metadonnees = metadonnees
    await session.flush()
    return document


async def archiver(session: AsyncSession, document_id: uuid.UUID) -> Document:
    document = await obtenir(session, document_id)
    document.archive = True
    document.statut = StatutGenerique.ARCHIVE
    await session.flush()
    return document


async def lister_par_entite(
    session: AsyncSession,
    entite_type: str,
    entite_id: uuid.UUID,
    *,
    derniere_version_seulement: bool = True,
) -> list[Document]:
    stmt = select(Document).where(
        Document.entite_type == entite_type,
        Document.entite_id == entite_id,
        Document.archive.is_(False),
    )
    documents = list((await session.execute(stmt)).scalars())

    if not derniere_version_seulement:
        return documents

    derniers: dict[str, Document] = {}
    for document in documents:
        actuel = derniers.get(document.nom)
        if actuel is None or document.version > actuel.version:
            derniers[document.nom] = document
    return list(derniers.values())


async def compter_par_statut(
    session: AsyncSession, entite_type: str, entite_id: uuid.UUID
) -> dict[str, int]:
    stmt = (
        select(Document.statut, func.count())
        .where(Document.entite_type == entite_type, Document.entite_id == entite_id)
        .group_by(Document.statut)
    )
    return {statut.value: total for statut, total in (await session.execute(stmt)).all()}
