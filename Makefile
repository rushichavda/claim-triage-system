.PHONY: help install test lint format clean docker-build docker-up docker-down demo

help:  ## Show this help message
	@echo "Claim Triage System - Makefile Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -e ".[dev]"

test:  ## Run all tests
	pytest tests/ -v --cov=services --cov-report=term-missing

test-unit:  ## Run unit tests only
	pytest tests/unit/ -v

test-integration:  ## Run integration tests
	pytest tests/integration/ -v

test-adversarial:  ## Run adversarial tests
	pytest tests/adversarial/ -v

lint:  ## Run linting
	ruff check services/ tests/
	mypy services/

format:  ## Format code
	black services/ tests/
	ruff check --fix services/ tests/

clean:  ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/

docker-build:  ## Build Docker images
	docker-compose build

docker-up:  ## Start all services
	docker-compose up -d

docker-down:  ## Stop all services
	docker-compose down

docker-logs:  ## View logs
	docker-compose logs -f

demo:  ## Run demo script
	./run_demo.sh

setup-env:  ## Setup environment file
	cp .env.example .env
	@echo "Please edit .env file with your API keys"

db-init:  ## Initialize database
	docker-compose exec postgres psql -U postgres -d claim_triage -f /docker-entrypoint-initdb.d/init.sql

db-migrate:  ## Run database migrations
	alembic upgrade head

streamlit:  ## Run Streamlit UI locally
	streamlit run services/human_review/streamlit_app.py

index-policies:  ## Index policy documents
	python scripts/index_policies.py

metrics:  ## Show system metrics
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000 (admin/admin)"

all: clean install test lint  ## Run full CI pipeline locally
