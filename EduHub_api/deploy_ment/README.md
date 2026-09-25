# Déploiement de l'API EduHub

Ce dossier contient tout ce qu'il faut pour faire tourner l'API sur un serveur :
une image Docker, une pile à deux services, un modèle de configuration et trois
scripts. Rien d'autre n'est requis — ni Redis, ni Celery, ni MinIO, ni PostGIS.
L'API est publiée en HTTPS sur **`api.ezafri.com`**, derrière nginx.

```
deploy_ment/
├── Dockerfile                    image de l'API (Python 3.12, sans compilateur)
├── docker-compose.prod.yml       pile : api + postgres 16
├── contraintes.txt               versions figées (généré)
├── figer-dependances.py          regénère contraintes.txt depuis le .venv
├── .env.production.example       modèle de configuration à recopier
├── README.md                     ce fichier
└── scripts/
    ├── verifier-serveur.sh       constate l'état du serveur, ne modifie rien
    ├── deployer.sh               envoie, construit, démarre, migre, peuple
    └── configurer-nginx.sh       publie l'API en HTTPS sur le sous-domaine
```

Un `.dockerignore` a par ailleurs été ajouté à la racine d'`EduHub_api/` : sans
lui, les 280 Mo du `.venv` et l'historique Git partiraient vers le démon Docker
à chaque construction.

Ne confondez pas les deux images : `EduHub_api/Dockerfile` est celle du
développement (outillage de test inclus, sources montées en volume), utilisée
par le `docker-compose.yml` à la racine du dépôt. `deploy_ment/Dockerfile` est
celle de la production. Elles coexistent volontairement.

---

## 1. Avant de commencer — trois points à connaître

### 1.1 Les fichiers d'origine venaient d'un autre projet

Les fichiers déposés dans ce dossier provenaient de LOKAHOME / fifaloge et ne
correspondaient pas à EduHub. Ils ont été remplacés parce qu'ils étaient
inopérants ou dangereux ici :

| Ce qu'ils faisaient | Pourquoi c'était inadapté |
| --- | --- |
| lançaient des workers **Celery** et un **Redis** | EduHub n'utilise ni l'un ni l'autre : Redis est déclaré dans la configuration mais n'est référencé nulle part dans `app/` |
| utilisaient **PostGIS** | les coordonnées géographiques d'EduHub sont de simples flottants |
| **Python 3.11** et un `requirements.txt` | EduHub exige 3.12 (syntaxe générique PEP 695) et déclare ses dépendances dans `pyproject.toml` |
| passaient `DATABASE_URL` | l'application lit `EDUHUB_DATABASE_URL` : **sans le préfixe, la variable est ignorée sans le moindre message** et l'API tenterait de joindre un `localhost` inexistant |
| publiaient sur les ports **8000** et **8080** | déjà pris sur votre serveur par swiftlink et lokahome |

Le `server-setup.sh` d'origine n'a **délibérément pas d'équivalent ici**, et
c'est important : il exécutait `ufw --force enable` en n'autorisant que les ports 22,
80 et 443. Sur votre machine, cela aurait coupé d'un coup les ports 3000, 3001,
4000, 5050, 5433, 8000, 8080 et 9000-9001 — soit swiftlink, noubidofi, lokahome
et nifurhotel. Il réécrivait aussi `/etc/docker/daemon.json` puis relançait
`systemctl restart docker`, ce qui aurait redémarré vos treize conteneurs.
**Ne le réexécutez pas depuis vos autres projets sur ce serveur.** Le serveur
étant déjà provisionné, il n'y avait rien à installer : `verifier-serveur.sh`
se contente donc de constater, et ce qu'il signale comme manquant, vous le
corrigez vous-même, en connaissance de cause.

### 1.2 Les versions sont figées, et ce n'est pas un détail

`pyproject.toml` ne déclare que des minimums (`>=`). C'est ce qu'il faut pour
développer, mais pour déployer c'est un piège : en vérifiant l'image, une
installation libre a résolu **SQLAlchemy 2.1**, alors que tout le code a été
écrit et éprouvé sur la **2.0.54** installée dans le `.venv`. Passer d'une
version mineure à l'autre de l'ORM sur une simple reconstruction d'image n'est
pas un risque à prendre.

`deploy_ment/contraintes.txt` fige donc les 52 paquets de l'arbre de
dépendances exact du poste de développement, et le `Dockerfile` installe sous
cette contrainte. Bénéfice secondaire : toutes ces versions existent en roue
précompilée, si bien que l'image n'embarque **aucun compilateur** — 250 Mo de
`build-essential` économisés, et plusieurs minutes de construction.

