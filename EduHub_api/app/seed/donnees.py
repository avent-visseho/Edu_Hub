"""Données de référence du Bénin fictif utilisé par le générateur.

Le découpage territorial reprend la géographie réelle du pays (12 départements,
77 communes) afin que la simulation soit crédible ; toutes les personnes,
établissements, notes et résultats sont en revanche entièrement fictifs.
"""

from __future__ import annotations

# ------------------------------------------------------------------
#  Découpage territorial : 12 départements, 77 communes
# ------------------------------------------------------------------

#: (code, libellé, chef-lieu, latitude, longitude)
DEPARTEMENTS: tuple[tuple[str, str, str, float, float], ...] = (
    ("ALI", "Alibori", "Kandi", 11.1342, 2.9386),
    ("ATA", "Atacora", "Natitingou", 10.3050, 1.3796),
    ("ATL", "Atlantique", "Allada", 6.6656, 2.1511),
    ("BOR", "Borgou", "Parakou", 9.3372, 2.6303),
    ("COL", "Collines", "Dassa-Zoumè", 7.7500, 2.1833),
    ("COU", "Couffo", "Aplahoué", 6.9333, 1.6833),
    ("DON", "Donga", "Djougou", 9.7085, 1.6660),
    ("LIT", "Littoral", "Cotonou", 6.3654, 2.4183),
    ("MON", "Mono", "Lokossa", 6.6388, 1.7167),
    ("OUE", "Ouémé", "Porto-Novo", 6.4969, 2.6289),
    ("PLA", "Plateau", "Pobè", 6.9800, 2.6647),
    ("ZOU", "Zou", "Abomey", 7.1826, 1.9912),
)

#: Communes par code de département.
COMMUNES: dict[str, tuple[str, ...]] = {
    "ALI": ("Banikoara", "Gogounou", "Kandi", "Karimama", "Malanville", "Ségbana"),
    "ATA": (
        "Boukoumbé",
        "Cobly",
        "Kérou",
        "Kouandé",
        "Matéri",
        "Natitingou",
        "Péhunco",
        "Tanguiéta",
        "Toucountouna",
    ),
    "ATL": (
        "Abomey-Calavi",
        "Allada",
        "Kpomassè",
        "Ouidah",
        "Sô-Ava",
        "Toffo",
        "Tori-Bossito",
        "Zè",
    ),
    "BOR": (
        "Bembèrèkè",
        "Kalalé",
        "N'Dali",
        "Nikki",
        "Parakou",
        "Pèrèrè",
        "Sinendé",
        "Tchaourou",
    ),
    "COL": ("Bantè", "Dassa-Zoumè", "Glazoué", "Ouèssè", "Savalou", "Savè"),
    "COU": ("Aplahoué", "Djakotomey", "Dogbo", "Klouékanmè", "Lalo", "Toviklin"),
    "DON": ("Bassila", "Copargo", "Djougou", "Ouaké"),
    "LIT": ("Cotonou",),
    "MON": ("Athiémé", "Bopa", "Comè", "Grand-Popo", "Houéyogbé", "Lokossa"),
    "OUE": (
        "Adjarra",
        "Adjohoun",
        "Aguégués",
        "Akpro-Missérété",
        "Avrankou",
        "Bonou",
        "Dangbo",
        "Porto-Novo",
        "Sèmè-Kpodji",
    ),
    "PLA": ("Adja-Ouèrè", "Ifangni", "Kétou", "Pobè", "Sakété"),
    "ZOU": (
        "Abomey",
        "Agbangnizoun",
        "Bohicon",
        "Covè",
        "Djidja",
        "Ouinhi",
        "Za-Kpota",
        "Zagnanado",
        "Zogbodomey",
    ),
}


# ------------------------------------------------------------------
#  Ministères, directions et structures
# ------------------------------------------------------------------

#: (code, sigle, libellé)
MINISTERES: tuple[tuple[str, str, str], ...] = (
    ("MEMP", "MEMP", "Ministère des Enseignements Maternel et Primaire"),
    (
        "MESFTP",
        "MESFTP",
        "Ministère des Enseignements Secondaire, Technique et de la Formation Professionnelle",
    ),
    (
        "MESRS",
        "MESRS",
        "Ministère de l'Enseignement Supérieur et de la Recherche Scientifique",
    ),
)

#: (code, sigle, libellé, code du ministère de rattachement, catégorie)
DIRECTIONS: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "DEC-MEMP",
        "DEC/MEMP",
        "Direction des Examens et Concours du MEMP",
        "MEMP",
        "DIRECTION_EXAMENS",
    ),
    (
        "DEC-MESFTP",
        "DEC/MESFTP",
        "Direction des Examens et Concours du MESFTP",
        "MESFTP",
        "DIRECTION_EXAMENS",
    ),
    (
        "DOB",
        "DOB",
        "Direction de l'Office du Baccalauréat",
        "MESRS",
        "DIRECTION_ORIENTATION",
    ),
)


