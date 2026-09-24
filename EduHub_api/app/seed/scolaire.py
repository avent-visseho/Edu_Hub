"""Données scolaires de référence : niveaux, séries, filières et matières."""

from __future__ import annotations

# ------------------------------------------------------------------
#  Niveaux — (code, libellé, code du cycle, rang)
# ------------------------------------------------------------------

NIVEAUX: tuple[tuple[str, str, str, int], ...] = (
    ("PS", "Petite section", "MATERNELLE", 1),
    ("MS", "Moyenne section", "MATERNELLE", 2),
    ("GS", "Grande section", "MATERNELLE", 3),
    ("CI", "Cours d'initiation", "PRIMAIRE", 4),
    ("CP", "Cours préparatoire", "PRIMAIRE", 5),
    ("CE1", "Cours élémentaire 1", "PRIMAIRE", 6),
    ("CE2", "Cours élémentaire 2", "PRIMAIRE", 7),
    ("CM1", "Cours moyen 1", "PRIMAIRE", 8),
    ("CM2", "Cours moyen 2", "PRIMAIRE", 9),
    ("6E", "Sixième", "PREMIER_CYCLE", 10),
    ("5E", "Cinquième", "PREMIER_CYCLE", 11),
    ("4E", "Quatrième", "PREMIER_CYCLE", 12),
    ("3E", "Troisième", "PREMIER_CYCLE", 13),
    ("2NDE", "Seconde", "SECOND_CYCLE", 14),
    ("1ERE", "Première", "SECOND_CYCLE", 15),
    ("TLE", "Terminale", "SECOND_CYCLE", 16),
    ("L1", "Licence 1", "LICENCE", 17),
    ("L2", "Licence 2", "LICENCE", 18),
    ("L3", "Licence 3", "LICENCE", 19),
    ("M1", "Master 1", "MASTER", 20),
    ("M2", "Master 2", "MASTER", 21),
)

#: Niveaux du second cycle, sur lesquels s'applique la logique des séries.
NIVEAUX_SECOND_CYCLE: tuple[str, ...] = ("2NDE", "1ERE", "TLE")

#: Niveau conduisant à chaque examen national.
NIVEAU_EXAMEN: dict[str, str] = {"CM2": "CEP", "3E": "BEPC", "TLE": "BAC"}


# ------------------------------------------------------------------
#  Séries — (code, libellé, code du cycle, technique)
# ------------------------------------------------------------------

SERIES: tuple[tuple[str, str, str, bool], ...] = (
    ("A1", "Série A1 — Lettres et langues", "SECOND_CYCLE", False),
    ("A2", "Série A2 — Lettres et sciences humaines", "SECOND_CYCLE", False),
    ("B", "Série B — Sciences économiques et sociales", "SECOND_CYCLE", False),
    ("C", "Série C — Mathématiques et sciences physiques", "SECOND_CYCLE", False),
    ("D", "Série D — Mathématiques et sciences de la nature", "SECOND_CYCLE", False),
    ("E", "Série E — Mathématiques et techniques", "SECOND_CYCLE", False),
    ("F1", "Série F1 — Construction mécanique", "BAC_TECHNIQUE", True),
    ("F2", "Série F2 — Électronique", "BAC_TECHNIQUE", True),
    ("F3", "Série F3 — Électrotechnique", "BAC_TECHNIQUE", True),
    ("F4", "Série F4 — Génie civil", "BAC_TECHNIQUE", True),
    ("G1", "Série G1 — Techniques administratives", "BAC_TECHNIQUE", True),
    ("G2", "Série G2 — Techniques quantitatives de gestion", "BAC_TECHNIQUE", True),
    ("G3", "Série G3 — Techniques commerciales", "BAC_TECHNIQUE", True),
)

#: Séries générales ouvertes au baccalauréat.
SERIES_GENERALES: tuple[str, ...] = ("A1", "A2", "B", "C", "D", "E")


# ------------------------------------------------------------------
#  Filières — (code, libellé, code du diplôme, durée)
# ------------------------------------------------------------------

