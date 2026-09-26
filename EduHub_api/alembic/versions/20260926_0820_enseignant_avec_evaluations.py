"""Rattache le compte enseignant à un professeur qui a des évaluations.

Comme pour le chef d'établissement, le tri alphabétique désignait un enseignant
sans la moindre évaluation : son tableau de bord affichait des zéros et la
démonstration n'y montrait rien.

Cette migration réattribue l'adresse enseignant@eduhub.bj au professeur qui en
compte le plus. Elle est sans effet si c'est déjà le cas.

Revision ID: b7d4e0a91f62
Revises: 9c2e5f71a4d3
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "b7d4e0a91f62"
down_revision = "9c2e5f71a4d3"
branch_labels = None
depends_on = None

ADRESSE = "enseignant@eduhub.bj"


def upgrade() -> None:
    connexion = op.get_bind()

    vise = connexion.execute(
        sa.text(
            """
            SELECT u.id
            FROM utilisateurs AS u
            JOIN utilisateur_roles AS ur ON ur.utilisateur_id = u.id
            JOIN roles AS r ON r.id = ur.role_id
            LEFT JOIN enseignants AS e ON e.utilisateur_id = u.id
            LEFT JOIN (
                SELECT enseignant_id, COUNT(*) AS total
                FROM evaluations GROUP BY enseignant_id
            ) AS ev ON ev.enseignant_id = e.id
            WHERE r.code = 'TEACHER'
            ORDER BY COALESCE(ev.total, 0) DESC, u.email
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
