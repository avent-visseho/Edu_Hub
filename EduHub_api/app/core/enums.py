"""Énumérations transverses au système."""

from __future__ import annotations

from enum import StrEnum


class Civilite(StrEnum):
    M = "M"
    MME = "MME"
    MLLE = "MLLE"


class Sexe(StrEnum):
    MASCULIN = "MASCULIN"
    FEMININ = "FEMININ"


class StatutGenerique(StrEnum):
    """Cycle de vie générique utilisé par le moteur de workflow."""

    BROUILLON = "BROUILLON"
    SOUMIS = "SOUMIS"
    EN_ETUDE = "EN_ETUDE"
    INCOMPLET = "INCOMPLET"
    VALIDE = "VALIDE"
    REJETE = "REJETE"
    ANNULE = "ANNULE"
    ARCHIVE = "ARCHIVE"


class Action(StrEnum):
    """Actions élémentaires soumises à permission."""

    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    VALIDATE = "VALIDATE"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    PUBLISH = "PUBLISH"
    EXPORT = "EXPORT"
    PRINT = "PRINT"
    ASSIGN = "ASSIGN"
    ARCHIVE = "ARCHIVE"


class RoleCode(StrEnum):
    """Rôles principaux de la plateforme."""

    SUPER_ADMIN = "SUPER_ADMIN"
    MINISTRY_ADMIN = "MINISTRY_ADMIN"
    DIRECTOR_ADMIN = "DIRECTOR_ADMIN"
    DEPARTMENT_ADMIN = "DEPARTMENT_ADMIN"
    EXAM_ADMIN = "EXAM_ADMIN"
    SCHOOL_ADMIN = "SCHOOL_ADMIN"
    SCHOOL_STAFF = "SCHOOL_STAFF"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"
    PARENT = "PARENT"
    CANDIDATE = "CANDIDATE"
    CORRECTOR = "CORRECTOR"
    INVIGILATOR = "INVIGILATOR"
    JURY_MEMBER = "JURY_MEMBER"
    RESEARCHER = "RESEARCHER"
    COMPANY = "COMPANY"
    PARTNER = "PARTNER"
    TRANSPORT_MANAGER = "TRANSPORT_MANAGER"
    LIBRARIAN = "LIBRARIAN"
    HEALTH_WORKER = "HEALTH_WORKER"
    FINANCE_MANAGER = "FINANCE_MANAGER"


class NiveauScope(StrEnum):
    """Portée d'action d'un utilisateur dans la hiérarchie institutionnelle."""

    NATIONAL = "NATIONAL"
    MINISTERE = "MINISTERE"
    DIRECTION = "DIRECTION"
    DEPARTEMENT = "DEPARTEMENT"
    ETABLISSEMENT = "ETABLISSEMENT"
    PERSONNEL = "PERSONNEL"


class TypeHandicap(StrEnum):
    AUCUN = "AUCUN"
    VISUEL = "VISUEL"
    AUDITIF = "AUDITIF"
    MOTEUR = "MOTEUR"
    COGNITIF = "COGNITIF"
    LANGAGE = "LANGAGE"
    MULTIPLE = "MULTIPLE"


class Langue(StrEnum):
    FR = "FR"
    FON = "FON"
    YORUBA = "YORUBA"
    BARIBA = "BARIBA"
    DENDI = "DENDI"
    ADJA = "ADJA"
    EN = "EN"


class StatutPaiement(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
