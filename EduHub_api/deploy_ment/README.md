# Déploiement de l'API EduHub

Ce dossier contient tout ce qu'il faut pour faire tourner l'API sur un serveur :
une image Docker, une pile à deux services, un modèle de configuration et trois
scripts. Rien d'autre n'est requis — ni Redis, ni Celery, ni MinIO, ni PostGIS.
L'API est publiée en HTTPS sur **`eduhub.ezafri.com`**, derrière nginx.

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

### 1.3 L'API n'est jamais exposée en clair

L'API publie son port **sur `127.0.0.1` uniquement**. Elle n'est donc pas
joignable depuis Internet tant que nginx n'est pas configuré, et ce n'est pas
une limitation mais le montage visé : c'est nginx qui l'expose, en HTTPS, sur
**`eduhub.ezafri.com`**.

Deux conséquences pratiques :

- **le déploiement seul ne suffit pas.** Après `deployer`, lancez `https`
  (section 6). D'ici là, l'API ne répond qu'en `ssh` sur le serveur.
- **c'est ce qui rend Vercel possible.** Un front servi en HTTPS ne peut pas
  appeler une API en HTTP : le navigateur bloque la requête pour contenu mixte,
  sans contournement possible côté code. Avec le certificat en place, le
  problème ne se pose pas.

Une seule chose est à faire de votre côté et ne peut pas l'être par un script :
**créer l'enregistrement DNS**. Chez le registrar d'`ezafri.com` :

```
eduhub.ezafri.com   A   <adresse IP du serveur>
```

Au moment d'écrire ces lignes, `eduhub.ezafri.com` ne résout vers aucune
adresse. Let's Encrypt validant le domaine en appelant `http://eduhub.ezafri.com/`,
le certificat échouera tant que l'enregistrement n'est pas propagé — et chaque
échec consomme un essai sur le quota. `verifier-serveur.sh` le contrôle et
vous donne la ligne exacte à créer, avec l'IP du serveur.

---

## 2. Prérequis sur le serveur

Docker et le greffon `compose`. Votre serveur les a déjà, puisqu'il fait tourner
treize conteneurs. Pour le vérifier, ainsi que le port libre et les ressources
disponibles :

```bash
SERVEUR=root@<ip-du-serveur> ./deploy_ment/scripts/deployer.sh verifier
```

Ce script ne modifie rien. Il signale : la version de Docker, si le port 8100
est libre, si les ports 80 et 443 le sont (nginx et le certificat en ont
besoin), si `eduhub.ezafri.com` résout bien vers ce serveur, la liste des ports
déjà pris, le nombre de conteneurs en service, la mémoire et le disque
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
| `EDUHUB_DOMAINE` | déjà renseigné : `eduhub.ezafri.com` |
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
SERVEUR=root@<ip-du-serveur> ./deploy_ment/scripts/deployer.sh deployer
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
SERVEUR=root@<ip-du-serveur> ./deploy_ment/scripts/deployer.sh peupler
```

Le volume dépend de `EDUHUB_SEED_SCALE` (`tiny`, `small`, `medium`, `large`).
En `medium`, comptez quelques minutes. Le seed suppose une base vide : relancé
sur une base déjà peuplée, il échoue sur les contraintes d'unicité — le script
demande confirmation avant de partir.

### Vérifier

L'API n'écoutant que sur la boucle locale, la vérification se fait depuis le
serveur :

```bash
ssh root@<ip-du-serveur> 'curl -s http://127.0.0.1:8100/health'
# {"status":"ok"}
```

Puis publiez-la en HTTPS (section 6) :

```bash
SERVEUR=root@<ip-du-serveur> ./deploy_ment/scripts/deployer.sh https
```

La documentation interactive sera alors sur `https://eduhub.ezafri.com/docs`.

Comptes de démonstration, mot de passe `EduHub2026!` :

| Identifiant | Portée |
| --- | --- |
| `super.admin@eduhub.bj` | accès complet |
| `admin.memp@eduhub.bj` | ministère |
| `admin.dec.memp@eduhub.bj` | direction des examens et concours |
| `admin.ddeps.atlantique@eduhub.bj` | direction départementale |

---

## 5. Exploitation courante

Toutes les commandes prennent `SERVEUR=root@<ip-du-serveur>` en préfixe.

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
ssh root@<ip-du-serveur> \
  "docker image ls --filter 'reference=eduhub-api' --filter 'dangling=true' -q \
   | xargs -r docker rmi"
```

### Sauvegarder la base

```bash
ssh root@<ip-du-serveur> \
  "docker exec eduhub-db pg_dump -U eduhub eduhub | gzip" \
  > eduhub-$(date +%F).sql.gz
```

### Restaurer

```bash
gunzip -c eduhub-2026-09-25.sql.gz \
  | ssh root@<ip-du-serveur> "docker exec -i eduhub-db psql -U eduhub -d eduhub"
```

### Repartir d'une base vierge

Destructif : supprime le volume, donc toutes les données.

```bash
ssh root@<ip-du-serveur> 'cd /opt/eduhub \
  && docker compose --env-file deploy_ment/.env.production \
       -f deploy_ment/docker-compose.prod.yml down \
  && docker volume rm eduhub_postgres'