Après une mise à jour volontaire des dépendances dans le `.venv`, regénérez le
fichier puis redéployez :

```bash
.venv/bin/python deploy_ment/figer-dependances.py
```

Si une roue venait à manquer pour une version figée, la construction échouerait
franchement (`--only-binary`) au lieu de compiler en silence : c'est voulu.

### 1.3 Deux façons d'exposer l'API, et une seule est tenable

`EDUHUB_BIND`, dans `.env.production`, décide de qui peut joindre l'API :

| `EDUHUB_BIND` | L'API est joignable… | Pour quoi faire |
| --- | --- | --- |
| `0.0.0.0` | sur `http://185.194.217.12:8100`, **en clair** | essayer `/docs` tout de suite, sans DNS ni certificat |
| `127.0.0.1` | par nginx seulement, qui la publie en **HTTPS** | la configuration visée |

Le modèle livré est sur `0.0.0.0` pour que vous puissiez déployer et regarder
l'API vivre dès maintenant. C'est une étape, pas une destination :

- **en clair, les jetons d'authentification et les mots de passe circulent en
  clair.** Les données sont fictives, mais prenez-le comme un banc d'essai, pas
  comme une mise en service ;
- **un front sur Vercel ne pourra pas l'appeler.** Vercel sert en HTTPS, et le
  navigateur bloque toute requête HTTP émise depuis une page HTTPS — c'est le
  « contenu mixte », et il n'existe aucun contournement côté code. Le front se
  déploiera, s'affichera, et **toutes ses requêtes échoueront**.

Il faut donc, pour que le front fonctionne : un sous-domaine pour l'API, un
certificat (`deployer.sh https`), puis `EDUHUB_BIND=127.0.0.1` et un
redéploiement.

Le seul geste qu'aucun script ne peut faire à votre place, c'est
**l'enregistrement DNS**. Chez Hostinger, dans la zone d'`ezafri.com` :

```
api.ezafri.com   A   185.194.217.12
```

`api.ezafri.com` ne résout aujourd'hui vers rien : l'enregistrement est donc à
**créer**, et rien ne s'y oppose. Il n'existe pas d'enregistrement générique
`*.ezafri.com` — un sous-domaine tiré au hasard ne résout vers rien — si bien
que la création n'entre en conflit avec quoi que ce soit.

`eduhub.ezafri.com`, en revanche, **a déjà un enregistrement**, qui pointe vers
l'hébergement Hostinger (`77.37.53.105`, `91.108.98.97` au moment d'écrire).
C'est celui-là qu'il faudra remplacer par le `CNAME` de Vercel quand vous
brancherez le front. Les deux noms sont indépendants : un nom ne peut pas
pointer à la fois vers Vercel et vers ce serveur, d'où la séparation.

