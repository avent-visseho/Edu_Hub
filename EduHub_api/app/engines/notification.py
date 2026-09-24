"""Moteur de notifications — diffusion multicanal et accessible."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.systeme import CanalNotification, Notification, TypeNotification

#: Pictogramme associé à chaque type, pour l'interface simplifiée.
PICTOGRAMMES: dict[TypeNotification, str] = {
    TypeNotification.INFORMATION: "ℹ️",
    TypeNotification.URGENCE: "🚨",
    TypeNotification.EXAMEN: "📝",
    TypeNotification.RESULTAT: "🏆",
    TypeNotification.ABSENCE: "📅",
    TypeNotification.PAIEMENT: "💳",
    TypeNotification.BOURSE: "🎓",
    TypeNotification.TRANSPORT: "🚌",
    TypeNotification.COURS: "📚",
    TypeNotification.PROJET: "💡",
    TypeNotification.BULLETIN: "📊",
    TypeNotification.INSCRIPTION: "✅",
    TypeNotification.DOCUMENT: "📎",
    TypeNotification.SYSTEME: "⚙️",
}

#: Priorité implicite des types urgents.
PRIORITES: dict[TypeNotification, int] = {
    TypeNotification.URGENCE: 3,
    TypeNotification.RESULTAT: 2,
    TypeNotification.EXAMEN: 2,
    TypeNotification.PAIEMENT: 1,
}


async def notifier(
    session: AsyncSession,
    *,
    destinataire_id: uuid.UUID,
    type_notification: TypeNotification,
    titre: str,
    message: str,
    message_simplifie: str | None = None,
    canal: CanalNotification = CanalNotification.APPLICATION,
    lien: str | None = None,
    entite_type: str | None = None,
    entite_id: uuid.UUID | None = None,
    audio_url: str | None = None,
) -> Notification:
    """Crée une notification enrichie des attributs d'accessibilité."""
    notification = Notification(
        destinataire_id=destinataire_id,
        type_notification=type_notification,
        canal=canal,
        titre=titre,
        message=message,
        message_simplifie=message_simplifie or _simplifier(message),
        pictogramme=PICTOGRAMMES.get(type_notification, "🔔"),
        priorite=PRIORITES.get(type_notification, 0),
        lien=lien,
        entite_type=entite_type,
        entite_id=entite_id,
        audio_url=audio_url,
    )
    session.add(notification)
    return notification


async def notifier_lot(
    session: AsyncSession,
    destinataires: Iterable[uuid.UUID],
    *,
    type_notification: TypeNotification,
    titre: str,
    message: str,
    message_simplifie: str | None = None,
    lien: str | None = None,
) -> int:
    """Diffuse la même notification à plusieurs destinataires."""
    total = 0
    for destinataire_id in destinataires:
        await notifier(
            session,
            destinataire_id=destinataire_id,
            type_notification=type_notification,
            titre=titre,
            message=message,
            message_simplifie=message_simplifie,
            lien=lien,
        )
        total += 1
    return total


def _simplifier(message: str, longueur_max: int = 120) -> str:
    """Produit une version courte, adaptée à l'interface simplifiée."""
    texte = " ".join(message.split())
    if len(texte) <= longueur_max:
        return texte
    return texte[: longueur_max - 1].rstrip() + "…"


async def marquer_lues(
    session: AsyncSession,
    destinataire_id: uuid.UUID,
    identifiants: Sequence[uuid.UUID] | None = None,
) -> int:
    """Marque comme lues toutes les notifications, ou celles indiquées."""
    from datetime import UTC, datetime

    stmt = (
        update(Notification)
        .where(Notification.destinataire_id == destinataire_id, Notification.lue.is_(False))
        .values(lue=True, lue_le=datetime.now(UTC))
    )
    if identifiants:
        stmt = stmt.where(Notification.id.in_(identifiants))
    resultat = await session.execute(stmt)
    return resultat.rowcount or 0


async def compter_non_lues(session: AsyncSession, destinataire_id: uuid.UUID) -> int:
    stmt = select(func.count()).where(
        Notification.destinataire_id == destinataire_id,
        Notification.lue.is_(False),
    )
    return int((await session.execute(stmt)).scalar_one())
