#!/usr/bin/env bash
# ===========================================================================
# EduHub — vérification du serveur avant déploiement
#
# Ce script ne modifie RIEN. Il se contente de constater ce qui est en place
# et de signaler ce qui manque.
#
# C'est délibéré : le serveur héberge déjà une douzaine de conteneurs en
# service. Un script de « setup » qui active un pare-feu, réécrit
# /etc/docker/daemon.json et redémarre Docker couperait l'accès aux autres
# projets et les redémarrerait tous. Ce qu'il faut ajouter, vous le ferez
# vous-même, en connaissance de cause.
# ===========================================================================
set -euo pipefail

VERT='\033[0;32m'; ROUGE='\033[0;31m'; JAUNE='\033[1;33m'; BLEU='\033[0;34m'; NEUTRE='\033[0m'
ok()      { echo -e "${VERT}  ✓${NEUTRE} $1"; }
manque()  { echo -e "${ROUGE}  ✗${NEUTRE} $1"; }
attention() { echo -e "${JAUNE}  !${NEUTRE} $1"; }
titre()   { echo -e "\n${BLEU}$1${NEUTRE}"; }

PORT="${EDUHUB_PORT:-8100}"

echo "==========================================================="
echo "  EduHub — état du serveur $(hostname)"
echo "==========================================================="

titre "Docker"
if command -v docker >/dev/null 2>&1; then
    ok "docker $(docker --version | sed 's/Docker version //; s/,.*//')"
else
    manque "docker absent — installez-le avec : curl -fsSL https://get.docker.com | sh"
fi

if docker compose version >/dev/null 2>&1; then
    ok "docker compose $(docker compose version --short)"
else
    manque "le greffon docker compose est absent — apt-get install docker-compose-plugin"
fi

titre "Port destiné à EduHub (${PORT})"
if ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
    manque "le port ${PORT} est déjà occupé — choisissez-en un autre via EDUHUB_PORT"
    ss -ltnp 2>/dev/null | grep ":${PORT} " | sed 's/^/      /'
else
    ok "le port ${PORT} est libre"
fi

titre "Ports déjà pris sur cette machine"
ss -ltn 2>/dev/null \
    | awk 'NR>1 {print $4}' \
    | sed 's/.*://' \
    | sort -n -u \
    | tr '\n' ' ' \
    | sed 's/^/      /'
echo

titre "Conteneurs en service"
nombre=$(docker ps -q 2>/dev/null | wc -l)
ok "${nombre} conteneur(s) en cours d'exécution"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^eduhub-'; then
    attention "des conteneurs EduHub tournent déjà — le déploiement les remplacera"
    docker ps --filter 'name=eduhub-' --format '      {{.Names}}  {{.Status}}'
fi

titre "Ressources"
libre_mo=$(free -m | awk '/^Mem:/ {print $7}')
if [ "${libre_mo}" -lt 400 ]; then
    attention "${libre_mo} Mo de mémoire disponible — c'est juste pour une API et un PostgreSQL"
else
    ok "${libre_mo} Mo de mémoire disponible"
fi

libre_go=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
if [ "${libre_go}" -lt 5 ]; then
    attention "${libre_go} Go libres sur / — la construction de l'image en demande quelques-uns"
else
    ok "${libre_go} Go libres sur /"
fi

titre "Pare-feu"
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q '^Status: active'; then
    attention "ufw est actif — vérifiez que le port ${PORT} est autorisé :"
    echo "      ufw allow ${PORT}/tcp"
    ufw status numbered 2>/dev/null | sed 's/^/      /' | head -20
else
    ok "ufw inactif ou absent — aucune règle à ajouter"
fi

echo
echo "==========================================================="
echo "  Rien n'a été modifié."
echo "==========================================================="
