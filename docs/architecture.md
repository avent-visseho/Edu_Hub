# Architecture d'EduHub

## Principe directeur

Ne pas construire cent trente fonctionnalités comme cent trente projets, mais
dix **moteurs génériques** que les domaines métiers réutilisent.

```
                            Interface Next.js
                                    │
                            API FastAPI (/api/v1)
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
   Domaines métiers            Dix moteurs             Simulation
   (18 domaines)               génériques              (générateur)
          │                         │                         │
          └─────────────────────────┼─────────────────────────┘
                                    │
                  PostgreSQL 16 · Redis 7 · MinIO (S3)
```

---

## Les dix moteurs

| Moteur | Module | Rôle |
|--------|--------|------|
| Identité | `app/engines/identity.py` | Authentification, rôles, permissions, portées |
| Organisation | `app/models/organisation.py` | Arbre ministère → direction → DDEPS |
| Workflow | `app/engines/workflow.py` | Machines à états et historisation des transitions |
| Documents | `app/engines/document.py` | Dépôt, versionnement, validation des pièces |
| Stockage | `app/engines/storage.py` | MinIO/S3 avec repli sur disque local |
| Notifications | `app/engines/notification.py` | Diffusion multicanal et accessible |
| Recherche | `app/engines/search.py` | Constructeur de requêtes typé et sûr |
| Analytique | `app/engines/analytics.py` | Indicateurs, agrégations, palmarès |
| Restitution | `app/engines/reporting.py` | PDF, QR codes, exports CSV |
| Audit | `app/engines/audit.py` | Journal des opérations sensibles |
| Assistance | `app/engines/ai.py` | Traduction français → filtres structurés |

Le moteur de documents sert indifféremment les candidatures, les bourses, les
examens, les diplômes, les stages et les actes administratifs. Le moteur de
recherche sert le constructeur visuel, la recherche en langage naturel, les
requêtes enregistrées et la simulation des règles métier.

---

## Sécurité des requêtes

Le constructeur de requêtes n'interprète **jamais** d'expression fournie par
l'utilisateur. Chaque entité déclare explicitement ses champs interrogeables
(`DescripteurChamp`), et seuls ces champs peuvent être filtrés. Les opérateurs
sont issus d'une énumération fermée, et les valeurs passent par les paramètres
liés de SQLAlchemy.

Les champs *calculés* — moyenne dans une matière, moyenne générale, taux
d'absence — n'existent dans aucune table : ils sont reconstruits par des
sous-requêtes agrégées jointes à l'entité interrogée.

---

## Chaîne institutionnelle

```
SUPER_ADMIN
  └── MINISTRY_ADMIN        MEMP · MESFTP · MESRS
        └── DIRECTOR_ADMIN  DEC/MEMP · DEC/MESFTP · DOB
              └── DEPARTMENT_ADMIN   DDEPS × 12 départements
                    └── SCHOOL_ADMIN  établissements
                          └── CANDIDATE / STUDENT
```

Chaque rôle porte une **portée** (`NiveauScope`) et un ensemble de permissions
`ressource:action`. Une affectation lie un utilisateur, un rôle et une portée
concrète — une structure ou un établissement.

---

## Cycle de vie d'un dossier d'examen

```
BROUILLON ──soumettre──▶ SOUMIS ──instruire──▶ EN_ETUDE
                            ▲                     │
                            │                     ├─ declarer_incomplet ─▶ INCOMPLET ─┐
                            └─────── completer ◀──┴───────────────────────────────────┘
                                                  │
                                                  ├─ rejeter ─▶ REJETE
                                                  └─ valider ─▶ VALIDE
                                                                  │
                                                     convoquer ───▶ CONVOQUE
                                                                        │
                                                    marquer_compose ────▶ COMPOSE
                                                                        │
                                                    marquer_corrige ────▶ CORRIGE
                                                                        │
                                                        admettre ───────▶ ADMIS
                                                        ajourner ───────▶ NON_ADMIS
```

Toute transition est enregistrée dans `transitions_workflow` : qui, quand,
depuis quel statut, vers quel statut, avec quel commentaire.

---

## Délibération

1. Moyenne pondérée des notes ramenées sur 20 par les coefficients d'épreuve.
2. Application des notes éliminatoires déclarées sur chaque épreuve.
3. Repêchage du jury : jusqu'à un plafond configurable de points, uniquement
   pour les candidats sous le seuil d'admission et sans note éliminatoire.
4. Décision : `ADMIS`, `NON_ADMIS`, `ABSENT` ou `EXCLU` (fraude).
5. Mention selon le barème propre à l'examen.
6. Rangs national, départemental, par établissement et par centre.

---

## Accessibilité

L'accessibilité n'est pas une option d'affichage : elle traverse le modèle.

- `Apprenant.type_handicap`, `amenagements_examen`, `tiers_temps` ;
- `SalleComposition.salle_amenagee` — la répartition y place en priorité les
  candidats concernés ;
- `Salle.accessibilite`, `Etablissement.accessibilite` ;
- `Livre.braille_disponible`, `audio_disponible`, `format_accessible` ;
- `Cours.version_audio`, `transcription_disponible`, `sous_titres_disponibles` ;
- `Notification.message_simplifie` et `pictogramme` ;
- `Utilisateur.mode_simplifie`, `contraste_eleve`, `grande_police`,
  `lecture_vocale`.

Côté interface, ces préférences sont appliquées par des attributs sur `<html>`,
mémorisées localement et synchronisables avec le compte.
