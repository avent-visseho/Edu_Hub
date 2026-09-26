"""Rattache le compte directeur à un établissement qui a des classes.

Le choix se faisait par ordre alphabétique des adresses et tombait sur un
centre d'alphabétisation dépourvu de classes : le chef d'établissement se
connectait sur des écrans vides, ce qui n'illustre rien.

Cette migration réattribue l'adresse directeur@eduhub.bj au chef de
l'établissement qui compte le plus de classes. Elle est sans effet si c'est
déjà le cas.

Revision ID: 9c2e5f71a4d3
Revises: 6a1f3c8d2b90
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "9c2e5f71a4d3"
down_revision = "6a1f3c8d2b90"
branch_labels = None
depends_on = None

ADRESSE = "directeur@eduhub.bj"


def upgrade() -> None:
    connexion = op.get_bind()

    vise = connexion.execute(
        sa.text(
            """
            SELECT u.id
            FROM utilisateurs AS u
            JOIN utilisateur_roles AS ur ON ur.utilisateur_id = u.id
            JOIN roles AS r ON r.id = ur.role_id
            LEFT JOIN (
                SELECT etablissement_id, COUNT(*) AS total
                FROM classes GROUP BY etablissement_id
            ) AS c ON c.etablissement_id = ur.etablissement_id
            WHERE r.code = 'SCHOOL_ADMIN'
            ORDER BY COALESCE(c.total, 0) DESC, u.email
            LIMIT 1
            """
        )
    ).scalar()

    if vise is None:
        return

    actuel = connexion.execute(
        sa.text("SELECT id FROM utilisateurs WHERE email = :adresse"), {"adresse": ADRESSE}
    ).scalar()
    if actuel == vise:
        return

    # Le compte qui portait l'adresse retrouve une adresse dérivée de la
    # précédente, afin que la contrainte d'unicité soit respectée.
    if actuel is not None:
        connexion.execute(
            sa.text("UPDATE utilisateurs SET email = 'ancien.' || email WHERE id = :ident"),
            {"ident": actuel},
        )
    connexion.execute(
        sa.text("UPDATE utilisateurs SET email = :adresse WHERE id = :ident"),
        {"adresse": ADRESSE, "ident": vise},
    )


def downgrade() -> None:
    """Rien à défaire : seule l'adresse d'un compte de démonstration a changé."""
