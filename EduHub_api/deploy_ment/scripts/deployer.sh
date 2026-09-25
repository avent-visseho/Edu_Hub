#!/usr/bin/env bash
# ===========================================================================
# EduHub — déploiement de l'API sur le serveur
#
#   ./deploy_ment/scripts/deployer.sh verifier      état du serveur, sans rien modifier
#   ./deploy_ment/scripts/deployer.sh deployer      envoi, construction, démarrage, migrations
#   ./deploy_ment/scripts/deployer.sh migrer        applique les migrations Alembic
#   ./deploy_ment/scripts/deployer.sh peupler       génère le jeu de démonstration
#   ./deploy_ment/scripts/deployer.sh https         publie en HTTPS derrière nginx
#   ./deploy_ment/scripts/deployer.sh etat          statut des conteneurs et ressources
#   ./deploy_ment/scripts/deployer.sh journaux      journaux en continu
#   ./deploy_ment/scripts/deployer.sh redemarrer    redémarre l'API
#   ./deploy_ment/scripts/deployer.sh arreter       arrête la pile EduHub
#   ./deploy_ment/scripts/deployer.sh console       ouvre un shell sur le serveur
#
# À lancer depuis EduHub_api/. L'adresse du serveur se donne par variable :
#   SERVEUR=root@185.194.217.12 ./deploy_ment/scripts/deployer.sh deployer
# ===========================================================================
set -euo pipefail

# ---- Réglages ---------------------------------------------------------------

# Renseignez SERVEUR une fois pour toutes, ou passez-le à chaque appel.
SERVEUR="${SERVEUR:-}"
DOSSIER_DISTANT="${DOSSIER_DISTANT:-/opt/eduhub}"
COMPOSE="docker compose --env-file deploy_ment/.env.production -f deploy_ment/docker-compose.prod.yml"

VERT='\033[0;32m'; ROUGE='\033[0;31m'; JAUNE='\033[1;33m'; BLEU='\033[0;34m'; NEUTRE='\033[0m'
info()      { echo -e "${BLEU}[·]${NEUTRE} $1"; }
ok()        { echo -e "${VERT}[✓]${NEUTRE} $1"; }
attention() { echo -e "${JAUNE}[!]${NEUTRE} $1"; }
erreur()    { echo -e "${ROUGE}[✗]${NEUTRE} $1" >&2; exit 1; }
titre()     { echo -e "\n${BLEU}=== $1 ===${NEUTRE}\n"; }

# Racine du projet API, quel que soit le répertoire d'appel.
RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${RACINE}"

verifier_serveur_defini() {
    [ -n "${SERVEUR}" ] || erreur "SERVEUR non défini. Exemple : SERVEUR=root@185.194.217.12 $0 $1"
}

# Le seed et la construction de l'image durent plusieurs minutes sans rien
# écrire : sans ces relances, la connexion finit par être coupée en silence.
OPTIONS_SSH=(-o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -o ServerAliveCountMax=20)

distant() { ssh "${OPTIONS_SSH[@]}" "${SERVEUR}" "$@"; }

# ---- Commandes --------------------------------------------------------------

