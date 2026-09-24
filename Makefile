# ============================================================
#  EduHub — Système Intégré de Gestion de l'Éducation
# ============================================================

COMPOSE := docker compose
API     := EduHub_api
FRONT   := EduHub_front

.DEFAULT_GOAL := help

# ---------- Infrastructure ----------

.PHONY: up
up: ## Démarre toute la pile (postgres, redis, minio, api, front)
	$(COMPOSE) up -d

.PHONY: infra
infra: ## Démarre uniquement postgres, redis et minio
	$(COMPOSE) up -d postgres redis minio

.PHONY: down
down: ## Arrête la pile
	$(COMPOSE) down

.PHONY: logs
logs: ## Suit les logs de l'API
	$(COMPOSE) logs -f api

.PHONY: ps
ps: ## Affiche l'état des services
	$(COMPOSE) ps

# ---------- Base de données ----------

.PHONY: migrate
migrate: ## Applique les migrations Alembic
	cd $(API) && alembic upgrade head

.PHONY: migration
migration: ## Génère une migration — usage: make migration m="message"
	cd $(API) && alembic revision --autogenerate -m "$(m)"

.PHONY: downgrade
downgrade: ## Revient d'une migration en arrière
	cd $(API) && alembic downgrade -1

.PHONY: reset-db
reset-db: ## Détruit et recrée la base de données
	cd $(API) && python -m app.cli reset-db

.PHONY: seed
seed: ## Génère le jeu de données fictives complet
	cd $(API) && python -m app.seed

.PHONY: reseed
reseed: reset-db migrate seed ## Reconstruit entièrement l'environnement de démonstration

# ---------- Développement ----------

.PHONY: api-dev
api-dev: ## Lance l'API en rechargement à chaud
	cd $(API) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: front-dev
front-dev: ## Lance le frontend en rechargement à chaud
	cd $(FRONT) && npm run dev

.PHONY: install
install: ## Installe les dépendances backend et frontend
	cd $(API) && uv pip install -e ".[dev]"
	cd $(FRONT) && npm install

# ---------- Qualité ----------

.PHONY: lint
lint: ## Analyse statique du backend et du frontend
	cd $(API) && ruff check app && ruff format --check app
	cd $(FRONT) && npm run lint

.PHONY: format
format: ## Formate le code
	cd $(API) && ruff format app && ruff check --fix app
	cd $(FRONT) && npm run format

.PHONY: typecheck
typecheck: ## Vérifie les types
	cd $(API) && mypy app
	cd $(FRONT) && npm run typecheck

.PHONY: test
test: ## Exécute les tests backend
	cd $(API) && pytest -q

# ---------- Aide ----------

.PHONY: help
help: ## Affiche cette aide
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
