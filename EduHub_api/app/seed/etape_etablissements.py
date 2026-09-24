"""Étape 3 — Établissements, bâtiments, salles, équipements et comptes."""

from __future__ import annotations

from datetime import date, timedelta

from app.core.enums import RoleCode
from app.core.security import hash_password
from app.models.etablissement import (
    Batiment,
    Equipement,
    Etablissement,
    EtatEquipement,
    HistoriqueDirecteur,
    NiveauAccessibilite,
    Salle,
    TypeEquipement,
)
from app.models.identity import Utilisateur, UtilisateurRole
from app.seed import donnees, scolaire
from app.seed.contexte import ContexteSeed, logger
from app.seed.etape_identite import (
    MOT_DE_PASSE_DEMO,
    construire_affectation,
    construire_utilisateur,
)

#: Répartition des établissements par type, exprimée en poids relatifs.
REPARTITION_TYPES: tuple[tuple[str, int], ...] = (
    ("EPP", 34),
    ("EM", 10),
    ("CEG", 22),
    ("LYCEE", 8),
    ("CS", 9),
    ("EPRIV", 6),
    ("LT", 4),
    ("CFP", 3),
    ("CAL", 2),
    ("UNIV", 1),
    ("IUT", 1),
)

#: Niveaux desservis par chaque type d'établissement.
NIVEAUX_PAR_TYPE: dict[str, tuple[str, ...]] = {
    "EM": ("PS", "MS", "GS"),
    "EPP": ("CI", "CP", "CE1", "CE2", "CM1", "CM2"),
    "EPRIV": ("CI", "CP", "CE1", "CE2", "CM1", "CM2"),
    "CEG": ("6E", "5E", "4E", "3E"),
    "LYCEE": ("6E", "5E", "4E", "3E", "2NDE", "1ERE", "TLE"),
    "CS": ("CI", "CP", "CE1", "CE2", "CM1", "CM2", "6E", "5E", "4E", "3E"),
    "LT": ("2NDE", "1ERE", "TLE"),
    "CFP": ("2NDE", "1ERE", "TLE"),
    "UNIV": ("L1", "L2", "L3", "M1", "M2"),
    "IUT": ("L1", "L2", "L3"),
    "CAL": (),
}

#: Équipements types et leur quantité indicative.
CATALOGUE_EQUIPEMENTS: tuple[tuple[str, str, int, int], ...] = (
    ("Ordinateur de bureau", TypeEquipement.ORDINATEUR, 5, 40),
    ("Vidéoprojecteur", TypeEquipement.VIDEOPROJECTEUR, 1, 6),
    ("Tableau blanc", TypeEquipement.TABLEAU, 4, 30),
    ("Imprimante", TypeEquipement.IMPRIMANTE, 1, 4),
    ("Table-banc", TypeEquipement.MOBILIER, 40, 400),
    ("Microscope", TypeEquipement.SCIENTIFIQUE, 2, 15),
    ("Ballon et matériel sportif", TypeEquipement.SPORTIF, 3, 20),
    ("Rampe d'accès et mobilier adapté", TypeEquipement.ACCESSIBILITE, 1, 5),
    ("Point d'accès réseau", TypeEquipement.RESEAU, 1, 8),
)


async def generer(ctx: ContexteSeed) -> None:
    await _etablissements(ctx)
    logger.info(
        "%d établissements générés avec leurs infrastructures.",
        len(ctx.cache("etablissement")),
    )


def _tirer_type(ctx: ContexteSeed) -> str:
    codes = [code for code, _ in REPARTITION_TYPES]
    poids = [poids for _, poids in REPARTITION_TYPES]
    return ctx.rng.choices(codes, weights=poids, k=1)[0]


