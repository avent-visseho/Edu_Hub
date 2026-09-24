"""Commandes d'administration en ligne de commande."""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import create_engine, text

from app.core.config import settings


def _admin_engine():
    return create_engine(settings.postgres_admin_url, isolation_level="AUTOCOMMIT")


def reset_db() -> None:
    """Détruit puis recrée la base de données applicative."""
    name = settings.database_name
    engine = _admin_engine()
    with engine.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :name AND pid <> pg_backend_pid()"
            ),
            {"name": name},
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    engine.dispose()
    print(f"Base de données « {name} » recréée.")


def create_db() -> None:
    name = settings.database_name
    engine = _admin_engine()
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
        ).scalar()
        if exists:
            print(f"Base de données « {name} » déjà présente.")
        else:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
            print(f"Base de données « {name} » créée.")
    engine.dispose()


COMMANDS = {"reset-db": reset_db, "create-db": create_db}


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.cli", description="Administration EduHub")
    parser.add_argument("command", choices=sorted(COMMANDS))
    args = parser.parse_args()
    COMMANDS[args.command]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