# ------------------------------------------------------------------
#  Nomenclatures
# ------------------------------------------------------------------

ORDRES_ENSEIGNEMENT: tuple[tuple[str, str], ...] = (
    ("MATERNEL", "Enseignement maternel"),
    ("PRIMAIRE", "Enseignement primaire"),
    ("SECONDAIRE_GENERAL", "Enseignement secondaire général"),
    ("TECHNIQUE", "Enseignement technique et professionnel"),
    ("SUPERIEUR", "Enseignement supérieur"),
    ("ALPHABETISATION", "Alphabétisation et éducation non formelle"),
)

#: (code, libellé, code de l'ordre, durée en années)
CYCLES: tuple[tuple[str, str, str, int], ...] = (
    ("MATERNELLE", "Cycle maternel", "MATERNEL", 3),
    ("PRIMAIRE", "Cycle primaire", "PRIMAIRE", 6),
    ("PREMIER_CYCLE", "Premier cycle du secondaire", "SECONDAIRE_GENERAL", 4),
    ("SECOND_CYCLE", "Second cycle du secondaire", "SECONDAIRE_GENERAL", 3),
    ("CAP", "Cycle CAP", "TECHNIQUE", 3),
    ("BAC_TECHNIQUE", "Cycle baccalauréat technique", "TECHNIQUE", 3),
    ("LICENCE", "Licence", "SUPERIEUR", 3),
    ("MASTER", "Master", "SUPERIEUR", 2),
    ("DOCTORAT", "Doctorat", "SUPERIEUR", 3),
)

#: (code, libellé, code de l'ordre)
TYPES_ETABLISSEMENT: tuple[tuple[str, str, str], ...] = (
    ("EM", "École maternelle", "MATERNEL"),
    ("EPP", "École primaire publique", "PRIMAIRE"),
    ("EPRIV", "École primaire privée", "PRIMAIRE"),
    ("CEG", "Collège d'enseignement général", "SECONDAIRE_GENERAL"),
    ("LYCEE", "Lycée d'enseignement général", "SECONDAIRE_GENERAL"),
    ("CS", "Complexe scolaire privé", "SECONDAIRE_GENERAL"),
    ("LT", "Lycée technique", "TECHNIQUE"),
    ("CFP", "Centre de formation professionnelle", "TECHNIQUE"),
    ("UNIV", "Université", "SUPERIEUR"),
    ("ENS", "École normale supérieure", "SUPERIEUR"),
    ("IUT", "Institut universitaire de technologie", "SUPERIEUR"),
    ("CAL", "Centre d'alphabétisation", "ALPHABETISATION"),
)

STATUTS_ETABLISSEMENT: tuple[tuple[str, str], ...] = (
    ("PUBLIC", "Public"),
    ("PRIVE_LAIC", "Privé laïc"),
    ("PRIVE_CONF", "Privé confessionnel"),
    ("COMMUNAUTAIRE", "Communautaire"),
    ("CONVENTIONNE", "Conventionné"),
)

TYPES_SALLE: tuple[tuple[str, str], ...] = (
    ("CLASSE", "Salle de classe"),
    ("LABO", "Laboratoire"),
    ("INFO", "Salle informatique"),
    ("BIBLIO", "Bibliothèque"),
    ("ATELIER", "Atelier technique"),
    ("AMPHI", "Amphithéâtre"),
    ("REUNION", "Salle de réunion"),
    ("PROFS", "Salle des professeurs"),
    ("ADMIN", "Bureau administratif"),
    ("INFIRMERIE", "Infirmerie"),
    ("CANTINE", "Cantine"),
    ("INTERNAT", "Dortoir d'internat"),
    ("SPORT", "Installation sportive"),
    ("NUMERIQUE", "Salle numérique"),
)

#: (code, libellé, extensions, taille maximale en Ko)
TYPES_DOCUMENT: tuple[tuple[str, str, str, int], ...] = (
    ("PHOTO", "Photo d'identité", "jpg,jpeg,png", 2048),
    ("ACTE_NAISSANCE", "Acte de naissance", "pdf,jpg,jpeg,png", 5120),
    ("CERTIFICAT", "Certificat", "pdf,jpg,jpeg,png", 5120),
    ("DIPLOME", "Diplôme", "pdf,jpg,jpeg,png", 5120),
    ("RELEVE", "Relevé de notes", "pdf,jpg,jpeg,png", 5120),
    ("ATTESTATION", "Attestation", "pdf,jpg,jpeg,png", 5120),
    ("CERTIFICAT_MEDICAL", "Certificat médical", "pdf,jpg,jpeg,png", 5120),
    ("QUITTANCE", "Quittance de paiement", "pdf,jpg,jpeg,png", 2048),
    ("AUTORISATION", "Autorisation parentale", "pdf,jpg,jpeg,png", 5120),
    ("CNI", "Pièce d'identité", "pdf,jpg,jpeg,png", 5120),
    ("ACTE_ADMIN", "Document administratif", "pdf,doc,docx", 10240),
    ("AUTRE", "Autre pièce", "pdf,jpg,jpeg,png,doc,docx", 10240),
)

