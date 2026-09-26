#!/usr/bin/env bash
# ===========================================================================
# EduHub — publication de l'API en HTTPS derrière nginx
#
# À exécuter sur le serveur, une seule fois. Relançable sans dommage : le
# fichier de site est réécrit à l'identique et certbot ne redemande pas un
# certificat encore valide.
#
# Ce script touche à nginx, pas à Docker : il n'active aucun pare-feu, ne
# réécrit pas /etc/docker/daemon.json et ne redémarre aucun conteneur. Les
# autres projets hébergés sur cette machine ne sont pas concernés — sauf s'ils
# servaient déjà quelque chose sur le port 80, cas que le script détecte et
# signale avant d'agir.
#
#   EDUHUB_DOMAINE=api.ezafri.com EDUHUB_PORT=8100 bash configurer-nginx.sh
#
# EDUHUB_COURRIEL fixe l'adresse d'inscription à Let's Encrypt. La valeur
# « aucun » s'inscrit sans adresse ; sans la variable, certbot pose la question.
# ===========================================================================
set -euo pipefail

DOMAINE="${EDUHUB_DOMAINE:-api.ezafri.com}"
PORT="${EDUHUB_PORT:-8100}"
COURRIEL="${EDUHUB_COURRIEL:-}"

VERT='\033[0;32m'; ROUGE='\033[0;31m'; JAUNE='\033[1;33m'; BLEU='\033[0;34m'; NEUTRE='\033[0m'
info()      { echo -e "${BLEU}[·]${NEUTRE} $1"; }
ok()        { echo -e "${VERT}[✓]${NEUTRE} $1"; }
attention() { echo -e "${JAUNE}[!]${NEUTRE} $1"; }
erreur()    { echo -e "${ROUGE}[✗]${NEUTRE} $1" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || erreur "à lancer en root (nginx et certbot écrivent dans /etc)."

echo "==========================================================="
echo "  EduHub — ${DOMAINE} → 127.0.0.1:${PORT}"
echo "==========================================================="
echo

# ---- 1. Le DNS doit pointer ici avant tout -----------------------------------
# Let's Encrypt valide la propriété du domaine en appelant http://DOMAINE/. Sans
# enregistrement A correct, certbot échoue et consomme un essai sur son quota.

info "Vérification du DNS…"
resolue=$(getent ahostsv4 "${DOMAINE}" 2>/dev/null | awk 'NR==1 {print $1}' || true)
if [ -z "${resolue}" ]; then
    erreur "${DOMAINE} ne résout vers aucune adresse.
      Créez d'abord un enregistrement A chez votre registrar :
          ${DOMAINE}  A  <adresse de ce serveur>
      puis attendez la propagation (quelques minutes à quelques heures)."
fi

publique=$(curl -fsS --max-time 10 https://api.ipify.org 2>/dev/null || true)
if [ -n "${publique}" ] && [ "${resolue}" != "${publique}" ]; then
    attention "${DOMAINE} résout vers ${resolue}, mais ce serveur se voit en ${publique}."
    attention "Si l'enregistrement A vient d'être modifié, attendez la propagation."
    read -r -p "  Continuer quand même ? (o/N) " reponse
    [[ "${reponse}" =~ ^[oO]$ ]] || { info "Abandon."; exit 0; }
else
    ok "${DOMAINE} → ${resolue}"
fi

# ---- 2. L'API doit déjà tourner ----------------------------------------------
info "Vérification de l'API…"
curl -fsS --max-time 5 "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1 \
    || erreur "aucune réponse sur http://127.0.0.1:${PORT}/health.
      Déployez l'API d'abord :  ./deploy_ment/scripts/deployer.sh deployer"
ok "l'API répond sur 127.0.0.1:${PORT}"

# ---- 3. nginx et certbot -----------------------------------------------------
if ! command -v nginx >/dev/null 2>&1; then
    info "Installation de nginx…"
    apt-get update -qq && apt-get install -y -qq nginx
fi
ok "nginx $(nginx -v 2>&1 | sed 's|nginx version: nginx/||')"

if ! command -v certbot >/dev/null 2>&1; then
    info "Installation de certbot…"
    apt-get install -y -qq certbot python3-certbot-nginx
fi
ok "certbot $(certbot --version 2>&1 | sed 's/certbot //')"

# Un autre service déjà sur le port 80 empêcherait nginx de démarrer et la
# validation du certificat d'aboutir.
if ss -ltnp 2>/dev/null | grep ':80 ' | grep -qv nginx; then
    attention "un autre service occupe le port 80 :"
    ss -ltnp 2>/dev/null | grep ':80 ' | sed 's/^/      /'
    erreur "libérez le port 80, ou intégrez EduHub à la configuration nginx existante."
fi

# Ce serveur sert déjà d'autres sites. On s'insère dans sa configuration, on ne
# la remplace pas : le fichier d'EduHub est un site de plus, sans
# « default_server », et les sites existants ne sont jamais touchés.
sites_actifs=$(find /etc/nginx/sites-enabled /etc/nginx/conf.d \( -type l -o -type f \) 2>/dev/null \
    | grep -cvE '/eduhub(\.conf)?$' || true)
if [ "${sites_actifs}" -gt 0 ]; then
    attention "${sites_actifs} site(s) nginx déjà configuré(s) — EduHub s'ajoute à côté,"
    attention "  aucun n'est modifié."
fi

# Debian et Ubuntu incluent sites-enabled/*, mais une configuration reprise
# d'ailleurs peut n'inclure que conf.d/ : le lien serait alors ignoré et le site
# resterait invisible, sans la moindre erreur.
if grep -qE '^\s*include\s+.*sites-enabled' /etc/nginx/nginx.conf; then
    DOSSIER_SITE=/etc/nginx/sites-available
    DOSSIER_LIEN=/etc/nginx/sites-enabled
    mkdir -p "${DOSSIER_SITE}" "${DOSSIER_LIEN}"
else
    attention "nginx.conf n'inclut pas sites-enabled : le site ira dans conf.d/"
    DOSSIER_SITE=/etc/nginx/conf.d
    DOSSIER_LIEN=""
    mkdir -p "${DOSSIER_SITE}"
fi

# ---- 4. Le site --------------------------------------------------------------
# On n'écrit ici que la partie HTTP : certbot ajoutera lui-même le bloc 443, le
# certificat et la redirection. Le laisser faire évite d'avoir à maintenir à la
# main des chemins de certificats et des directives TLS.

if [ -n "${DOSSIER_LIEN}" ]; then
    FICHIER_SITE="${DOSSIER_SITE}/eduhub"
else
    FICHIER_SITE="${DOSSIER_SITE}/eduhub.conf"
fi

info "Écriture de ${FICHIER_SITE}…"
cat > "${FICHIER_SITE}" <<CONF
# EduHub — API. Fichier généré par deploy_ment/scripts/configurer-nginx.sh.
# Le bloc HTTPS est ajouté par certbot : ne le recopiez pas ici à la main.
#
# Pas de « default_server » : ce site ne répond que pour ${DOMAINE} et
# laisse les autres sites de cette machine répondre pour les leurs.

server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAINE};

    # Dépôts de pièces justificatives : la valeur par défaut de nginx (1 Mo)
    # refuserait un scan de diplôme avec un 413 que le front ne sait pas
    # expliquer.
    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:${PORT};

        proxy_http_version 1.1;
        proxy_set_header Host              \$host;
        proxy_set_header X-Real-IP         \$remote_addr;
        proxy_set_header X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Génération des PDF (relevés, convocations, bulletins) et exports CSV :
        # quelques dizaines de secondes sur les gros lots.
        proxy_connect_timeout 10s;
        proxy_send_timeout   120s;
        proxy_read_timeout   120s;
    }
}
CONF