SERVEUR=root@<ip-du-serveur> ./deploy_ment/scripts/deployer.sh deployer
SERVEUR=root@<ip-du-serveur> ./deploy_ment/scripts/deployer.sh peupler
```

Le `--env-file` n'est pas décoratif : le fichier de composition exige
`EDUHUB_DB_PASSWORD` et refuse de s'exécuter sans lui. C'est pour cette raison
que `deployer.sh` le passe systématiquement.

---

## 6. Publier en HTTPS sur eduhub.ezafri.com

Une seule commande, à lancer une seule fois :

```bash
SERVEUR=root@<ip-du-serveur> ./deploy_ment/scripts/deployer.sh https
```

Elle exécute `configurer-nginx.sh` sur le serveur, qui :

1. **vérifie le DNS** — `eduhub.ezafri.com` doit résoudre vers ce serveur. Sinon
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

Chez le registrar d'`ezafri.com` :

```
eduhub.ezafri.com   A   <adresse IP du serveur>
```

Puis, en attendant la propagation :

```bash
dig +short eduhub.ezafri.com
```

Tant que cette commande ne renvoie pas l'IP du serveur, `https` s'arrêtera
avant de demander le certificat.

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
curl https://eduhub.ezafri.com/health
# {"status":"ok"}
```

Et dans un navigateur : `https://eduhub.ezafri.com/docs`

---

## 7. Brancher le front sur Vercel

**a. Côté Vercel**, dans *Settings → Environment Variables* du projet :

```
NEXT_PUBLIC_API_URL        = https://eduhub.ezafri.com/api/v1
NEXT_PUBLIC_NOM_PLATEFORME = EduHub
```

Le suffixe `/api/v1` fait partie de l'URL : c'est le préfixe sous lequel toutes
les routes sont montées. Seule `/health` vit à la racine.

Ces variables sont lues **à la construction** : après les avoir modifiées, il
faut relancer un déploiement pour qu'elles prennent effet.

**b. Côté API**, ajoutez l'origine Vercel à `EDUHUB_CORS_ORIGINS` dans
`deploy_ment/.env.production`, puis redéployez :

```
EDUHUB_CORS_ORIGINS=http://localhost:3000,https://eduhub.vercel.app
```

```bash
SERVEUR=root@<ip-du-serveur> ./deploy_ment/scripts/deployer.sh deployer
```

L'origine doit être exacte : schéma compris, sans barre oblique finale.
`https://eduhub.vercel.app`, et non `eduhub.vercel.app` ni
`https://eduhub.vercel.app/`.

Vercel attribue par ailleurs une URL distincte à chaque déploiement de
prévisualisation (`https://eduhub-xxxx-votrecompte.vercel.app`). Elles ne sont
pas couvertes par l'origine de production : ajoutez-les au fur et à mesure si
vous voulez les faire fonctionner, ou fixez un domaine de prévisualisation
stable dans Vercel.

**c. Si vous préférez servir le front sur le même domaine**, par exemple
`eduhub.ezafri.com` pour le front et `eduhub.ezafri.com/api` pour l'API, il n'y
a plus de CORS du tout — mais cela suppose de faire passer le front par nginx
plutôt que par Vercel. Le montage décrit ici est le plus simple des deux.

---

## 8. Quand quelque chose ne va pas

| Symptôme | Cause la plus fréquente |
| --- | --- |
| `curl /health` ne répond pas | conteneur non démarré : `deployer.sh etat`, puis `deployer.sh journaux api` |
| `password authentication failed for user "eduhub"` | `EDUHUB_DB_PASSWORD` et le mot de passe dans `EDUHUB_DATABASE_URL` diffèrent. Attention : changer `EDUHUB_DB_PASSWORD` après la création du volume ne change pas le mot de passe en base — PostgreSQL ne lit `POSTGRES_PASSWORD` qu'à l'initialisation |
| l'API essaie de joindre `localhost:5432` | une variable a été écrite sans le préfixe `EDUHUB_` |
| `bind: address already in use` | le port est pris : `deployer.sh verifier`, puis changez `EDUHUB_PORT` |
| erreur CORS dans la console du navigateur | l'origine du front n'est pas dans `EDUHUB_CORS_ORIGINS`, ou elle y figure avec une barre oblique finale |
| `Mixed Content ... has been blocked` | le front appelle l'API en `http://` : `NEXT_PUBLIC_API_URL` doit commencer par `https://` |
| `curl https://eduhub.ezafri.com` : connexion refusée | nginx n'est pas configuré : `deployer.sh https` |
| certbot : `Timeout during connect` | le DNS ne pointe pas encore vers le serveur, ou le port 80 est fermé |
| la construction échoue sur `No matching distribution ... --only-binary` | une version figée n'a pas de roue pour Linux/CPython 3.12. Ajustez la version dans le `.venv`, puis regénérez `contraintes.txt` (section 1.2) |
| `Target database is not up to date` | migrations non appliquées : `deployer.sh migrer` |
| le seed échoue sur une contrainte d'unicité | la base est déjà peuplée : videz-la d'abord (section 5) |
| la construction manque de disque | supprimez les anciennes images EduHub (section 5). N'utilisez pas `docker image prune -a` : il emporterait les images des autres projets du serveur |