#: (code, libellé, est un concours, code de l'ordre)
TYPES_EXAMEN: tuple[tuple[str, str, bool, str], ...] = (
    ("CEP", "Certificat d'études primaires", False, "PRIMAIRE"),
    ("BEPC", "Brevet d'études du premier cycle", False, "SECONDAIRE_GENERAL"),
    ("BAC", "Baccalauréat", False, "SECONDAIRE_GENERAL"),
    ("CAP", "Certificat d'aptitude professionnelle", False, "TECHNIQUE"),
    ("BEPC_TECH", "BEPC technique", False, "TECHNIQUE"),
    ("BAC_TECH", "Baccalauréat technique", False, "TECHNIQUE"),
    ("EXAM_UNIV", "Examen universitaire", False, "SUPERIEUR"),
    ("EXAM_BLANC", "Examen blanc", False, "SECONDAIRE_GENERAL"),
    ("CERT_PRO", "Certification professionnelle", False, "TECHNIQUE"),
    ("CONC_ENTREE_6E", "Concours d'entrée en sixième", True, "PRIMAIRE"),
    ("CONC_ENS", "Concours d'entrée à l'ENS", True, "SUPERIEUR"),
    ("CONC_RECRUT", "Concours de recrutement d'enseignants", True, "SECONDAIRE_GENERAL"),
    ("CONC_ADMIN", "Concours administratif", True, "SUPERIEUR"),
)

#: (code, libellé, montant indicatif mensuel)
TYPES_BOURSE: tuple[tuple[str, str, float], ...] = (
    ("EXCELLENCE", "Bourse d'excellence", 60000.0),
    ("SOCIALE", "Bourse sociale", 35000.0),
    ("MERITE", "Bourse au mérite", 45000.0),
    ("HANDICAP", "Bourse inclusion et handicap", 50000.0),
    ("FILLE_SCIENCE", "Bourse filles et sciences", 55000.0),
    ("ETRANGERE", "Bourse de mobilité internationale", 150000.0),
    ("RECHERCHE", "Allocation de recherche", 120000.0),
)

TYPES_FORMATION: tuple[tuple[str, str], ...] = (
    ("INITIALE", "Formation initiale"),
    ("CONTINUE", "Formation continue"),
    ("PROFESSIONNELLE", "Formation professionnelle"),
    ("ALTERNANCE", "Formation en alternance"),
    ("ALPHABETISATION", "Alphabétisation"),
    ("DISTANCE", "Formation à distance"),
)

#: (code, libellé, catégorie, aménagements)
TYPES_HANDICAP: tuple[tuple[str, str, str, str], ...] = (
    ("AUCUN", "Aucun besoin spécifique", "AUCUN", ""),
    (
        "VISUEL_MALVOYANT",
        "Déficience visuelle — malvoyance",
        "VISUEL",
        "Documents en grands caractères, éclairage renforcé, tiers temps",
    ),
    (
        "VISUEL_AVEUGLE",
        "Déficience visuelle — cécité",
        "VISUEL",
        "Sujets en braille, secrétaire, synthèse vocale, tiers temps",
    ),
    (
        "AUDITIF",
        "Déficience auditive",
        "AUDITIF",
        "Consignes écrites, interprète en langue des signes, sous-titrage",
    ),
    (
        "MOTEUR",
        "Déficience motrice",
        "MOTEUR",
        "Salle accessible au rez-de-chaussée, mobilier adapté, secrétaire",
    ),
    (
        "COGNITIF",
        "Trouble cognitif ou de l'apprentissage",
        "COGNITIF",
        "Énoncés simplifiés, tiers temps, salle au calme",
    ),
    ("LANGAGE", "Trouble du langage", "LANGAGE", "Épreuves écrites privilégiées, tiers temps"),
    ("MULTIPLE", "Handicaps multiples", "MULTIPLE", "Dispositif individualisé"),
)

#: (code, libellé, niveau de qualification, code du cycle)
DIPLOMES: tuple[tuple[str, str, str, str], ...] = (
    ("CEP", "Certificat d'études primaires", "Niveau 1", "PRIMAIRE"),
    ("BEPC", "Brevet d'études du premier cycle", "Niveau 2", "PREMIER_CYCLE"),
    ("BAC", "Baccalauréat", "Niveau 4", "SECOND_CYCLE"),
    ("CAP", "Certificat d'aptitude professionnelle", "Niveau 3", "CAP"),
    ("BAC_TECH", "Baccalauréat technique", "Niveau 4", "BAC_TECHNIQUE"),
    ("LICENCE", "Licence", "Niveau 6", "LICENCE"),
    ("MASTER", "Master", "Niveau 7", "MASTER"),
    ("DOCTORAT", "Doctorat", "Niveau 8", "DOCTORAT"),
)
