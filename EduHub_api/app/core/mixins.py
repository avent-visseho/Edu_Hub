"""Mixins ORM réutilisables."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, declarative_mixin, mapped_column


@declarative_mixin
class CodeMixin:
    """Entité identifiée par un code métier unique et un libellé."""

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ordre: Mapped[int] = mapped_column(default=0, nullable=False)


@declarative_mixin
class SoftDeleteMixin:
    """Entité archivable sans suppression physique."""

    supprime: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    supprime_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


@declarative_mixin
class AuditorMixin:
    """Trace l'auteur de la création et de la dernière modification."""

    cree_par_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )
    modifie_par_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )
