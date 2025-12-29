.PHONY: help dev-up dev-down dev-logs test clean install

help:
	@echo "Available commands:"
	@echo "  make dev-up      - Start PostgreSQL and backend locally"
	@echo "  make dev-down    - Stop all services"
	@echo "  make dev-logs    - View service logs"
	@echo "  make backend     - Run backend only (requires DB running)"
	@echo "  make frontend    - Run frontend dev server"
	@echo "  make test        - Run tests"
	@echo "  make install     - Install all dependencies"

install:
	pip install -r requirements.txt
	cd frontend && npm install

dev-up:
	docker-compose up -d
	@echo "PostgreSQL started. Waiting for it to be ready..."
	@sleep 3
	@echo "Database is ready on localhost:5432"

dev-down:
	docker-compose down

dev-logs:
	docker-compose logs -f

backend:
	python -m venv venv
	.\venv\Scripts\Activate.ps1
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

test:
	@echo "Running backend tests..."
	pytest tests/ -v

clean:
	docker-compose down -v
	rm -rf venv
	cd frontend && rm -rf node_modules
