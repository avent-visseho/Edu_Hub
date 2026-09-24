"""Schémas du domaine identité — authentification, utilisateurs, rôles."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import EmailStr, Field, field_validator

from app.core.config import settings
from app.core.enums import Action, Civilite, Langue, NiveauScope, Sexe, TypeHandicap
from app.schemas.base import SchemaBase, SchemaEntree

# ------------------------------------------------------------------
#  Authentification
# ------------------------------------------------------------------


class ConnexionDemande(SchemaEntree):
    """Identifiants de connexion."""

    email: EmailStr
    mot_de_passe: str = Field(min_length=1)


class JetonsReponse(SchemaBase):
    """Couple de jetons émis à la connexion."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=settings.access_token_expire_minutes * 60)


class RafraichissementDemande(SchemaEntree):
    refresh_token: str


class ChangementMotDePasse(SchemaEntree):
    ancien_mot_de_passe: str
    nouveau_mot_de_passe: str = Field(min_length=settings.password_min_length)

    @field_validator("nouveau_mot_de_passe")
    @classmethod
    def _robustesse(cls, valeur: str) -> str:
        if valeur.isdigit() or valeur.isalpha():
            raise ValueError("Le mot de passe doit mêler lettres et chiffres.")
        return valeur


# ------------------------------------------------------------------
#  Permissions et rôles
# ------------------------------------------------------------------


class PermissionLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    ressource: str
    action: Action


class RoleLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    description: str | None = None
    niveau_scope: NiveauScope
    systeme: bool
    permissions: list[PermissionLecture] = Field(default_factory=list)


class RoleResume(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    niveau_scope: NiveauScope


class AffectationLecture(SchemaBase):
    """Rôle exercé par un utilisateur dans une portée donnée."""

    id: uuid.UUID
    role: RoleResume
    structure_id: uuid.UUID | None = None
    etablissement_id: uuid.UUID | None = None
    actif: bool
    debut: date | None = None
    fin: date | None = None


class AffectationEcriture(SchemaEntree):
    role_code: str
    structure_id: uuid.UUID | None = None
    etablissement_id: uuid.UUID | None = None
    debut: date | None = None
    fin: date | None = None


# ------------------------------------------------------------------
#  Utilisateurs
# ------------------------------------------------------------------


class PreferencesAccessibilite(SchemaEntree):
    """Réglages d'accessibilité propres à chaque utilisateur."""

    langue: Langue | None = None
    mode_simplifie: bool | None = None
    contraste_eleve: bool | None = None
    grande_police: bool | None = None
    lecture_vocale: bool | None = None
    type_handicap: TypeHandicap | None = None
    notes_accessibilite: str | None = Field(default=None, max_length=2000)


class UtilisateurLecture(SchemaBase):
    id: uuid.UUID
    email: EmailStr
    civilite: Civilite | None = None
    nom: str
    prenoms: str
    nom_complet: str
    sexe: Sexe | None = None
    date_naissance: date | None = None
    telephone: str | None = None
    adresse: str | None = None
    photo_url: str | None = None
    actif: bool
    verifie: bool
    doit_changer_mot_de_passe: bool
    derniere_connexion: datetime | None = None
    langue: Langue
    type_handicap: TypeHandicap
    mode_simplifie: bool
    contraste_eleve: bool
    grande_police: bool
    lecture_vocale: bool
    created_at: datetime


class UtilisateurDetail(UtilisateurLecture):
    """Utilisateur avec ses affectations et ses droits effectifs."""

    affectations: list[AffectationLecture] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    niveau_scope: NiveauScope = NiveauScope.PERSONNEL


class UtilisateurCreation(SchemaEntree):
    email: EmailStr
    mot_de_passe: str | None = Field(default=None, min_length=settings.password_min_length)
    civilite: Civilite | None = None
    nom: str = Field(min_length=1, max_length=120)
    prenoms: str = Field(min_length=1, max_length=180)
    sexe: Sexe | None = None
    date_naissance: date | None = None
    lieu_naissance: str | None = Field(default=None, max_length=180)
    telephone: str | None = Field(default=None, max_length=40)
    adresse: str | None = Field(default=None, max_length=255)
    langue: Langue = Langue.FR
    type_handicap: TypeHandicap = TypeHandicap.AUCUN
    actif: bool = True
    affectations: list[AffectationEcriture] = Field(default_factory=list)


class UtilisateurMiseAJour(SchemaEntree):
    civilite: Civilite | None = None
    nom: str | None = Field(default=None, min_length=1, max_length=120)
    prenoms: str | None = Field(default=None, min_length=1, max_length=180)
    sexe: Sexe | None = None
    date_naissance: date | None = None
    telephone: str | None = Field(default=None, max_length=40)
    adresse: str | None = Field(default=None, max_length=255)
    photo_url: str | None = Field(default=None, max_length=500)
    actif: bool | None = None
    langue: Langue | None = None
    type_handicap: TypeHandicap | None = None
    mode_simplifie: bool | None = None
    contraste_eleve: bool | None = None
    grande_police: bool | None = None
    lecture_vocale: bool | None = None


class ReinitialisationMotDePasse(SchemaEntree):
    """Réinitialisation par une administration."""

    nouveau_mot_de_passe: str | None = Field(default=None, min_length=settings.password_min_length)
    forcer_changement: bool = True
