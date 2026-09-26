"""Ramène dans le pays les établissements situés hors des frontières.

Le tirage des coordonnées dispersait chaque établissement dans un carré de
±0,4° autour du chef-lieu de son département, sans connaître les frontières.
Autour de Cotonou, cela plaçait des écoles dans le golfe de Guinée ; à l'ouest,
au Togo. Sur un jeu de deux cent cinquante établissements, soixante-douze
tombaient hors du territoire — de quoi rendre la carte nationale incohérente
dès qu'on masque l'extérieur du pays.

Le tirage est corrigé à la source dans app/seed/contexte.py. Cette migration
répare les bases déjà peuplées : elle relocalise les seuls établissements
fautifs, en tirant une nouvelle position dans le pays autour du chef-lieu de
leur département. Le tirage est amorcé par l'identifiant de l'établissement,
afin que deux exécutions donnent le même résultat.

Elle est sans effet sur une base déjà conforme, et ne peut pas être annulée :
les coordonnées d'origine, étant fictives et invalides, n'ont rien qui mérite
d'être restauré.

Revision ID: 3d5b81c9e4a7
Revises: 8f2a4c17b0d5
"""

from __future__ import annotations

import random

import sqlalchemy as sa

from alembic import op
from app.seed.frontiere import dans_le_pays

revision = "3d5b81c9e4a7"
down_revision = "8f2a4c17b0d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connexion = op.get_bind()

    # On joint le département par la commune : l'établissement ne porte pas
    # lui-même de référence départementale.
    lignes = connexion.execute(
        sa.text(
            """
            SELECT e.id, e.latitude, e.longitude, d.latitude AS lat_dep, d.longitude AS lon_dep
            FROM etablissements AS e
            JOIN communes AS c ON c.id = e.commune_id
            JOIN departements AS d ON d.id = c.departement_id
            WHERE e.latitude IS NOT NULL AND e.longitude IS NOT NULL
            """
        )
    ).fetchall()

    corrections: list[dict[str, object]] = []
    for ligne in lignes:
        if dans_le_pays(float(ligne.latitude), float(ligne.longitude)):
            continue

        tirage = random.Random(str(ligne.id))
        latitude, longitude = float(ligne.lat_dep), float(ligne.lon_dep)
        for essai in range(40):
            portee = 0.4 * (1 - essai / 50)
            candidat = (
                round(latitude + tirage.uniform(-portee, portee), 6),
                round(longitude + tirage.uniform(-portee, portee), 6),
            )
            if dans_le_pays(*candidat):
                latitude, longitude = candidat
                break

        corrections.append({"ident": ligne.id, "latitude": latitude, "longitude": longitude})

    if not corrections:
        return

    connexion.execute(
        sa.text(
            "UPDATE etablissements SET latitude = :latitude, longitude = :longitude "
            "WHERE id = :ident"
        ),
        corrections,
    )


def downgrade() -> None:
    """Rien à défaire : les positions remplacées étaient hors du territoire."""
