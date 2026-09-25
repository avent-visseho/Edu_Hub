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
# L'API ne publie ce port que sur 127.0.0.1 — c'est nginx qui l'expose en HTTPS —
# mais il doit tout de même être libre sur la boucle locale.
if ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
    manque "le port ${PORT} est déjà occupé — choisissez-en un autre via EDUHUB_PORT"
    ss -ltnp 2>/dev/null | grep ":${PORT} " | sed 's/^/      /'
else
    ok "le port ${PORT} est libre"
fi

titre "Ports 80 et 443, nécessaires à nginx et au certificat"
for p in 80 443; do
    if ss -ltn 2>/dev/null | grep -q ":${p} "; then
        # Sans les privilèges root, ss ne révèle pas le processus : l'occupant
        # reste inconnu, ce qui ne doit pas interrompre le diagnostic.
        occupant=$(ss -ltnp 2>/dev/null | grep ":${p} " | grep -oP 'users:\(\("\K[^"]+' | head -1 || true)
        if [ "${occupant}" = "nginx" ]; then
            ok "port ${p} : nginx — la configuration EduHub s'y ajoutera"
        else
            attention "port ${p} occupé par « ${occupant:-inconnu} » — à libérer, ou intégrez"
            attention "  EduHub à la configuration du serveur web déjà en place"
        fi
    else
        ok "le port ${p} est libre"
    fi
done

titre "Résolution DNS du sous-domaine"
DOMAINE="${EDUHUB_DOMAINE:-eduhub.ezafri.com}"
adresse=$(getent ahostsv4 "${DOMAINE}" 2>/dev/null | awk 'NR==1 {print $1}' || true)
publique=$(curl -fsS --max-time 10 https://api.ipify.org 2>/dev/null || true)
if [ -z "${adresse}" ]; then
    manque "${DOMAINE} ne résout vers aucune adresse — créez l'enregistrement A"
    [ -n "${publique}" ] && echo "      ${DOMAINE}  A  ${publique}"
elif [ -n "${publique}" ] && [ "${adresse}" != "${publique}" ]; then
    attention "${DOMAINE} → ${adresse}, mais ce serveur se voit en ${publique}"
else
    ok "${DOMAINE} → ${adresse}"
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
# Uniquement les deux conteneurs de la pile de production : sur un poste de
# développement, « eduhub- » attraperait aussi redis, minio et le postgres local.
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qE '^eduhub-(api|db)$'; then
    attention "la pile EduHub tourne déjà — le déploiement la remplacera"
    docker ps --format '{{.Names}}  {{.Status}}' 2>/dev/null \
        | grep -E '^eduhub-(api|db) ' | sed 's/^/      /'
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
    attention "ufw est actif — 80 et 443 doivent être autorisés (configurer-nginx.sh"
    attention "  s'en charge). Le port ${PORT} n'a pas à l'être : il n'écoute que sur"
    attention "  la boucle locale."
    ufw status numbered 2>/dev/null | sed 's/^/      /' | head -20
else
    ok "ufw inactif ou absent — aucune règle à ajouter"
fi

echo
echo "==========================================================="
echo "  Rien n'a été modifié."
echo "==========================================================="
