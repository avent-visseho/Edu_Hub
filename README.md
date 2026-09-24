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

### Avec Docker (recommandé)

```bash
make up          # démarre postgres, redis, minio, api, front
make migrate     # applique les migrations
make seed        # génère le Bénin fictif complet
```

- API : http://localhost:8000 — documentation : http://localhost:8000/docs
- Front : http://localhost:3000
- MinIO : http://localhost:9001

### En local

```bash
# Backend
cd EduHub_api
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload

# Frontend
cd EduHub_front
npm install
cp .env.example .env.local
npm run dev
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
| Ministère (MEMP) | `admin.memp@eduhub.bj` |
| Direction des examens | `admin.dec@eduhub.bj` |
| Direction départementale | `admin.ddeps.atlantique@eduhub.bj` |
| Établissement | `admin.ceg1.calavi@eduhub.bj` |
| Enseignant | `enseignant.demo@eduhub.bj` |
| Apprenant | `eleve.demo@eduhub.bj` |
| Parent | `parent.demo@eduhub.bj` |
| Candidat libre | `candidat.demo@eduhub.bj` |
| Démonstration | `demo@education.local` |

---

## Accessibilité

Conçu pour être utilisable par tous : contraste élevé, grande police, lecture
vocale, navigation clavier complète, compatibilité lecteur d'écran, sous-titres,
pictogrammes, **interface simplifiée** pour les personnes peu alphabétisées, et
fonctionnement en connectivité limitée (PWA, cache, mode hors ligne partiel).
