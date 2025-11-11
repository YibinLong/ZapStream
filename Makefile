# ZapStream Development Makefile

.PHONY: help dev dev-frontend dev-backend test test-backend test-backend-unit test-backend-api lint lint-frontend lint-backend clean setup-backend

# Default target
help: ## Show this help message
	@echo "ZapStream Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Frontend commands (existing Next.js)
dev-frontend: ## Run frontend development server (Next.js)
	npm run dev

build-frontend: ## Build frontend for production
	npm run build

lint-frontend: ## Lint frontend code
	npm run lint

# Backend commands (FastAPI)
setup-backend: ## Set up Python virtual environment and install dependencies
	@if [ ! -d ".venv" ]; then \
		echo "Creating Python virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@echo "Activating virtual environment and installing dependencies..."
	@source .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
	@echo "Backend setup complete!"

dev-backend: ## Run backend development server (FastAPI)
	@echo "Starting FastAPI backend server..."
	@source .venv/bin/activate && python -m uvicorn backend.main:app --reload --port $(or ${BACKEND_PORT},8000)

dev-backend-dbg: ## Run backend with debug logging
	@echo "Starting FastAPI backend server with debug logging..."
	@source .venv/bin/activate && LOG_LEVEL=DEBUG python -m uvicorn backend.main:app --reload --port $(or ${BACKEND_PORT},8000)

test-backend: ## Run all backend tests
	@echo "Running backend test suite..."
	@source .venv/bin/activate && pytest tests/ -v

test-backend-unit: ## Run backend unit tests only
	@echo "Running backend unit tests..."
	@source .venv/bin/activate && pytest tests/ -v -m "not integration"

test-backend-api: ## Run backend API tests only
	@echo "Running backend API integration tests..."
	@source .venv/bin/activate && pytest tests/ -v -m "integration"

test-backend-cov: ## Run backend tests with coverage
	@echo "Running backend tests with coverage..."
	@source .venv/bin/activate && pytest tests/ -v --cov=backend --cov-report=html --cov-report=term-missing

lint-backend: ## Lint and format backend code
	@echo "Linting backend code..."
	@source .venv/bin/activate && ruff check backend/
	@echo "Checking backend code formatting..."
	@source .venv/bin/activate && ruff format --check backend/

lint-backend-fix: ## Fix backend linting issues
	@echo "Fixing backend code formatting..."
	@source .venv/bin/activate && ruff format backend/
	@echo "Running ruff check with auto-fix..."
	@source .venv/bin/activate && ruff check backend/ --fix

# Combined commands
dev: ## Run both frontend and backend development servers
	@echo "Starting full-stack development environment..."
	@make dev-backend & make dev-frontend

lint: ## Lint both frontend and backend code
	@echo "Linting all code..."
	@make lint-frontend
	@make lint-backend

test: ## Run all tests (frontend and backend)
	@echo "Running all tests..."
	@make test-backend

# Deployment (existing)
deploy: ## Deploy frontend to AWS Amplify (existing script)
	./deploy.sh

# Maintenance
clean: ## Clean up temporary files and caches
	@echo "Cleaning up..."
	@rm -rf .pytest_cache/
	@rm -rf .coverage
	@rm -rf htmlcov/
	@rm -rf .ruff_cache/
	@rm -rf .mypy_cache/
	@rm -rf dist/
	@rm -rf build/
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@echo "Cleanup complete!"

# Environment management
env-setup: ## Copy .env.example to .env for local development
	@if [ ! -f ".env" ]; then \
		echo "Creating .env from .env.example..."; \
		cp .env.example .env; \
		echo "✅ .env created! Please update it with your configuration."; \
	else \
		echo "⚠️  .env already exists. Update it manually if needed."; \
	fi

# Database management
db-init: ## Initialize SQLite database for development
	@echo "Initializing SQLite database..."
	@mkdir -p data
	@source .venv/bin/activate && python -c "import asyncio; from backend.storage.sqlite import SQLiteStorage; async def main(): storage = SQLiteStorage(); await storage.initialize(); print('✅ Database initialized successfully!'); asyncio.run(main())"

db-reset: ## Reset SQLite database (delete and recreate)
	@echo "Resetting database..."
	@rm -f data/events.db
	@make db-init