aide() {
    sed -n '3,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

verifier() {
    verifier_serveur_defini verifier
    titre "État du serveur"
    # Le port à tester vient de la configuration locale quand elle existe, pour
    # que la vérification porte bien sur celui qui sera publié.
    local port=8100
    if [ -f deploy_ment/.env.production ]; then
        port=$(grep -E '^EDUHUB_PORT=' deploy_ment/.env.production | cut -d= -f2-)
        port="${port:-8100}"
    fi
    ssh "${OPTIONS_SSH[@]}" "${SERVEUR}" "EDUHUB_PORT=${port} bash -s" \
        < deploy_ment/scripts/verifier-serveur.sh
}

deployer() {
    verifier_serveur_defini deployer

    [ -f deploy_ment/.env.production ] \
        || erreur "deploy_ment/.env.production manquant. Copiez .env.production.example et renseignez-le."

    if grep -q 'CHANGEZ_MOI' deploy_ment/.env.production; then
        erreur "des valeurs CHANGEZ_MOI subsistent dans deploy_ment/.env.production."
    fi

    # La clé de signature protège tous les jetons : une clé trop courte ruine
    # l'authentification sans qu'aucune erreur ne le signale.
    cle=$(grep -E '^EDUHUB_SECRET_KEY=' deploy_ment/.env.production | cut -d= -f2-)
    [ "${#cle}" -ge 32 ] \
        || erreur "EDUHUB_SECRET_KEY fait ${#cle} caractères ; il en faut au moins 32 (openssl rand -hex 32)."

    titre "Déploiement vers ${SERVEUR}"

    info "Préparation du dossier distant…"
    distant "mkdir -p '${DOSSIER_DISTANT}'"

    info "Envoi des sources…"
    rsync -az --delete --info=stats1 \
        --exclude '.git' \
        --exclude '.venv' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.pytest_cache' \
        --exclude '.ruff_cache' \
        --exclude '.mypy_cache' \
        --exclude '.env' \
        --exclude '.env.example' \
        --exclude 'tests' \
        --exclude 'storage' \
        -e "ssh ${OPTIONS_SSH[*]}" \
        ./ "${SERVEUR}:${DOSSIER_DISTANT}/"
    ok "Sources synchronisées"

    info "Construction de l'image et démarrage…"
    distant "cd '${DOSSIER_DISTANT}' && ${COMPOSE} up -d --build"
    ok "Conteneurs démarrés"

    info "Attente de la sonde de santé…"
    port=$(grep -E '^EDUHUB_PORT=' deploy_ment/.env.production | cut -d= -f2- || echo 8100)
    port="${port:-8100}"
    for tentative in $(seq 1 45); do
        if distant "curl -fsS http://localhost:${port}/health >/dev/null 2>&1"; then
            ok "API opérationnelle"
            break
        fi
        if [ "${tentative}" -eq 45 ]; then
            attention "L'API n'a pas répondu en 90 secondes. Derniers journaux :"
            distant "cd '${DOSSIER_DISTANT}' && ${COMPOSE} logs --tail=40 api"
            erreur "Déploiement interrompu."
        fi
        sleep 2
    done

    info "Application des migrations…"
    distant "cd '${DOSSIER_DISTANT}' && ${COMPOSE} exec -T api alembic upgrade head"
    ok "Schéma à jour"

    echo
    ok "Déploiement terminé."
    echo
    domaine=$(grep -E '^EDUHUB_DOMAINE=' deploy_ment/.env.production | cut -d= -f2- || true)
    if [ -n "${domaine}" ] && distant "test -d /etc/letsencrypt/live/${domaine}"; then
        echo "  Santé        : https://${domaine}/health"
        echo "  Documentation: https://${domaine}/docs"
    else
        echo "  L'API n'écoute que sur 127.0.0.1:${port} du serveur : elle n'est pas"
        echo "  encore joignable depuis Internet. Pour la publier en HTTPS sur"
        echo "  ${domaine:-votre sous-domaine} :"
        echo "      $0 https"
    fi
    echo
    echo "  Si la base est vide, générez le jeu de démonstration :"
    echo "      $0 peupler"
    echo
    echo "  Les images remplacées ne sont pas supprimées automatiquement : le"
    echo "  serveur héberge d'autres projets et un élagage global pourrait leur"
    echo "  retirer une image. Pour libérer la place, ciblez EduHub :"
    echo "      docker image ls --filter 'reference=eduhub-api' --filter 'dangling=true' -q | xargs -r docker rmi"
    echo
}

migrer() {
    verifier_serveur_defini migrer
    titre "Migrations"
    distant "cd '${DOSSIER_DISTANT}' && ${COMPOSE} exec -T api alembic upgrade head"
    ok "Schéma à jour"
}

peupler() {
    verifier_serveur_defini peupler
    titre "Jeu de démonstration"
    attention "Le seed remplit une base vide ; relancé sur une base déjà peuplée, il échouera"
    attention "sur les contraintes d'unicité. Pour repartir de zéro, videz d'abord le schéma."
    echo
    read -r -p "Continuer ? (o/N) " reponse
    [[ "${reponse}" =~ ^[oO]$ ]] || { info "Abandon."; return; }

    distant "cd '${DOSSIER_DISTANT}' && ${COMPOSE} exec -T api python -m app.seed"
    ok "Données générées"
    echo
    echo "  Comptes de démonstration — mot de passe EduHub2026!"
    echo "      super.admin@eduhub.bj            (accès complet)"
    echo "      admin.memp@eduhub.bj             (ministère)"
    echo "      admin.dec.memp@eduhub.bj         (direction des examens)"
    echo "      admin.ddeps.atlantique@eduhub.bj (direction départementale)"
    echo
}

https() {
    verifier_serveur_defini https
    [ -f deploy_ment/.env.production ] \
        || erreur "deploy_ment/.env.production manquant : le domaine et le port en viennent."

    local domaine port
    domaine=$(grep -E '^EDUHUB_DOMAINE=' deploy_ment/.env.production | cut -d= -f2- || true)
    port=$(grep -E '^EDUHUB_PORT=' deploy_ment/.env.production | cut -d= -f2- || true)
    [ -n "${domaine}" ] \
        || erreur "EDUHUB_DOMAINE absent de deploy_ment/.env.production."

    titre "Publication de ${domaine} en HTTPS"
    attention "Cette étape installe nginx et certbot sur le serveur et demande un"
    attention "certificat à Let's Encrypt. Les autres projets hébergés ne sont pas"
    attention "touchés, mais le port 80 doit être libre."
    echo
    read -r -p "Continuer ? (o/N) " reponse
    [[ "${reponse}" =~ ^[oO]$ ]] || { info "Abandon."; return; }

    # Le script part en flux sur l'entrée standard : rien à déposer sur le
    # serveur, et -t pour que certbot puisse poser ses questions.
    ssh "${OPTIONS_SSH[@]}" "${SERVEUR}" \
        "EDUHUB_DOMAINE='${domaine}' EDUHUB_PORT='${port:-8100}' bash -s" \
        < deploy_ment/scripts/configurer-nginx.sh
}

etat() {
    verifier_serveur_defini etat
    titre "Conteneurs EduHub"
    distant "cd '${DOSSIER_DISTANT}' && ${COMPOSE} ps"
    echo
    info "Ressources consommées :"
    distant "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' | grep -E 'NAME|eduhub' || true"
}

journaux() {
    verifier_serveur_defini journaux
    local service="${1:-}"
    distant "cd '${DOSSIER_DISTANT}' && ${COMPOSE} logs -f --tail=100 ${service}"
}

redemarrer() {
    verifier_serveur_defini redemarrer
    titre "Redémarrage de l'API"
    distant "cd '${DOSSIER_DISTANT}' && ${COMPOSE} restart api"
    ok "API redémarrée"
}

arreter() {
    verifier_serveur_defini arreter
    titre "Arrêt de la pile EduHub"
    attention "Les volumes sont conservés : la base et les pièces déposées restent en place."
    distant "cd '${DOSSIER_DISTANT}' && ${COMPOSE} down"
    ok "Pile arrêtée"
}

console() {
    verifier_serveur_defini console
    ssh "${OPTIONS_SSH[@]}" -t "${SERVEUR}" "cd '${DOSSIER_DISTANT}' && exec bash -l"
}

# ---- Aiguillage -------------------------------------------------------------

commande="${1:-aide}"
shift || true

case "${commande}" in
    verifier)   verifier "$@" ;;
    deployer)   deployer "$@" ;;
    migrer)     migrer "$@" ;;
    peupler)    peupler "$@" ;;
    https)      https "$@" ;;
    etat)       etat "$@" ;;
    journaux)   journaux "$@" ;;
    redemarrer) redemarrer "$@" ;;
    arreter)    arreter "$@" ;;
    console)    console "$@" ;;
    aide|*)     aide ;;
esac
