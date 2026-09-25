# EduHub — Système Intégré de Gestion de l'Éducation

Plateforme numérique intégrée simulant la gestion complète d'un système éducatif
national : de l'inscription d'un apprenant jusqu'à son insertion professionnelle.

> Prototype **totalement autonome** : aucune dépendance à EducMaster, à une API
> ministérielle ou à une base gouvernementale. Toutes les données sont fictives
> et générées par le moteur de simulation intégré.

---

## Sommaire

- [Périmètre](#périmètre)
- [Architecture](#architecture)
- [Démarrage rapide](#démarrage-rapide)
- [Structure du dépôt](#structure-du-dépôt)
- [Comptes de démonstration](#comptes-de-démonstration)

---

## Périmètre

18 domaines fonctionnels :

| # | Domaine | # | Domaine |
|---|---------|---|---------|
| 01 | Identité et utilisateurs | 10 | Diplômes et certifications |
| 02 | Organisation institutionnelle | 11 | Orientation |
| 03 | Établissements | 12 | Vie étudiante |
| 04 | Apprenants | 13 | Ressources et services |
| 05 | Enseignants et personnel | 14 | Projets, recherche, innovation |
| 06 | Scolarité | 15 | Stages et emploi |
| 07 | Pédagogie | 16 | Infrastructures |
| 08 | Évaluations et bulletins | 17 | Gouvernance et statistiques |
| 09 | Examens et concours | 18 | IA et aide à la décision |

Portés par **10 moteurs génériques réutilisables** : Identity, Organization,
Workflow, Document, Notification, Search, Analytics, Reporting, Audit, AI.

### Chaîne institutionnelle

```
SUPER_ADMIN
     └── Ministère (MEMP / MESFTP / MESRS)
             └── Direction (DEC / DOB)
                     └── Direction Départementale (DDEPS)
                             └── Établissement
                                     └── Candidat / Apprenant
```

---

## Architecture

```
                         Next.js / React / TypeScript
                                      │
                              FastAPI / Python 3.12
                                      │
                 ┌────────────────────┼────────────────────┐
                 │                    │                    │
           Domaines métiers      10 moteurs           Simulation
                 │                    │                    │
                 └────────────────────┼────────────────────┘
                                      │
                  ┌───────────────────┼───────────────────┐
                  │                   │                   │
             PostgreSQL 16          Redis              MinIO (S3)
```

| Couche | Technologie |
|--------|-------------|
| API | FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Base | PostgreSQL 16 |
| Cache / files | Redis 7 |
| Stockage objet | MinIO (compatible S3) |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS 4 |
| Données | TanStack Query, React Hook Form, Zod, Recharts |

---

## Démarrage rapide

### 1. Infrastructure

```bash
cp .env.example .env
make infra          # postgres, redis et minio
```

Les ports sont décalés pour cohabiter avec d'autres projets :
PostgreSQL **5442**, Redis **6389**, MinIO **9010** (console **9011**).

### 2. Backend

```bash
cd EduHub_api
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env

alembic upgrade head          # crée les 152 tables
python -m app.seed --echelle small
uvicorn app.main:app --reload --port 8000
```

- API : http://localhost:8000
- Documentation interactive : http://localhost:8000/docs

### 3. Frontend

```bash
cd EduHub_front
npm install
cp .env.example .env.local
npm run dev
```

- Application : http://localhost:3000

### Volumes de données

`python -m app.seed --echelle <taille>` :

| Échelle | Établissements | Apprenants | Enseignants | Durée indicative |
|---------|----------------|------------|-------------|------------------|
| `tiny` | 12 | 400 | 60 | ~30 s |
| `small` | 60 | 2 500 | 300 | ~2 min |
| `medium` | 250 | 12 000 | 1 400 | ~10 min |
| `large` | 1 000 | 50 000 | 5 500 | ~45 min |

Pour repartir de zéro : `make reseed` (détruit la base, migre, régénère).

### Tout via Docker

```bash
make up             # postgres, redis, minio, api, front
make migrate
make seed
```

---

## Structure du dépôt

```
EduHub/
├── EduHub_api/          API FastAPI (domaines + moteurs)
├── EduHub_front/        Application Next.js
├── infra/               Docker, configuration d'infrastructure
├── docs/                Spécifications et documentation
├── docker-compose.yml
└── Makefile
```

---

## Comptes de démonstration

Après `make seed`, tous les comptes partagent le mot de passe `EduHub2026!`.

| Rôle | Identifiant |
|------|-------------|
| Super administrateur | `super.admin@eduhub.bj` |
| Compte de démonstration | `demo@education.local` |
| Ministère — enseignement primaire | `admin.memp@eduhub.bj` |
| Ministère — secondaire et technique | `admin.mesftp@eduhub.bj` |
| Ministère — enseignement supérieur | `admin.mesrs@eduhub.bj` |
| Direction des examens (MEMP) | `admin.dec.memp@eduhub.bj` |
| Direction des examens (MESFTP) | `admin.dec.mesftp@eduhub.bj` |
| Office du baccalauréat | `admin.dob@eduhub.bj` |
| Administrateur des examens | `examens.dec.memp@eduhub.bj` |
| Direction départementale | `admin.ddeps.atlantique@eduhub.bj` |

Un compte est également créé pour chaque établissement
(`admin.<code-etablissement>@eduhub.bj`) et pour chaque enseignant. Les
identifiants exacts figurent dans la table `utilisateurs` après le seed :

```bash
docker exec eduhub-postgres psql -U eduhub -d eduhub \
  -c "SELECT email FROM utilisateurs ORDER BY email LIMIT 40"
```

---

## Parcours de démonstration

1. **Connexion** en super administrateur — la page de connexion propose les
   comptes en un clic.
2. **Tableau de bord national** : effectifs, parité, inclusion, distribution des
   moyennes, taux de réussite par session, alertes du moteur de règles.
3. **Apprenants** → ouvrir un dossier : parcours, bulletins, examens, diplômes,
   assiduité, bourses, transport, projets, stages, compétences.
4. **Classes** → choisir une classe : emploi du temps hebdomadaire, assiduité,
   puis *Générer les bulletins* — moyennes pondérées, rangs et appréciations
   sont recalculés en direct.
5. **Classes** → *Faire l'appel* : feuille d'appel d'une séance, présents,
   retards et absences justifiées ou non ; la synthèse d'assiduité suit.
6. **Inscriptions** : répartition des dossiers par étape, puis ouvrir une
   inscription pour appliquer une transition — seules les actions autorisées
   depuis l'étape courante sont proposées, et chacune est historisée.
7. **Évaluations** → ouvrir une évaluation : saisie des notes élève par élève
   (absence, non-rendu, dispense, fraude), statistiques en direct, puis la
   chaîne de validation enseignant → établissement → publication.
8. **Bulletins** → ouvrir un bulletin → *Imprimer* : PDF officiel avec QR code.
9. **Sessions d'examen** → ouvrir une session : répartition des candidats par
   centre et par salle, convocations, copies anonymées, délibération avec
   repêchage, publication des résultats, délivrance des diplômes.
10. **Centres de composition** → ouvrir un centre : salles, plages de places,
   liste d'émargement exportable en CSV.
11. **Candidats** → ouvrir un dossier : pièces jointes et leur vérification,
    affectation de composition, notes aux épreuves, décision du jury, actions
    de workflow autorisées et historique des transitions.
12. **Contentieux** : recours déposés après publication, et leur instruction.
13. **Recherche avancée** : constructeur visuel, puis onglet *Question en
    français* — « Montre-moi les élèves des CEG ayant au moins 17 de moyenne en
    mathématiques. »
14. **Correction des copies** : choisir une épreuve, suivre l'avancement des
    correcteurs, noter des copies anonymées en première ou en seconde lecture —
    un écart de trois points déclenche une troisième correction — puis lire les
    notes définitives, rattachées au candidat une fois la correction faite.
15. **Jurys et surveillance** : composition des jurys de délibération, ajout
    d'un membre, et agents affectés aux centres par rôle.
16. **Gouvernance** : organigramme ministère → direction → direction
    départementale, règles métier et bouton *Simuler* qui les confronte aux
    données réelles sans rien modifier, alertes et leur traitement.
17. **Cartographie** : implantation nationale des établissements.
18. **Infrastructures** : bâtiments, salles et équipements, avec leur état et
    leur niveau d'accessibilité.
19. **Transport** : suivi des trajets, prochain arrêt, places disponibles.
20. **Référentiels** : les nomenclatures partagées par tout le système. Tenter
    de retirer un type de salle utilisé par 890 salles est refusé, avec le
    décompte exact des enregistrements concernés.
21. **Vérification publique** : coller le code d'un diplôme sur `/verification`.

À tout moment, le bouton **Accessibilité** de l'en-tête permet de basculer en
contraste élevé, grande police, interface simplifiée, lecture vocale ou
économie de données.

---

## Accessibilité

Conçu pour être utilisable par tous : contraste élevé, grande police, lecture
vocale, navigation clavier complète, compatibilité lecteur d'écran, sous-titres,
pictogrammes, **interface simplifiée** pour les personnes peu alphabétisées, et
fonctionnement en connectivité limitée (PWA, cache, mode hors ligne partiel).
