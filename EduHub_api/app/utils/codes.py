"""Génération des identifiants, références et codes métier."""

from __future__ import annotations

import random
import secrets
import string
import uuid
from datetime import date

ALPHABET_CODE = string.ascii_uppercase + string.digits


def generer_identifiant_educatif(sequence: int, annee: int | None = None) -> str:
    """Identifiant éducatif national : `EDU-2026-000001`."""
    annee = annee or date.today().year
    return f"EDU-{annee}-{sequence:06d}"


def generer_matricule(prefixe: str, sequence: int, annee: int | None = None) -> str:
    """Matricule agent : `ENS-2026-00123`."""
    annee = annee or date.today().year
    return f"{prefixe}-{annee}-{sequence:05d}"


def generer_numero_candidat(code_examen: str, annee: int, sequence: int) -> str:
    """Numéro de candidat : `BEPC-2027-0001234`."""
    return f"{code_examen}-{annee}-{sequence:07d}"


def generer_numero_table(code_centre: str, sequence: int) -> str:
    """Numéro de table dans un centre : `C0142-0087`."""
    return f"{code_centre}-{sequence:04d}"


def generer_code_anonymat(longueur: int = 10) -> str:
    """Code d'anonymat d'une copie."""
    return "".join(secrets.choice(ALPHABET_CODE) for _ in range(longueur))


def generer_reference(prefixe: str, annee: int | None = None) -> str:
    """Référence documentaire : `DOC-2026-A1B2C3D4`."""
    annee = annee or date.today().year
    return f"{prefixe}-{annee}-{uuid.uuid4().hex[:8].upper()}"


def generer_code_verification(longueur: int = 16) -> str:
    """Code de vérification imprimé sur un document et encodé en QR."""
    return "".join(secrets.choice(ALPHABET_CODE) for _ in range(longueur))


def generer_numero_bulletin(annee_code: str, etablissement_code: str, sequence: int) -> str:
    """Numéro de bulletin : `BUL-2026-2027-CEG001-000042`."""
    return f"BUL-{annee_code}-{etablissement_code}-{sequence:06d}"


def generer_numero_diplome(sigle_examen: str, annee: int, sequence: int) -> str:
    """Numéro de diplôme : `BEPC/2027/0012345`."""
    return f"{sigle_examen}/{annee}/{sequence:07d}"


def generer_mot_de_passe(longueur: int = 12) -> str:
    """Mot de passe aléatoire lisible, pour les comptes créés par une administration."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(longueur))


def generer_code_barre(prefixe: str, rng: random.Random | None = None) -> str:
    """Code-barres d'un exemplaire de bibliothèque."""
    generateur = rng or random
    return f"{prefixe}{generateur.randint(10**9, 10**10 - 1)}"
