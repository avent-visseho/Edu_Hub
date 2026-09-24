"""Schémas des référentiels territoriaux et des nomenclatures."""

from __future__ import annotations

import uuid

from pydantic import Field

from app.schemas.base import SchemaBase, SchemaEntree


class DepartementLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    chef_lieu: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    population: int | None = None
    actif: bool = True


class CommuneLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    departement_id: uuid.UUID
    latitude: float | None = None
    longitude: float | None = None
    population: int | None = None
    actif: bool = True


class ArrondissementLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    commune_id: uuid.UUID
    actif: bool = True


class VillageLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    arrondissement_id: uuid.UUID
    quartier_ville: bool = False


class DepartementEcriture(SchemaEntree):
    code: str = Field(min_length=1, max_length=64)
    libelle: str = Field(min_length=1, max_length=255)
    chef_lieu: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    population: int | None = None
    actif: bool = True


class CommuneEcriture(SchemaEntree):
    code: str = Field(min_length=1, max_length=64)
    libelle: str = Field(min_length=1, max_length=255)
    departement_id: uuid.UUID
    latitude: float | None = None
    longitude: float | None = None
    population: int | None = None
    actif: bool = True


class TypeExamenLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    est_concours: bool = False
    actif: bool = True


class TypeDocumentLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    extensions_autorisees: str
    taille_max_ko: int
    actif: bool = True


class DiplomeReferentielLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    niveau_qualification: str | None = None
    actif: bool = True


class NiveauLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    cycle_id: uuid.UUID | None = None
    rang: int = 0
    actif: bool = True


class SerieLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    description: str | None = None
    technique: bool = False
    actif: bool = True


class FiliereLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    description: str | None = None
    duree_annees: int = 3
    debouches: str | None = None
    actif: bool = True


class MatiereLecture(SchemaBase):
    id: uuid.UUID
    code: str
    libelle: str
    abreviation: str | None = None
    domaine: str | None = None
    coefficient_defaut: float = 1.0
    volume_horaire_defaut: int = 0
    couleur: str | None = None
    actif: bool = True


class MatiereEcriture(SchemaEntree):
    code: str = Field(min_length=1, max_length=32)
    libelle: str = Field(min_length=1, max_length=180)
    abreviation: str | None = Field(default=None, max_length=16)
    domaine: str | None = None
    coefficient_defaut: float = Field(default=1.0, ge=0, le=20)
    volume_horaire_defaut: int = Field(default=0, ge=0, le=60)
    couleur: str | None = None
    actif: bool = True
