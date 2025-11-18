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
	@source .venv/bin/activate && python -c "import asyncio; from backend.storage.sqlite import SQLiteStorage; storage = SQLiteStorage(); asyncio.run(storage.initialize()); print('✅ Database initialized successfully!')"

db-reset: ## Reset SQLite database (delete and recreate)
	@echo "Resetting database..."
	@rm -f data/events.db
	@make db-init

# Quick start for new developers
quickstart: ## Set up everything for a new developer (first time setup)
	@echo "🚀 Setting up ZapStream for development..."
	@echo ""
	@echo "Step 1: Setting up environment..."
	@make env-setup
	@echo ""
	@echo "Step 2: Setting up backend..."
	@make setup-backend
	@echo ""
	@echo "Step 3: Initializing database..."
	@make db-init
	@echo ""
	@echo "Step 4: Running tests to verify setup..."
	@make test-backend
	@echo ""
	@echo "✅ Setup complete! Run 'make dev' to start development servers."

# Health check for development environment
health-check: ## Check if development environment is healthy
	@echo "🔍 Checking development environment..."
	@echo ""
	@echo "📁 Checking directories..."
	@test -d ".venv" || (echo "❌ Python virtual environment not found. Run 'make setup-backend'."; exit 1)
	@test -f ".env" || (echo "❌ .env file not found. Run 'make env-setup'."; exit 1)
	@test -d "data" || (echo "❌ Data directory not found. Run 'make db-init'."; exit 1)
	@echo "✅ Directories OK"
	@echo ""
	@echo "🔧 Checking backend..."
	@source .venv/bin/activate && python -c "import backend.main" || (echo "❌ Backend imports failed. Run 'make setup-backend'."; exit 1)
	@echo "✅ Backend OK"
	@echo ""
	@echo "📊 Checking database..."
	@source .venv/bin/activate && python -c "import asyncio; from backend.storage.sqlite import SQLiteStorage; asyncio.run(SQLiteStorage().initialize())" || (echo "❌ Database check failed. Run 'make db-init'."; exit 1)
	@echo "✅ Database OK"
	@echo ""
	@echo "🎉 Development environment is healthy!"

# Development status overview
status: ## Show development environment status
	@echo "📊 ZapStream Development Status"
	@echo "=============================="
	@echo ""
	@echo "🐍 Python Backend:"
	@if [ -d ".venv" ]; then echo "  ✅ Virtual environment exists"; else echo "  ❌ Virtual environment missing"; fi
	@if [ -f ".env" ]; then echo "  ✅ .env file exists"; else echo "  ❌ .env file missing"; fi
	@if [ -d "data" ]; then echo "  ✅ Data directory exists"; else echo "  ❌ Data directory missing"; fi
	@echo ""
	@echo "🌐 Frontend:"
	@if [ -d "node_modules" ]; then echo "  ✅ Node modules installed"; else echo "  ❌ Node modules missing (run npm install)"; fi
	@echo ""
	@echo "🔗 Services:"
	@if pgrep -f "uvicorn.*backend.main" > /dev/null 2>&1; then echo "  ✅ Backend server running"; else echo "  ❌ Backend server not running"; fi
	@if pgrep -f "next" > /dev/null 2>&1; then echo "  ✅ Frontend server running"; else echo "  ❌ Frontend server not running"; fi
	@echo ""
	@echo "📝 Quick commands:"
	@echo "  make quickstart  - First time setup"
	@echo "  make dev         - Start both servers"
	@echo "  make status      - Show this status"
	@echo "  make health-check- Verify environment health"