FILIERES: tuple[tuple[str, str, str, int], ...] = (
    ("INFO", "Informatique et systèmes d'information", "LICENCE", 3),
    ("GESTION", "Sciences de gestion", "LICENCE", 3),
    ("DROIT", "Droit", "LICENCE", 3),
    ("ECO", "Sciences économiques", "LICENCE", 3),
    ("AGRO", "Agronomie", "LICENCE", 3),
    ("SANTE", "Sciences de la santé", "LICENCE", 3),
    ("LETTRES", "Lettres modernes", "LICENCE", 3),
    ("MATH", "Mathématiques appliquées", "LICENCE", 3),
    ("GENIE_CIVIL", "Génie civil", "BAC_TECH", 3),
    ("ELECTRO", "Électrotechnique", "BAC_TECH", 3),
    ("MECA", "Construction mécanique", "CAP", 3),
    ("COMPTA", "Comptabilité et gestion", "CAP", 3),
    ("HOTEL", "Hôtellerie et restauration", "CAP", 3),
    ("COUTURE", "Habillement et mode", "CAP", 3),
    ("EDUC", "Sciences de l'éducation", "LICENCE", 3),
)


# ------------------------------------------------------------------
#  Matières — (code, libellé, abréviation, domaine, coefficient, volume horaire)
# ------------------------------------------------------------------

MATIERES: tuple[tuple[str, str, str, str, float, int], ...] = (
    ("MATH", "Mathématiques", "MATH", "Sciences", 4.0, 5),
    ("FRA", "Français", "FR", "Lettres", 4.0, 5),
    ("ANG", "Anglais", "ANG", "Langues", 2.0, 3),
    ("SVT", "Sciences de la vie et de la Terre", "SVT", "Sciences", 3.0, 3),
    ("PC", "Physique — Chimie — Technologie", "PCT", "Sciences", 3.0, 4),
    ("HG", "Histoire — Géographie", "HG", "Sciences humaines", 2.0, 3),
    ("PHILO", "Philosophie", "PHI", "Sciences humaines", 3.0, 3),
    ("ECO", "Sciences économiques et sociales", "SES", "Sciences humaines", 3.0, 4),
    ("INFO", "Informatique", "INFO", "Sciences", 2.0, 2),
    ("EPS", "Éducation physique et sportive", "EPS", "Sport", 1.0, 2),
    ("ESP", "Espagnol", "ESP", "Langues", 2.0, 3),
    ("ALL", "Allemand", "ALL", "Langues", 2.0, 3),
    ("ECM", "Éducation civique et morale", "ECM", "Sciences humaines", 1.0, 1),
    ("ART", "Éducation artistique", "ART", "Arts", 1.0, 1),
    ("LECTURE", "Lecture et expression", "LEC", "Lettres", 3.0, 5),
    ("CALCUL", "Calcul et raisonnement", "CAL", "Sciences", 3.0, 5),
    ("EVEIL", "Éveil scientifique", "EVE", "Sciences", 2.0, 2),
    ("COMPTA", "Comptabilité générale", "CPT", "Gestion", 4.0, 5),
    ("DROIT", "Droit et législation", "DRT", "Gestion", 2.0, 2),
    ("TECHNO", "Technologie professionnelle", "TEC", "Technique", 4.0, 6),
    ("DESSIN", "Dessin technique", "DES", "Technique", 3.0, 4),
    ("ATELIER", "Travaux d'atelier", "ATL", "Technique", 4.0, 8),
)

#: Matières enseignées selon le niveau ou la série.
PROGRAMME_PAR_NIVEAU: dict[str, tuple[str, ...]] = {
    "MATERNELLE": ("LECTURE", "CALCUL", "EVEIL", "ART", "EPS"),
    "PRIMAIRE": ("LECTURE", "CALCUL", "FRA", "MATH", "EVEIL", "HG", "ECM", "EPS", "ART"),
    "PREMIER_CYCLE": ("FRA", "MATH", "ANG", "SVT", "PC", "HG", "ECM", "EPS", "INFO"),
}

