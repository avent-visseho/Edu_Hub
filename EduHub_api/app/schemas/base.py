"""Schémas de base et types partagés."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SchemaBase(BaseModel):
    """Schéma de sortie lisant directement les attributs d'un objet ORM."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SchemaEntree(BaseModel):
    """Schéma d'entrée refusant les champs inconnus."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Horodatage(SchemaBase):
    """Métadonnées temporelles communes."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class Reference(SchemaBase):
    """Référence légère vers une entité, pour les listes déroulantes."""

    id: uuid.UUID
    code: str | None = None
    libelle: str


class MessageReponse(BaseModel):
    """Réponse générique à une action sans contenu."""

    message: str
    details: dict[str, Any] | None = None


class ResultatOperation(BaseModel):
    """Compte rendu d'une opération de masse."""

    succes: bool = True
    traites: int = 0
    ignores: int = 0
    erreurs: list[str] = Field(default_factory=list)
    message: str | None = None


class NomenclatureLecture(SchemaBase):
    """Élément de référentiel : code, libellé, activation."""

    id: uuid.UUID
    code: str
    libelle: str
    description: str | None = None
    actif: bool = True
    ordre: int = 0


class NomenclatureEcriture(SchemaEntree):
    """Création ou mise à jour d'un élément de référentiel."""

    code: str = Field(min_length=1, max_length=64)
    libelle: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    actif: bool = True
    ordre: int = 0