| Nom | Pointe vers | Enregistrement | État |
| --- | --- | --- | --- |
| `api.ezafri.com` | ce serveur (l'API) | `A` → `185.194.217.12` | à créer |
| `eduhub.ezafri.com` | Vercel (le front) | `CNAME` fourni par Vercel | à remplacer |

La zone d'`ezafri.com` est servie par les serveurs de noms d'Hostinger
(`ns1.dns-parking.com`, `ns2.dns-parking.com`) : c'est donc dans le panneau DNS
d'Hostinger que les deux enregistrements se règlent.

Let's Encrypt validant le domaine en appelant `http://api.ezafri.com/`, le
certificat serait délivré pour le serveur de parking — ou, plus probablement,
échouerait. Et chaque échec consomme un essai sur le quota.
`verifier-serveur.sh` compare la résolution à l'adresse réelle du serveur et
refuse d'aller plus loin si elles diffèrent.

---

## 2. Prérequis sur le serveur

Docker et le greffon `compose`. Votre serveur les a déjà, puisqu'il fait tourner
treize conteneurs. Pour le vérifier, ainsi que le port libre et les ressources
disponibles :

```bash
SERVEUR=root@185.194.217.12 ./deploy_ment/scripts/deployer.sh verifier
```

Ce script ne modifie rien. Il signale : la version de Docker, si le port 8100
est libre, qui occupe les ports 80 et 443 (ici nginx, ce qui est le cas
attendu), si `api.ezafri.com` résout bien vers ce serveur, la liste des
ports déjà pris, le nombre de conteneurs en service, la mémoire et le disque
disponibles, et l'état du pare-feu.

Rien à ouvrir manuellement dans le pare-feu : le port de l'API n'écoute que sur
la boucle locale, et `configurer-nginx.sh` autorise 80 et 443 lui-même si `ufw`
est actif.

---

## 3. Configuration

Depuis `EduHub_api/` :

```bash
cp deploy_ment/.env.production.example deploy_ment/.env.production
openssl rand -hex 32          # la valeur de EDUHUB_SECRET_KEY
```

Puis éditez `deploy_ment/.env.production` et remplacez **chaque** `CHANGEZ_MOI` :

| Variable | À renseigner |
| --- | --- |
| `EDUHUB_SECRET_KEY` | la sortie d'`openssl rand -hex 32` |
| `EDUHUB_DB_PASSWORD` | un mot de passe fort |
| `EDUHUB_DATABASE_URL` | le **même** mot de passe, dans l'URL |
| `EDUHUB_CORS_ORIGINS` | l'URL Vercel, dès qu'elle est connue |
| `EDUHUB_DOMAINE` | le nom réservé à l'API (voir section 1.3) |
| `EDUHUB_BIND` | `0.0.0.0` pour essayer tout de suite, `127.0.0.1` une fois nginx en place |
| `EDUHUB_PORT` | 8100, sauf si `verifier` le dit occupé |

Trois pièges qui ne produisent aucune erreur visible :

1. **Le préfixe `EDUHUB_`** est obligatoire sur toutes les variables. Sans lui,
   la valeur est ignorée silencieusement et la valeur par défaut s'applique.
2. **Le mot de passe apparaît deux fois** — dans `EDUHUB_DB_PASSWORD` (qui crée
   le compte PostgreSQL) et dans `EDUHUB_DATABASE_URL` (qui s'y connecte). S'ils
   diffèrent, l'API démarre et échoue à la première requête.
3. **`EDUHUB_CORS_ORIGINS` attend l'origine exacte**, schéma compris, sans barre
   oblique finale : `https://eduhub.vercel.app`, pas `eduhub.vercel.app` ni
   `https://eduhub.vercel.app/`.

`deploy_ment/.env.production` contient la clé de signature des jetons et le mot
de passe de la base. Il est exclu du dépôt par `.gitignore` — **ne le versionnez
jamais** — mais il est bien envoyé sur le serveur par le script : c'est là que
`docker compose` le lit, à la fois pour renseigner l'environnement de l'API et
pour créer le compte PostgreSQL.

---

## 4. Premier déploiement

```bash
cd EduHub_api
SERVEUR=root@185.194.217.12 ./deploy_ment/scripts/deployer.sh deployer
```

Le script, dans cet ordre : vérifie que la configuration est complète et que la
clé fait au moins 32 caractères, envoie les sources en `rsync` (sans `.git`,
sans `.venv` — 280 Mo —, sans les caches ni les tests), construit l'image,
démarre les deux conteneurs, attend que `/health` réponde et applique les
migrations Alembic. Comptez trois à cinq minutes la première fois, une trentaine de secondes ensuite : la couche des
dépendances est réutilisée tant que `pyproject.toml` ne change pas.

À l'issue, la base a son schéma mais **aucune donnée**. Pour générer le jeu de
démonstration complet :

```bash
SERVEUR=root@185.194.217.12 ./deploy_ment/scripts/deployer.sh peupler
```

Le volume dépend de `EDUHUB_SEED_SCALE` (`tiny`, `small`, `medium`, `large`).
En `medium`, comptez quelques minutes. Le seed suppose une base vide : relancé
sur une base déjà peuplée, il échoue sur les contraintes d'unicité — le script
demande confirmation avant de partir.

### Vérifier

Avec `EDUHUB_BIND=0.0.0.0`, tel que livré, depuis n'importe où :

```bash
curl http://185.194.217.12:8100/health
# {"status":"ok"}
```

Et dans un navigateur : **`http://185.194.217.12:8100/docs`** — la
documentation interactive, où toutes les routes sont essayables directement.

Avec `EDUHUB_BIND=127.0.0.1`, la même vérification passe par le serveur :

```bash
ssh root@185.194.217.12 'curl -s http://127.0.0.1:8100/health'
```

Le passage en HTTPS fait l'objet de la section 6.

Comptes de démonstration, mot de passe `EduHub2026!` :

| Identifiant | Portée |
| --- | --- |
| `super.admin@eduhub.bj` | accès complet |
| `admin.memp@eduhub.bj` | ministère |
| `admin.dec.memp@eduhub.bj` | direction des examens et concours |
| `admin.ddeps.atlantique@eduhub.bj` | direction départementale |

---

## 5. Exploitation courante

Toutes les commandes prennent `SERVEUR=root@185.194.217.12` en préfixe.

| Commande | Effet |
| --- | --- |
| `deployer.sh deployer` | redéploie (envoi, construction, démarrage, migrations) |
| `deployer.sh etat` | statut des conteneurs, CPU et mémoire consommés |
| `deployer.sh journaux` | journaux en continu (`journaux api` pour un seul service) |
| `deployer.sh https` | installe nginx et le certificat (une seule fois) |
| `deployer.sh migrer` | applique les migrations sans redéployer |
| `deployer.sh redemarrer` | redémarre l'API seule |
| `deployer.sh arreter` | arrête la pile ; **les volumes sont conservés** |
| `deployer.sh console` | ouvre un shell dans le dossier distant |

Le dossier distant est `/opt/eduhub` (`DOSSIER_DISTANT` pour en changer). Les
données vivent dans deux volumes Docker, `eduhub_postgres` et `eduhub_storage`,
qui survivent aux redéploiements, aux reconstructions d'image et à `arreter`.

### Libérer la place prise par les anciennes images

Chaque redéploiement laisse l'image précédente sans étiquette. Le script ne les
supprime pas de lui-même : un `docker image prune` global s'appliquerait à tout
le serveur, y compris aux autres projets. Ciblez EduHub :

```bash
ssh root@185.194.217.12 \
  "docker image ls --filter 'reference=eduhub-api' --filter 'dangling=true' -q \
   | xargs -r docker rmi"
```

### Sauvegarder la base

```bash
ssh root@185.194.217.12 \
  "docker exec eduhub-db pg_dump -U eduhub eduhub | gzip" \
  > eduhub-$(date +%F).sql.gz
```

### Restaurer

```bash
gunzip -c eduhub-2026-09-25.sql.gz \
  | ssh root@185.194.217.12 "docker exec -i eduhub-db psql -U eduhub -d eduhub"
```

### Repartir d'une base vierge

Destructif : supprime le volume, donc toutes les données.

```bash
ssh root@185.194.217.12 'cd /opt/eduhub \
  && docker compose --env-file deploy_ment/.env.production \
       -f deploy_ment/docker-compose.prod.yml down \
  && docker volume rm eduhub_postgres'
SERVEUR=root@185.194.217.12 ./deploy_ment/scripts/deployer.sh deployer
SERVEUR=root@185.194.217.12 ./deploy_ment/scripts/deployer.sh peupler
```

Le `--env-file` n'est pas décoratif : le fichier de composition exige
`EDUHUB_DB_PASSWORD` et refuse de s'exécuter sans lui. C'est pour cette raison
que `deployer.sh` le passe systématiquement.

---

## 6. Publier l'API en HTTPS sur api.ezafri.com

Une seule commande, à lancer une seule fois :

```bash
SERVEUR=root@185.194.217.12 ./deploy_ment/scripts/deployer.sh https
```

Elle exécute `configurer-nginx.sh` sur le serveur, qui :

1. **vérifie le DNS** — `api.ezafri.com` doit résoudre vers ce serveur. Sinon
   il s'arrête en donnant l'enregistrement à créer, plutôt que de laisser
   certbot échouer et consommer un essai sur son quota ;
2. **vérifie que l'API répond** sur `127.0.0.1:8100` ;
3. installe **nginx** et **certbot** s'ils manquent ;
4. **refuse d'agir si le port 80 est pris** par autre chose que nginx, en
   nommant le service concerné — vos autres projets ne doivent pas être
   interrompus par surprise ;
5. écrit `/etc/nginx/sites-available/eduhub` et l'active ;
6. demande le **certificat Let's Encrypt** et installe la redirection
   HTTP → HTTPS. Certbot pose deux questions (adresse de courriel, conditions
   d'utilisation) ; pour un passage non interactif, fournissez
   `EDUHUB_COURRIEL` ;
7. si `ufw` est actif, ouvre **80** et **443** et referme le port de l'API,
   devenu inutile.

Le script est relançable sans dommage : il réécrit le même fichier de site et
certbot ne redemande pas un certificat encore valide. Le renouvellement est
ensuite automatique, assuré par le minuteur installé avec certbot.

### Le prérequis à faire soi-même : l'enregistrement DNS

Chez le registrar d'`ezafri.com`, remplacez la résolution générique par un
enregistrement explicite :

```
api.ezafri.com   A   185.194.217.12
```

Puis, en attendant la propagation :

```bash
dig +short api.ezafri.com
# doit renvoyer 185.194.217.12, et rien d'autre
```

Tant que cette commande renvoie autre chose, `https` s'arrêtera avant de
demander le certificat.

### nginx est déjà en place sur ce serveur

La machine fait déjà tourner **nginx 1.24.0 (Ubuntu)**, qui sert d'autres sites
en HTTP et en HTTPS. Le script s'y insère plutôt que de s'y substituer :

- il n'installe rien si nginx est présent ;
- le fichier d'EduHub est **un site de plus**, déclaré sans `default_server` :
  il ne répond que pour `api.ezafri.com` et laisse les autres sites répondre
  pour les leurs ;
- aucun fichier existant n'est modifié, et le script annonce combien de sites
  sont déjà configurés avant d'agir ;
- nginx est **rechargé**, pas redémarré : les autres sites ne sont pas
  interrompus ;
- si la configuration produite était invalide, `nginx -t` l'arrête avant le
  rechargement.

Il vérifie aussi que `nginx.conf` inclut bien `sites-enabled/*` ; sinon il place
le site dans `conf.d/`, sans quoi le fichier serait ignoré en silence.

### Ce que nginx fait de particulier

Deux réglages sortent des valeurs par défaut, et les deux ont une raison :

- `client_max_body_size 25M` — la limite par défaut de nginx est de 1 Mo, ce
  qui refuserait un scan de diplôme avec un `413` que le front ne sait pas
  expliquer ;
- `proxy_read_timeout 120s` — la génération des relevés, convocations et
  bulletins, et les exports CSV, prennent quelques dizaines de secondes sur les
  gros lots.

Les en-têtes `X-Forwarded-*` sont transmis et l'image lance déjà uvicorn avec
`--proxy-headers` : les URL que l'API génère porteront donc bien le `https://`
vu par le navigateur, sans rien à changer dans le code.

### Vérifier

```bash
curl https://api.ezafri.com/health
# {"status":"ok"}
```

Et dans un navigateur : `https://api.ezafri.com/docs`

---

## 7. Brancher le front sur Vercel

### Les variables que Vercel vous propose sont les mauvaises

Vercel scrute le dépôt et, y trouvant le `docker-compose.yml` de la racine, il
propose `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`,
`REDIS_PORT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_PORT` et
`MINIO_CONSOLE_PORT`.

**Laissez-les toutes vides et n'en créez aucune.** Ce sont les variables de la
pile de développement locale — PostgreSQL, Redis, MinIO — c'est-à-dire des
services qui tournent sur *votre* machine et sur *le serveur*, jamais sur
Vercel. Vercel n'héberge que le front Next.js : il ne parle pas à la base, il
parle à l'API par HTTP. Y déposer le mot de passe de PostgreSQL ne servirait à
rien et l'exposerait pour rien.

### Les variables qui comptent

Le front n'en lit qu'une, dans `src/lib/api.ts` :

```
NEXT_PUBLIC_API_URL = https://api.ezafri.com/api/v1
```

C'est tout. (`NEXT_PUBLIC_NOM_PLATEFORME` figure dans `.env.example` mais n'est
lue nulle part dans le code : inutile de la renseigner.)

Le suffixe `/api/v1` fait partie de l'URL — c'est le préfixe sous lequel toutes
les routes sont montées. Seule `/health` vit à la racine.

Cette variable est lue **à la construction** : après l'avoir modifiée, il faut
relancer un déploiement pour qu'elle prenne effet.

### Les réglages du projet Vercel

| Réglage | Valeur |
| --- | --- |
| Framework Preset | Next.js |
| **Root Directory** | **`EduHub_front`** |
| Build Command | (par défaut) |
| Install Command | (par défaut) |

Le **Root Directory** est le point à ne pas manquer : le dépôt contient l'API et
le front côte à côte, et sans lui Vercel construirait la racine et ne trouverait
aucune application Next.js.

### Côté API : autoriser l'origine

Ajoutez les origines du front à `EDUHUB_CORS_ORIGINS` dans
`deploy_ment/.env.production`, puis redéployez :

```
EDUHUB_CORS_ORIGINS=http://localhost:3000,https://eduhub.ezafri.com,https://eduhub.vercel.app
```

Les deux origines du front sont utiles : `eduhub.ezafri.com` une fois le
sous-domaine branché, et l'URL `.vercel.app` que Vercel attribue de toute façon
et par laquelle vous accéderez au site avant cela.

```bash
SERVEUR=root@185.194.217.12 ./deploy_ment/scripts/deployer.sh deployer
```

L'origine doit être exacte : schéma compris, sans barre oblique finale.
`https://eduhub.vercel.app`, et non `eduhub.vercel.app` ni
`https://eduhub.vercel.app/`.

Vercel attribue par ailleurs une URL distincte à chaque déploiement de
prévisualisation (`https://eduhub-xxxx-votrecompte.vercel.app`). Elles ne sont
pas couvertes par l'origine de production : ajoutez-les au fur et à mesure si
vous voulez les faire fonctionner, ou fixez un domaine de prévisualisation
stable dans Vercel.

### L'ordre des opérations

Le front ne peut pas fonctionner avant que l'API soit en HTTPS. L'enchaînement
qui évite les allers-retours :

1. **Déployer l'API sur son port** (`EDUHUB_BIND=0.0.0.0`) et vérifier
   `http://185.194.217.12:8100/docs`. Rien d'autre n'est nécessaire à ce stade :
   ni DNS, ni certificat, ni Vercel.
2. **Créer les enregistrements DNS** chez Hostinger : un nom pour l'API vers
   `185.194.217.12`, et le nom du front vers Vercel.
3. **`deployer.sh https`**, puis `EDUHUB_BIND=127.0.0.1` et un redéploiement.
4. **Déployer le front sur Vercel** avec `NEXT_PUBLIC_API_URL` pointant vers
   l'API en HTTPS, et l'origine Vercel ajoutée à `EDUHUB_CORS_ORIGINS`.

Rien n'empêche de déployer le front dès l'étape 1 pour voir l'interface
s'afficher — sachez seulement que toutes ses requêtes échoueront jusqu'à
l'étape 4, et que ce n'est pas un bogue.

---

## 8. Quand quelque chose ne va pas

| Symptôme | Cause la plus fréquente |
| --- | --- |
| `curl /health` ne répond pas | conteneur non démarré : `deployer.sh etat`, puis `deployer.sh journaux api` |
| `password authentication failed for user "eduhub"` | `EDUHUB_DB_PASSWORD` et le mot de passe dans `EDUHUB_DATABASE_URL` diffèrent. Attention : changer `EDUHUB_DB_PASSWORD` après la création du volume ne change pas le mot de passe en base — PostgreSQL ne lit `POSTGRES_PASSWORD` qu'à l'initialisation |
| l'API essaie de joindre `localhost:5432` | une variable a été écrite sans le préfixe `EDUHUB_` |
| `bind: address already in use` | le port est pris : `deployer.sh verifier`, puis changez `EDUHUB_PORT` |
| erreur CORS dans la console du navigateur | l'origine du front n'est pas dans `EDUHUB_CORS_ORIGINS`, ou elle y figure avec une barre oblique finale |
| `Mixed Content ... has been blocked` | le front appelle l'API en `http://` : `NEXT_PUBLIC_API_URL` doit commencer par `https://`, ce qui suppose l'étape 3 de la section 7 |
| Vercel : `No Next.js version detected` | le **Root Directory** du projet n'est pas `EduHub_front` |
| `curl https://api.ezafri.com` : connexion refusée | nginx n'est pas configuré : `deployer.sh https` |
| certbot : `Timeout during connect` | le DNS ne pointe pas encore vers le serveur, ou le port 80 est fermé |
| `https` s'arrête sur un écart d'adresse | `api.ezafri.com` ne résout pas encore vers `185.194.217.12` : l'enregistrement `A` n'est pas créé ou pas propagé (section 6) |
| la construction échoue sur `No matching distribution ... --only-binary` | une version figée n'a pas de roue pour Linux/CPython 3.12. Ajustez la version dans le `.venv`, puis regénérez `contraintes.txt` (section 1.2) |
| `Target database is not up to date` | migrations non appliquées : `deployer.sh migrer` |
| le seed échoue sur une contrainte d'unicité | la base est déjà peuplée : videz-la d'abord (section 5) |
| la construction manque de disque | supprimez les anciennes images EduHub (section 5). N'utilisez pas `docker image prune -a` : il emporterait les images des autres projets du serveur |
