"""statut de paiement en français

Le domaine est intégralement en français ; l'énumération des statuts de paiement
était restée en anglais et remontait telle quelle dans l'interface. Les colonnes
sont des VARCHAR (l'énumération n'est pas native côté PostgreSQL) : il suffit de
les élargir puis de réécrire les valeurs stockées.

Revision ID: 8f2a4c17b0d5
Revises: 1c6d1989f93b
Create Date: 2026-09-24 21:40:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8f2a4c17b0d5"
down_revision: str | None = "1c6d1989f93b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Colonnes portant un StatutPaiement.
COLONNES: tuple[tuple[str, str], ...] = (
    ("versements_bourse", "statut"),
    ("abonnements_transport", "statut_paiement"),
    ("candidats", "statut_paiement"),
    ("depenses_examen", "statut_paiement"),
)

TRADUCTIONS: tuple[tuple[str, str], ...] = (
    ("PENDING", "EN_ATTENTE"),
    ("PAID", "PAYE"),
    ("FAILED", "ECHOUE"),
    ("REFUNDED", "REMBOURSE"),
)

LONGUEUR_ANGLAISE = 8
LONGUEUR_FRANCAISE = 10


def _redimensionner(longueur: int) -> None:
    for table, colonne in COLONNES:
        op.alter_column(
            table,
            colonne,
            existing_type=sa.String(length=LONGUEUR_ANGLAISE),
            type_=sa.String(length=longueur),
            existing_nullable=False,
        )


def _traduire(couples: Sequence[tuple[str, str]]) -> None:
    for table, colonne in COLONNES:
        for source, cible in couples:
            op.execute(
                sa.text(
                    f"UPDATE {table} SET {colonne} = :cible WHERE {colonne} = :source"
                ).bindparams(cible=cible, source=source)
            )


def upgrade() -> None:
    # « EN_ATTENTE » dépasse la largeur d'origine : on élargit avant de réécrire.
    _redimensionner(LONGUEUR_FRANCAISE)
    _traduire(TRADUCTIONS)


def downgrade() -> None:
    _traduire([(cible, source) for source, cible in TRADUCTIONS])
    _redimensionner(LONGUEUR_ANGLAISE)
