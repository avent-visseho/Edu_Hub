"""Donne une adresse mémorable à un compte de démonstration par rôle.

Le générateur crée des comptes pour tous les acteurs, mais leurs adresses sont
dérivées de données tirées au hasard : « ablam.adjovi.635@enseignant.bj » n'est
ni devinable ni stable. La page de connexion ne pouvait donc proposer que la
chaîne administrative, dont les adresses sont construites à partir de codes
fixes.

Cette migration renomme un compte existant par rôle plutôt que d'en créer de
nouveaux : l'élève reste inscrit dans sa classe, l'enseignant garde ses
matières, le parent ses enfants. Le choix est déterministe — le compte dont
l'adresse vient en premier alphabétiquement — afin que deux exécutions sur le
même jeu de données désignent le même compte.

Elle est sans effet si les adresses sont déjà en place, et ne peut pas être
annulée : l'adresse d'origine, engendrée au hasard, n'a rien qui mérite d'être
restaurée.

Revision ID: 6a1f3c8d2b90
Revises: 3d5b81c9e4a7
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "6a1f3c8d2b90"
down_revision = "3d5b81c9e4a7"
branch_labels = None
depends_on = None

#: (code du rôle, adresse retenue)
COMPTES = (
    ("SCHOOL_ADMIN", "directeur@eduhub.bj"),
    ("TEACHER", "enseignant@eduhub.bj"),
    ("STUDENT", "eleve@eduhub.bj"),
    ("PARENT", "parent@eduhub.bj"),
)


def upgrade() -> None:
    connexion = op.get_bind()

    for code_role, adresse in COMPTES:
        identifiant = connexion.execute(
            sa.text(
                """
                SELECT u.id
                FROM utilisateurs AS u
                JOIN utilisateur_roles AS ur ON ur.utilisateur_id = u.id
                JOIN roles AS r ON r.id = ur.role_id
                WHERE r.code = :code
                ORDER BY u.email
                LIMIT 1
                """
            ),
            {"code": code_role},
        ).scalar()

        if identifiant is None:
            continue
        # Le compte retenu porte déjà l'adresse visée : la migration a tourné.
        deja = connexion.execute(
            sa.text("SELECT email FROM utilisateurs WHERE id = :ident"), {"ident": identifiant}
        ).scalar()
        if deja == adresse:
            continue

        # L'adresse est unique : si le générateur l'a produite ailleurs, on la
        # libère avant de l'attribuer.
        connexion.execute(
            sa.text(
                "UPDATE utilisateurs SET email = 'ancien.' || email "
                "WHERE email = :adresse AND id <> :ident"
            ),
            {"adresse": adresse, "ident": identifiant},
        )
        connexion.execute(
            sa.text("UPDATE utilisateurs SET email = :adresse WHERE id = :ident"),
            {"adresse": adresse, "ident": identifiant},
        )


def downgrade() -> None:
    """Rien à défaire : les adresses remplacées étaient engendrées au hasard."""
