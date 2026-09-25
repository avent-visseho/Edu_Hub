# EduHub — image de l'API
#
# Le projet exige Python 3.12 (syntaxe générique PEP 695) et déclare ses
# dépendances dans pyproject.toml.
#
# Deux choix expliquent la forme de ce fichier :
#
# 1. Les versions sont figées par deploy_ment/contraintes.txt. pyproject.toml ne
#    donne que des minimums (« >= ») : une installation libre résout aujourd'hui
#    SQLAlchemy 2.1, alors que le code a été écrit et vérifié sur la 2.0. On
#    installe donc exactement l'arbre de dépendances du poste de développement.
#
# 2. Aucun compilateur n'est installé. Toutes les versions figées existent en
#    roue précompilée pour Linux/CPython 3.12, et `--only-binary` le garantit :
#    si une roue venait à manquer, la construction échouerait franchement au
#    lieu de compiler en silence. Cela épargne les 250 Mo de build-essential,
#    ce qui n'est pas rien sur un VPS qui héberge déjà une douzaine de
#    conteneurs.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# curl sert uniquement à la sonde de santé.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Couche de dépendances, isolée pour être réutilisée tant que pyproject.toml et
# les contraintes ne changent pas : sur un VPS modeste, c'est la différence
# entre un redéploiement de trente secondes et un de cinq minutes. Le paquet
# factice suffit à satisfaire hatchling, qui refuserait un projet sans sources.
COPY pyproject.toml ./
COPY deploy_ment/contraintes.txt ./deploy_ment/contraintes.txt
RUN mkdir -p app && touch app/__init__.py \
    && pip install --upgrade pip \
    && pip install --only-binary=:all: --no-binary=eduhub-api \
        -c deploy_ment/contraintes.txt -e .

# Code applicatif. Les tests et l'outillage de développement restent dehors.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# Le stockage local sert de repli quand aucun S3 n'est configuré ; il est monté
# sur un volume pour que les pièces déposées survivent aux redéploiements.
RUN mkdir -p /app/storage \
    && adduser --disabled-password --gecos '' eduhub \
    && chown -R eduhub:eduhub /app
USER eduhub

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Deux workers : l'API est asynchrone et le VPS héberge déjà une douzaine de
# conteneurs. Ajustez EDUHUB_WORKERS si la machine est plus confortable.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${EDUHUB_WORKERS:-2} --proxy-headers --forwarded-allow-ips='*'"]