#: Matières par série du second cycle, avec leur coefficient propre.
PROGRAMME_PAR_SERIE: dict[str, tuple[tuple[str, float], ...]] = {
    "A1": (("FRA", 5), ("PHILO", 4), ("ANG", 4), ("ESP", 3), ("HG", 3), ("MATH", 1), ("EPS", 1)),
    "A2": (("FRA", 5), ("PHILO", 4), ("HG", 4), ("ANG", 3), ("ECO", 2), ("MATH", 2), ("EPS", 1)),
    "B": (("ECO", 5), ("MATH", 4), ("HG", 3), ("FRA", 3), ("PHILO", 3), ("ANG", 2), ("EPS", 1)),
    "C": (("MATH", 6), ("PC", 5), ("SVT", 3), ("FRA", 2), ("ANG", 2), ("PHILO", 2), ("EPS", 1)),
    "D": (("SVT", 5), ("MATH", 4), ("PC", 4), ("FRA", 2), ("ANG", 2), ("PHILO", 2), ("EPS", 1)),
    "E": (("MATH", 5), ("PC", 5), ("DESSIN", 3), ("FRA", 2), ("ANG", 2), ("PHILO", 2), ("EPS", 1)),
    "F1": (("TECHNO", 6), ("MATH", 4), ("PC", 4), ("DESSIN", 4), ("FRA", 2), ("ANG", 2)),
    "F2": (("TECHNO", 6), ("MATH", 4), ("PC", 5), ("INFO", 3), ("FRA", 2), ("ANG", 2)),
    "F3": (("TECHNO", 6), ("PC", 5), ("MATH", 4), ("DESSIN", 3), ("FRA", 2), ("ANG", 2)),
    "F4": (("TECHNO", 6), ("DESSIN", 5), ("MATH", 4), ("PC", 3), ("FRA", 2), ("ANG", 2)),
    "G1": (("COMPTA", 5), ("DROIT", 4), ("FRA", 4), ("ANG", 3), ("ECO", 3), ("INFO", 2)),
    "G2": (("COMPTA", 6), ("MATH", 4), ("ECO", 4), ("DROIT", 3), ("FRA", 2), ("ANG", 2)),
    "G3": (("ECO", 5), ("COMPTA", 4), ("DROIT", 3), ("FRA", 3), ("ANG", 3), ("INFO", 2)),
}


# ------------------------------------------------------------------
#  Anthroponymie béninoise
# ------------------------------------------------------------------

NOMS: tuple[str, ...] = (
    "ADJOVI",
    "AGBODJAN",
    "AHOUANSOU",
    "AKPOVI",
    "ALLAGBE",
    "AMOUSSOU",
    "ASSOGBA",
    "AVOCE",
    "AYIVI",
    "BIO",
    "BOKO",
    "DAGBA",
    "DAKPOGAN",
    "DANSOU",
    "DEGBEY",
    "DJIMA",
    "DOSSOU",
    "FASSINOU",
    "GBAGUIDI",
    "GNANSOUNOU",
    "HODONOU",
    "HOUNKPE",
    "HOUNSOU",
    "KOUAGOU",
    "KPOGNON",
    "LOKOSSOU",
    "MENSAH",
    "MONTCHO",
    "NOUATIN",
    "OKE",
    "OLOU",
    "ORIOU",
    "QUENUM",
    "SAGBO",
    "SALAMI",
    "SOGLO",
    "SOSSOU",
    "TCHIBOZO",
    "TOGNON",
    "VIGAN",
    "YAROU",
    "ZINSOU",
    "ZOSSOU",
    "ADAMOU",
    "BACHABI",
    "GADO",
    "IDRISSOU",
    "MAMA",
    "SEIDOU",
    "TIDJANI",
)

