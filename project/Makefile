# =============================================================================
# PPT Master - Makefile
# Common development and deployment commands
# =============================================================================

# Colors for terminal output
BLUE   := \033[36m
GREEN  := \033[32m
YELLOW := \033[33m
RED    := \033[31m
RESET  := \033[0m
BOLD   := \033[1m

# Compose files
COMPOSE_PROD := docker-compose.yml
COMPOSE_DEV  := docker-compose.dev.yml
COMPOSE_TOOL := docker-compose.dev.yml --profile tools

# Project name
PROJECT_NAME := ppt-master

# Default target
.DEFAULT_GOAL := help

# =============================================================================
# Help
# =============================================================================

.PHONY: help
help: ## Show this help message
	@echo ""
	@echo "$(BOLD)PPT Master - Available Commands$(RESET)"
	@echo "========================================"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(BLUE)%-20s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

# =============================================================================
# Development Commands
# =============================================================================

.PHONY: dev
dev: ## Start development environment (with hot-reload)
	@echo "$(GREEN)Starting development environment...$(RESET)"
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev up -d
	@echo ""
	@echo "$(GREEN)✓ Development environment is running!$(RESET)"
	@echo "  Frontend:    http://localhost:5173"
	@echo "  Backend API: http://localhost:8000"
	@echo "  API Docs:    http://localhost:8000/docs"
	@echo "  MinIO:       http://localhost:9001 (console)"
	@echo ""
	@echo "$(YELLOW)To view logs: make logs-dev$(RESET)"

.PHONY: dev-tools
dev-tools: ## Start development environment with pgAdmin and RedisInsight
	@echo "$(GREEN)Starting development environment with tools...$(RESET)"
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev --profile tools up -d
	@echo ""
	@echo "$(GREEN)✓ Development environment with tools is running!$(RESET)"
	@echo "  Frontend:      http://localhost:5173"
	@echo "  Backend API:   http://localhost:8000"
	@echo "  API Docs:      http://localhost:8000/docs"
	@echo "  MinIO:         http://localhost:9001 (console)"
	@echo "  pgAdmin:       http://localhost:5050"
	@echo "  RedisInsight:  http://localhost:5540"
	@echo ""

.PHONY: dev-build
dev-build: ## Build development images
	@echo "$(GREEN)Building development images...$(RESET)"
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev build

.PHONY: dev-down
dev-down: ## Stop development environment
	@echo "$(YELLOW)Stopping development environment...$(RESET)"
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev down

.PHONY: dev-down-volumes
dev-down-volumes: ## Stop development environment and remove all data volumes
	@echo "$(RED)Stopping development environment and removing volumes...$(RESET)"
	@read -p "Are you sure? This will delete all data! [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev down -v; \
		echo "$(GREEN)✓ All development data removed.$(RESET)"; \
	else \
		echo "$(YELLOW)Cancelled.$(RESET)"; \
	fi

# =============================================================================
# Production Commands
# =============================================================================

.PHONY: build
build: ## Build production images
	@echo "$(GREEN)Building production images...$(RESET)"
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) build

.PHONY: build-no-cache
build-no-cache: ## Build production images without cache
	@echo "$(GREEN)Building production images (no cache)...$(RESET)"
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) build --no-cache

.PHONY: up
up: ## Start production environment
	@echo "$(GREEN)Starting production environment...$(RESET)"
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) up -d
	@echo ""
	@echo "$(GREEN)✓ Production environment is running!$(RESET)"
	@echo "  Frontend: http://localhost"
	@echo ""
	@echo "$(YELLOW)To view logs: make logs$(RESET)"

.PHONY: up-pull
up-pull: ## Pull latest images and start production environment
	@echo "$(GREEN)Pulling latest images and starting...$(RESET)"
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) pull
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) up -d

.PHONY: down
down: ## Stop production environment
	@echo "$(YELLOW)Stopping production environment...$(RESET)"
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) down

.PHONY: down-volumes
down-volumes: ## Stop production environment and remove all data volumes
	@echo "$(RED)Stopping production environment and removing volumes...$(RESET)"
	@read -p "Are you sure? This will delete all data! [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) down -v; \
		echo "$(GREEN)✓ All production data removed.$(RESET)"; \
	else \
		echo "$(YELLOW)Cancelled.$(RESET)"; \
	fi

# =============================================================================
# Log Commands
# =============================================================================

.PHONY: logs
logs: ## View production logs (follow mode)
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) logs -f

.PHONY: logs-backend
logs-backend: ## View production backend logs
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) logs -f backend

.PHONY: logs-celery
logs-celery: ## View production celery worker logs
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) logs -f celery_worker

.PHONY: logs-dev
logs-dev: ## View development logs (follow mode)
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev logs -f

.PHONY: logs-dev-backend
logs-dev-backend: ## View development backend logs
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev logs -f backend

# =============================================================================
# Database Commands
# =============================================================================

.PHONY: migrate
migrate: ## Run database migrations in production
	@echo "$(GREEN)Running database migrations...$(RESET)"
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) exec backend alembic upgrade head

.PHONY: migrate-dev
migrate-dev: ## Run database migrations in development
	@echo "$(GREEN)Running database migrations (dev)...$(RESET)"
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev exec backend alembic upgrade head

.PHONY: makemigrations
makemigrations: ## Create new Alembic migration
	@echo "$(GREEN)Creating new migration...$(RESET)"
	@read -p "Enter migration message: " msg; \
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev exec backend alembic revision --autogenerate -m "$$msg"

.PHONY: db-shell
db-shell: ## Open PostgreSQL shell in development
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev exec db psql -U pptmaster -d pptmaster

.PHONY: db-backup
db-backup: ## Backup PostgreSQL database
	@echo "$(GREEN)Creating database backup...$(RESET)"
	@mkdir -p backups
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) exec -T db pg_dump \
		-U pptmaster -d pptmaster -F c > backups/pptmaster_$$timestamp.dump; \
	echo "$(GREEN)✓ Backup saved to: backups/pptmaster_$$timestamp.dump$(RESET)"

.PHONY: db-restore
db-restore: ## Restore PostgreSQL database (usage: make db-restore FILE=backups/xxx.dump)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Error: Please specify FILE=path/to/backup.dump$(RESET)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Restoring database from $(FILE)...$(RESET)"
	@read -p "This will overwrite existing data! Continue? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) exec -T db pg_restore \
			-U pptmaster -d pptmaster --clean --if-exists < $(FILE); \
		echo "$(GREEN)✓ Database restored.$(RESET)"; \
	else \
		echo "$(YELLOW)Cancelled.$(RESET)"; \
	fi

# =============================================================================
# Testing Commands
# =============================================================================

.PHONY: test
test: ## Run backend tests in development container
	@echo "$(GREEN)Running tests...$(RESET)"
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev exec backend pytest -v

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	@echo "$(GREEN)Running tests with coverage...$(RESET)"
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev exec backend \
		pytest -v --cov=app --cov-report=term-missing --cov-report=html

.PHONY: test-specific
test-specific: ## Run specific test file (usage: make test-specific FILE=tests/test_api.py)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Error: Please specify FILE=path/to/test.py$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Running tests: $(FILE)$(RESET)"
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev exec backend pytest -v $(FILE)

.PHONY: lint
lint: ## Run code linting (flake8, mypy)
	@echo "$(GREEN)Running linters...$(RESET)"
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev exec backend \
		sh -c "flake8 app/ && mypy app/"

.PHONY: format
format: ## Format code with black and isort
	@echo "$(GREEN)Formatting code...$(RESET)"
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev exec backend \
		sh -c "black app/ && isort app/"

# =============================================================================
# Celery Commands
# =============================================================================

.PHONY: celery-logs
celery-logs: ## View Celery worker logs
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) logs -f celery_worker