[ -n "${DOSSIER_LIEN}" ] && ln -sfn "${FICHIER_SITE}" "${DOSSIER_LIEN}/eduhub"

# Un « reload » et non un « restart » : les autres sites hébergés continuent de
# servir pendant le rechargement. Et si la configuration est invalide, on
# s'arrête avant d'y toucher.
nginx -t >/dev/null 2>&1 || { nginx -t; erreur "configuration nginx invalide."; }
systemctl reload nginx 2>/dev/null || systemctl start nginx

# Un rechargement est asynchrone : nginx signale le processus maître, qui lance
# de nouveaux ouvriers pendant que les anciens finissent leurs requêtes. Tant
# qu'ils n'ont pas pris le relais, c'est encore l'ancienne configuration qui
# répond. On attend donc la bascule au lieu de l'annoncer à l'aveugle.
#
# La vérification porte sur le CONTENU de la réponse, pas sur son code : un
# autre site déclaré « default_server » répondrait 200 à /health sans que la
# requête ait jamais atteint EduHub, et le script annoncerait un succès
# trompeur. Seule l'API renvoie {"status":"ok"}.
info "Attente de la prise en compte par nginx…"
bascule=""
for _ in $(seq 1 15); do
    reponse=$(curl -sS --max-time 3 -H "Host: ${DOMAINE}" http://127.0.0.1/health 2>/dev/null || true)
    case "${reponse}" in
        *'"status"'*'"ok"'*) bascule="oui"; break ;;
    esac
    sleep 1