def _nom_etablissement(ctx: ContexteSeed, type_code: str, commune: str) -> str:
    patron = ctx.choix(scolaire.PATRONS_ETABLISSEMENT)
    modeles = {
        "EM": f"École maternelle {patron} de {commune}",
        "EPP": f"EPP {commune} {ctx.entier(1, 4)}",
        "EPRIV": f"École privée {patron} de {commune}",
        "CEG": f"CEG {commune} {ctx.entier(1, 3)}",
        "LYCEE": f"Lycée {patron} de {commune}",
        "CS": f"Complexe scolaire {patron} de {commune}",
        "LT": f"Lycée technique de {commune}",
        "CFP": f"Centre de formation professionnelle de {commune}",
        "CAL": f"Centre d'alphabétisation de {commune}",
        "UNIV": f"Université de {commune}",
        "IUT": f"Institut universitaire de technologie de {commune}",
    }
    return modeles.get(type_code, f"Établissement {patron} de {commune}")


async def _etablissements(ctx: ContexteSeed) -> None:
    empreinte = hash_password(MOT_DE_PASSE_DEMO)
    volumetrie = ctx.volumetrie

    etablissements, batiments, salles, equipements, historiques = [], [], [], [], []
    utilisateurs, affectations = [], []

    codes_departements = [code for code, _, _, _, _ in donnees.DEPARTEMENTS]
    # Le Littoral et l'Atlantique concentrent davantage d'établissements.
    poids_departements = [
        3 if code in {"LIT", "ATL", "OUE", "BOR"} else 1 for code in codes_departements
    ]

    for index in range(1, volumetrie.etablissements + 1):
        code_departement = ctx.rng.choices(codes_departements, weights=poids_departements)[0]
        codes_communes = ctx.cache("communes_par_departement")[code_departement]
        code_commune = ctx.choix(codes_communes)
        nom_commune = _libelle_commune(code_commune)

        type_code = _tirer_type(ctx)
        statut_code = ctx.rng.choices(
            ["PUBLIC", "PRIVE_LAIC", "PRIVE_CONF", "COMMUNAUTAIRE", "CONVENTIONNE"],
            weights=[62, 14, 12, 7, 5],
        )[0]
        if type_code in {"EPRIV", "CS"} and statut_code == "PUBLIC":
            statut_code = "PRIVE_LAIC"

        code_etablissement = f"{type_code}-{code_departement}-{index:04d}"
        ident = ctx.nouvel_id()
        latitude, longitude = ctx.coordonnees(*_position_departement(code_departement), 0.4)

        capacite = ctx.entier(120, 1800)
        nombre_salles = max(4, capacite // ctx.entier(35, 60))
        accessibilite = ctx.rng.choices(list(NiveauAccessibilite), weights=[45, 30, 18, 7])[0]
        # Chaque département doit disposer d'au moins un centre de composition.
        eligible_centre = type_code in {"CEG", "LYCEE", "LT", "CS"}
        deja_centre = ctx.cache("centres_potentiels").get(code_departement)
        est_centre = eligible_centre and (not deja_centre or ctx.probabilite(0.45))
        sexe_directeur = ctx.sexe(0.35)
        nom_directeur, prenoms_directeur = ctx.identite(sexe_directeur)

        ctx.enregistrer("etablissement", code_etablissement, ident)
        ctx.cache("etablissement_info")[code_etablissement] = {
            "id": ident,
            "type": type_code,
            "departement": code_departement,
            "commune": code_commune,
            "nom": _nom_etablissement(ctx, type_code, nom_commune),
            "centre_examen": est_centre,
            "capacite": capacite,
        }
        if est_centre:
            ctx.cache("centres_potentiels").setdefault(code_departement, []).append(
                code_etablissement
            )
        ctx.cache("etablissements_par_type").setdefault(type_code, []).append(code_etablissement)

        etablissements.append(
            {
                "id": ident,
                "code": code_etablissement,
                "nom": ctx.cache("etablissement_info")[code_etablissement]["nom"],
                "sigle": type_code,
                "devise": "Travail — Discipline — Réussite",
                "type_etablissement_id": ctx.recuperer("type_etablissement", type_code),
                "statut_etablissement_id": ctx.recuperer("statut_etablissement", statut_code),
                "ministere_id": ctx.recuperer("structure", _ministere_du_type(type_code)),
                "direction_departementale_id": ctx.cache("ddeps_par_departement")[code_departement],
                "commune_id": ctx.recuperer("commune", code_commune),
                "arrondissement_id": ctx.choix(
                    ctx.cache("arrondissements_par_commune")[code_commune]
                ),
                "adresse": f"{nom_commune}, {code_departement}",
                "latitude": latitude,
                "longitude": longitude,
                "zone_rurale": code_departement not in {"LIT", "ATL", "OUE"}
                and ctx.probabilite(0.55),
                "directeur_nom": f"{prenoms_directeur} {nom_directeur}",
                "directeur_telephone": ctx.telephone(),
                "telephone": ctx.telephone(),
                "email": f"contact.{code_etablissement.lower()}@education.bj",
                "annee_creation": ctx.entier(1960, 2022),
                "capacite_accueil": capacite,
                "effectif_actuel": 0,
                "est_centre_examen": est_centre,
                "internat": type_code in {"LYCEE", "LT", "UNIV"} and ctx.probabilite(0.3),
                "cantine": ctx.probabilite(0.45),
                "electricite": ctx.probabilite(0.82),
                "eau_potable": ctx.probabilite(0.74),
                "connexion_internet": ctx.probabilite(0.38),
                "accessibilite": accessibilite,
                "actif": True,
                "supprime": False,
            }
        )

        historiques.append(
            {
                "id": ctx.nouvel_id(),
                "etablissement_id": ident,
                "nom_complet": f"{prenoms_directeur} {nom_directeur}",
                "matricule": f"DIR-{ctx.entier(10000, 99999)}",
                "date_debut": ctx.date_entre(date(2015, 9, 1), date(2024, 9, 1)),
                "date_fin": None,
                "acte_nomination": f"Arrêté n°{ctx.entier(100, 999)}/MESFTP/DC",
            }
        )

        _infrastructures(
            ctx,
            ident,
            code_etablissement,
            nombre_salles,
            accessibilite,
            batiments,
            salles,
            equipements,
        )

        # Compte administrateur de l'établissement.
        sexe = ctx.sexe(0.4)
        nom, prenoms = ctx.identite(sexe)
        compte = construire_utilisateur(
            ctx,
            email=f"admin.{code_etablissement.lower()}@eduhub.bj",
            nom=nom,
            prenoms=prenoms,
            sexe=sexe,
            empreinte=empreinte,
            telephone=ctx.telephone(),
        )
        utilisateurs.append(compte)
        affectations.append(
            construire_affectation(ctx, compte["id"], RoleCode.SCHOOL_ADMIN, etablissement_id=ident)
        )
        ctx.cache("admin_etablissement")[code_etablissement] = compte["id"]

    await ctx.inserer(Etablissement, etablissements)
    await ctx.inserer(Batiment, batiments)
    await ctx.inserer(Salle, salles)
    await ctx.inserer(Equipement, equipements)
    await ctx.inserer(HistoriqueDirecteur, historiques)
    await ctx.inserer(Utilisateur, utilisateurs)
    await ctx.inserer(UtilisateurRole, affectations)


def _infrastructures(
    ctx,
    etablissement_id,
    code_etablissement,
    nombre_salles,
    accessibilite,
    batiments,
    salles,
    equipements,
) -> None:
    """Crée bâtiments, salles et équipements d'un établissement."""
    nombre_batiments = max(1, nombre_salles // ctx.entier(4, 8))
    salles_restantes = nombre_salles
    salles_creees: list[dict] = []

    for numero in range(1, nombre_batiments + 1):
        id_batiment = ctx.nouvel_id()
        etages = ctx.entier(1, 2)
        batiments.append(
            {
                "id": id_batiment,
                "etablissement_id": etablissement_id,
                "code": f"{code_etablissement}-B{numero}",
                "nom": f"Bâtiment {chr(64 + numero)}",
                "nombre_etages": etages,
                "annee_construction": ctx.entier(1975, 2023),
                "etat": ctx.rng.choices(list(EtatEquipement), weights=[10, 45, 30, 12, 3])[0],
                "accessibilite": accessibilite,
            }
        )

        quota = (
            salles_restantes
            if numero == nombre_batiments
            else min(salles_restantes, ctx.entier(3, 8))
        )
        for _ in range(quota):
            type_salle = (
                "CLASSE"
                if ctx.probabilite(0.72)
                else ctx.choix(["LABO", "INFO", "BIBLIO", "ATELIER", "ADMIN", "PROFS"])
            )
            capacite = ctx.entier(30, 70) if type_salle == "CLASSE" else ctx.entier(15, 45)
            id_salle = ctx.nouvel_id()
            ligne = {
                "id": id_salle,
                "etablissement_id": etablissement_id,
                "batiment_id": id_batiment,
                "type_salle_id": ctx.recuperer("type_salle", type_salle),
                "code": f"{code_etablissement}-S{len(salles_creees) + 1:03d}",
                "nom": f"Salle {len(salles_creees) + 1}",
                "etage": ctx.entier(0, etages - 1) if etages > 1 else 0,
                "capacite": capacite,
                "capacite_examen": max(12, int(capacite * 0.6)),
                "superficie_m2": round(capacite * ctx.rng.uniform(1.1, 1.8), 1),
                "disponible": True,
                "accessibilite": accessibilite,
                "equipement_resume": "Tableau, tables-bancs"
                if type_salle == "CLASSE"
                else "Équipement spécialisé",
            }
            salles.append(ligne)
            salles_creees.append(ligne)
            if type_salle == "CLASSE":
                ctx.cache("salles_de_classe").setdefault(code_etablissement, []).append(id_salle)
            ctx.cache("salles_examen").setdefault(code_etablissement, []).append(
                (id_salle, ligne["nom"], ligne["capacite_examen"], f"Bâtiment {chr(64 + numero)}")
            )
        salles_restantes -= quota
        if salles_restantes <= 0:
            break

    for designation, type_equipement, minimum, maximum in CATALOGUE_EQUIPEMENTS:
        if not ctx.probabilite(0.62):
            continue
        salle = ctx.choix(salles_creees) if salles_creees else None
        equipements.append(
            {
                "id": ctx.nouvel_id(),
                "etablissement_id": etablissement_id,
                "salle_id": salle["id"] if salle else None,
                "reference": f"EQ-{ctx.suivant('equipement'):07d}",
                "designation": designation,
                "type_equipement": type_equipement,
                "quantite": ctx.entier(minimum, maximum),
                "etat": ctx.rng.choices(list(EtatEquipement), weights=[8, 40, 32, 15, 5])[0],
                "date_acquisition": ctx.date_entre(date(2016, 1, 1), date.today()),
                "valeur_acquisition": float(ctx.entier(25_000, 4_500_000)),
                "derniere_maintenance": ctx.date_entre(
                    date.today() - timedelta(days=720), date.today()
                ),
                "adapte_handicap": type_equipement == TypeEquipement.ACCESSIBILITE,
            }
        )


def _libelle_commune(code_commune: str) -> str:
    code_departement = code_commune.split("-")[0]
    index = int(code_commune.split("-")[1]) - 1
    return donnees.COMMUNES[code_departement][index]


def _position_departement(code: str) -> tuple[float, float]:
    for code_dep, _, _, latitude, longitude in donnees.DEPARTEMENTS:
        if code_dep == code:
            return latitude, longitude
    return 6.5, 2.4


def _ministere_du_type(type_code: str) -> str:
    if type_code in {"EM", "EPP", "EPRIV"}:
        return "MEMP"
    if type_code in {"UNIV", "IUT", "ENS"}:
        return "MESRS"
    return "MESFTP"


def niveaux_du_type(type_code: str) -> tuple[str, ...]:
    """Niveaux ouverts dans un type d'établissement donné."""
    return NIVEAUX_PAR_TYPE.get(type_code, ())