PRENOMS_MASCULINS: tuple[str, ...] = (
    "Ablam",
    "Achille",
    "Adéchina",
    "Alphonse",
    "Ange",
    "Antoine",
    "Armand",
    "Aurélien",
    "Bachirou",
    "Benoît",
    "Bertin",
    "Boris",
    "Christian",
    "Clément",
    "Cyrille",
    "Damien",
    "Désiré",
    "Dieudonné",
    "Emmanuel",
    "Éric",
    "Fabrice",
    "Félicien",
    "Firmin",
    "Franck",
    "Gaston",
    "Gérard",
    "Gilbert",
    "Hervé",
    "Hyacinthe",
    "Ibrahim",
    "Isidore",
    "Jean",
    "Jocelyn",
    "Joseph",
    "Judicaël",
    "Karim",
    "Landry",
    "Laurent",
    "Marcel",
    "Mathias",
    "Moussa",
    "Norbert",
    "Olivier",
    "Pascal",
    "Patrice",
    "Raoul",
    "Rodrigue",
    "Serge",
    "Sylvain",
    "Théophile",
    "Ulrich",
    "Valentin",
    "Wilfried",
    "Yannick",
)

PRENOMS_FEMININS: tuple[str, ...] = (
    "Adèle",
    "Afiavi",
    "Aïcha",
    "Alice",
    "Amina",
    "Angèle",
    "Antoinette",
    "Ariane",
    "Awa",
    "Bernadette",
    "Blandine",
    "Carine",
    "Céline",
    "Chantal",
    "Clarisse",
    "Colette",
    "Dorcas",
    "Édith",
    "Elisabeth",
    "Estelle",
    "Fatima",
    "Félicité",
    "Flore",
    "Gisèle",
    "Grâce",
    "Hortense",
    "Ines",
    "Irène",
    "Jacqueline",
    "Josiane",
    "Julienne",
    "Laure",
    "Léonie",
    "Lucie",
    "Marthe",
    "Micheline",
    "Nadège",
    "Nathalie",
    "Odette",
    "Pascaline",
    "Perpétue",
    "Prisca",
    "Rachelle",
    "Reine",
    "Rosine",
    "Sandrine",
    "Sylvie",
    "Thérèse",
    "Vanessa",
    "Véronique",
    "Viviane",
    "Yolande",
    "Zita",
)

#: Éléments de nom d'établissement, pour composer des dénominations plausibles.
PATRONS_ETABLISSEMENT: tuple[str, ...] = (
    "Sainte-Rita",
    "Saint-Michel",
    "Notre-Dame",
    "Saint-Joseph",
    "Sainte-Marie",
    "Le Progrès",
    "L'Espérance",
    "Les Pionniers",
    "L'Excellence",
    "La Concorde",
    "Wologuèdè",
    "Houéyiho",
    "Gbégamey",
    "Fidjrossè",
    "Vèdoko",
    "Agla",
    "Zogbohouè",
    "Sègbèya",
    "Ladji",
    "Akpakpa",
    "Cadjèhoun",
    "Tokplégbé",
)

#: Secteurs d'activité des entreprises partenaires.
SECTEURS_ENTREPRISE: tuple[str, ...] = (
    "Agroalimentaire",
    "Banque et assurance",
    "BTP et génie civil",
    "Commerce",
    "Énergie",
    "Éducation et formation",
    "Informatique et numérique",
    "Logistique et transport",
    "Santé",
    "Télécommunications",
    "Textile",
    "Tourisme et hôtellerie",
    "Agriculture",
    "Microfinance",
    "Médias",
)

#: Domaines de projets étudiants et de recherche.
DOMAINES_PROJET: tuple[str, ...] = (
    "Agriculture durable",
    "Accès à l'eau potable",
    "Santé communautaire",
    "Énergie solaire",
    "Numérique éducatif",
    "Entrepreneuriat",
    "Gestion des déchets",
    "Inclusion et handicap",
    "Langues nationales",
    "Alphabétisation",
    "Intelligence artificielle",
    "Mobilité urbaine",
    "Sécurité alimentaire",
    "Changement climatique",
    "Patrimoine culturel",
)
