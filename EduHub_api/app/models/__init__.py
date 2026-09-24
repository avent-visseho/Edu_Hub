"""Enregistrement de tous les modèles ORM du système."""

from app.models.apprenant import (  # noqa: F401
    Apprenant,
    ApprenantParent,
    LienParente,
    Parent,
    Recompense,
    Sanction,
    StatutApprenant,
    TypeRecompense,
    TypeSanction,
)
from app.models.etablissement import (  # noqa: F401
    Batiment,
    Equipement,
    Etablissement,
    EtatEquipement,
    HistoriqueDirecteur,
    NiveauAccessibilite,
    Salle,
    TypeEquipement,
)
from app.models.identity import (  # noqa: F401
    Permission,
    Role,
    SessionUtilisateur,
    Utilisateur,
    UtilisateurRole,
    role_permission,
)
from app.models.organisation import CategorieStructure, Structure  # noqa: F401
from app.models.personnel import (  # noqa: F401
    AffectationEnseignant,
    CategoriePersonnel,
    Enseignant,
    EnseignantMatiere,
    EvenementCarriere,
    Personnel,
    SituationAgent,
    StatutAgent,
    TypeEvenementCarriere,
)
from app.models.referentiel import (  # noqa: F401
    Arrondissement,
    Commune,
    Cycle,
    Departement,
    Diplome,
    OrdreEnseignement,
    StatutEtablissement,
    TypeBourse,
    TypeDocument,
    TypeEtablissement,
    TypeExamen,
    TypeFormation,
    TypeHandicapRef,
    TypeSalle,
    Village,
)
from app.models.scolarite import (  # noqa: F401
    AnneeAcademique,
    Classe,
    DecisionFinAnnee,
    Filiere,
    Inscription,
    Matiere,
    MatiereNiveau,
    Niveau,
    Periode,
    RegimeScolarite,
    Serie,
    StatutInscription,
    Transfert,
    TypePeriode,
)
