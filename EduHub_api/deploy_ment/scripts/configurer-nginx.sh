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
#   EDUHUB_DOMAINE=eduhub.ezafri.com EDUHUB_PORT=8100 bash configurer-nginx.sh
# ===========================================================================
set -euo pipefail

DOMAINE="${EDUHUB_DOMAINE:-eduhub.ezafri.com}"
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

# ---- 4. Le site --------------------------------------------------------------
# On n'écrit ici que la partie HTTP : certbot ajoutera lui-même le bloc 443, le
# certificat et la redirection. Le laisser faire évite d'avoir à maintenir à la
# main des chemins de certificats et des directives TLS.

info "Écriture de /etc/nginx/sites-available/eduhub…"
cat > /etc/nginx/sites-available/eduhub <<CONF
# EduHub — API. Fichier généré par deploy_ment/scripts/configurer-nginx.sh.
# Le bloc HTTPS est ajouté par certbot : ne le recopiez pas ici à la main.

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

ln -sfn /etc/nginx/sites-available/eduhub /etc/nginx/sites-enabled/eduhub
nginx -t >/dev/null 2>&1 || { nginx -t; erreur "configuration nginx invalide."; }
systemctl reload nginx 2>/dev/null || systemctl start nginx
ok "site actif en HTTP"

# ---- 5. Le certificat --------------------------------------------------------
if [ -d "/etc/letsencrypt/live/${DOMAINE}" ]; then
    ok "certificat déjà présent — renouvellement géré par le minuteur de certbot"
else
    info "Obtention du certificat Let's Encrypt…"
    if [ -n "${COURRIEL}" ]; then
        certbot --nginx -d "${DOMAINE}" --redirect --agree-tos --no-eff-email \
            -m "${COURRIEL}" --non-interactive
    else
        # Sans courriel fourni, certbot le demande — ainsi que l'acceptation des
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