.PHONY: celery-status
celery-status: ## Check Celery worker status
	@echo "$(GREEN)Checking Celery status...$(RESET)"
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) exec celery_worker \
		celery -A app.celery_app inspect active --timeout 10

.PHONY: celery-purge
celery-purge: ## Purge all Celery tasks from queue
	@echo "$(YELLOW)Purging all Celery tasks...$(RESET)"
	@read -p "Are you sure? This will remove all pending tasks! [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) exec celery_worker \
			celery -A app.celery_app purge -f; \
	else \
		echo "$(YELLOW)Cancelled.$(RESET)"; \
	fi

# =============================================================================
# Maintenance Commands
# =============================================================================

.PHONY: ps
ps: ## Show running containers
	@echo "$(BOLD)Production containers:$(RESET)"
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) ps
	@echo ""
	@echo "$(BOLD)Development containers:$(RESET)"
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev ps

.PHONY: prune
prune: ## Clean up unused Docker resources
	@echo "$(YELLOW)Cleaning up unused Docker resources...$(RESET)"
	@read -p "This will remove unused images, containers, networks. Continue? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker system prune -f; \
		echo "$(GREEN)✓ Cleanup complete.$(RESET)"; \
	else \
		echo "$(YELLOW)Cancelled.$(RESET)"; \
	fi

.PHONY: shell-backend
shell-backend: ## Open shell in production backend container
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) exec backend bash

.PHONY: shell-backend-dev
shell-backend-dev: ## Open shell in development backend container
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev exec backend bash

.PHONY: restart-backend
restart-backend: ## Restart production backend
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) restart backend

.PHONY: restart-celery
restart-celery: ## Restart Celery workers
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) restart celery_worker

.PHONY: restart-all
restart-all: ## Restart all production services
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) restart

# =============================================================================
# CI/CD Commands
# =============================================================================

.PHONY: ci-build
ci-build: ## Build images for CI pipeline
	@echo "$(GREEN)Building images for CI...$(RESET)"
	docker compose -f $(COMPOSE_PROD) -p $(PROJECT_NAME) build --parallel

.PHONY: ci-test
ci-test: ## Run tests in CI environment
	@echo "$(GREEN)Running CI tests...$(RESET)"
	make dev-build
	docker compose -f $(COMPOSE_DEV) -p $(PROJECT_NAME)-dev run --rm backend \
		pytest -v --cov=app --cov-report=xml --cov-report=term

.PHONY: ci-push
ci-push: ## Push images to registry (set REGISTRY env var)
	@if [ -z "$(REGISTRY)" ]; then \
		echo "$(RED)Error: Please set REGISTRY environment variable$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Pushing images to $(REGISTRY)...$(RESET)"
	docker tag $(PROJECT_NAME)-backend $(REGISTRY)/$(PROJECT_NAME)-backend:latest
	docker tag $(PROJECT_NAME)-frontend $(REGISTRY)/$(PROJECT_NAME)-frontend:latest
	docker tag $(PROJECT_NAME)-celery $(REGISTRY)/$(PROJECT_NAME)-celery:latest
	docker push $(REGISTRY)/$(PROJECT_NAME)-backend:latest
	docker push $(REGISTRY)/$(PROJECT_NAME)-frontend:latest
	docker push $(REGISTRY)/$(PROJECT_NAME)-celery:latest

# =============================================================================
# Setup Commands
# =============================================================================

.PHONY: setup
setup: ## Initial setup: copy .env and create directories
	@echo "$(GREEN)Running initial setup...$(RESET)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✓ Created .env from .env.example$(RESET)"; \
		echo "$(YELLOW)⚠ Please edit .env with your actual values before starting!$(RESET)"; \
	else \
		echo "$(YELLOW).env already exists, skipping.$(RESET)"; \
	fi
	@mkdir -p backups logs
	@echo "$(GREEN)✓ Setup complete!$(RESET)"

.PHONY: init
init: setup dev ## Full initialization: setup + start development