done
if [ -z "${bascule}" ]; then
    attention "réponse obtenue : ${reponse:-aucune}"
    erreur "nginx a rechargé, mais ${DOMAINE} ne mène pas à l'API.
      Un autre bloc server capte probablement ce nom — souvent celui déclaré
      « default_server ». Pour le repérer :
          nginx -T | grep -nE 'server_name|listen |default_server'"
fi
ok "site actif en HTTP, les autres sites n'ont pas été interrompus"

# ---- 5. Le certificat --------------------------------------------------------
if [ -d "/etc/letsencrypt/live/${DOMAINE}" ]; then
    ok "certificat déjà présent — renouvellement géré par le minuteur de certbot"
else
    info "Obtention du certificat Let's Encrypt…"
    if [ "${COURRIEL}" = "aucun" ]; then
        # Inscription sans adresse : Let's Encrypt ne pourra pas prévenir si un
        # renouvellement échoue un jour. Le minuteur de certbot s'en charge
        # automatiquement, mais une panne passerait inaperçue jusqu'à
        # l'expiration. Une adresse s'ajoute après coup :
        #     certbot update_account --email vous@exemple.org
        attention "inscription sans adresse de courriel : aucune alerte d'expiration"
        certbot --nginx -d "${DOMAINE}" --redirect --agree-tos \
            --register-unsafely-without-email --non-interactive
    elif [ -n "${COURRIEL}" ]; then
        certbot --nginx -d "${DOMAINE}" --redirect --agree-tos --no-eff-email \
            -m "${COURRIEL}" --non-interactive
    else
        # Sans consigne, certbot demande l'adresse et l'acceptation des
        # conditions. C'est le mode par défaut, volontairement interactif.
        certbot --nginx -d "${DOMAINE}" --redirect
    fi
    ok "certificat installé, redirection HTTP → HTTPS en place"
fi

# ---- 6. Pare-feu -------------------------------------------------------------
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q '^Status: active'; then
    info "ufw est actif : ouverture de 80 et 443…"
    ufw allow 80/tcp >/dev/null
    ufw allow 443/tcp >/dev/null
    # Le port de l'API n'est plus publié que sur la boucle locale : s'il avait
    # été ouvert lors d'un déploiement en HTTP, la règle ne sert plus à rien.
    ufw delete allow "${PORT}/tcp" >/dev/null 2>&1 || true
    ok "80 et 443 autorisés, ${PORT} refermé"
else
    ok "ufw inactif ou absent — aucune règle à ajouter"
fi

echo
echo "==========================================================="
ok "L'API est publiée sur https://${DOMAINE}"
echo "==========================================================="
echo
echo "  Santé        : https://${DOMAINE}/health"
echo "  Documentation: https://${DOMAINE}/docs"
echo
echo "  Côté Vercel, renseignez :"
echo "      NEXT_PUBLIC_API_URL = https://${DOMAINE}/api/v1"
echo
echo "  Puis ajoutez l'origine Vercel à EDUHUB_CORS_ORIGINS dans"
echo "  deploy_ment/.env.production et redéployez."
echo
