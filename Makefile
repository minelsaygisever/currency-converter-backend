# Makefile - Currency Converter

# Default target
help:
	@echo "Currency Converter API - Available Commands:"
	@echo "  make install   → Install dependencies"
	@echo "  make run       → Start the API server"
	@echo "  make test      → Run tests"
	@echo "  make db        → Seed the database"
	@echo "  make clean     → Clean up build artifacts"
	@echo "  make docker    → Build the Docker image"
	@echo "  make version   → Show current version"

# Install dependencies
install:
	pip install -r requirements.txt
	@echo "✅ Installation complete!"

# Run the API server
run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
test:
	pytest tests/ -v

# Seed the database
db:
	python scripts/seed_currencies.py

# Build the Docker image
docker:
	docker build -t currency-converter:latest .
	@echo "✅ Docker image created!"

# Run the Docker container
docker-run:
	docker run -d \
		--name currency-api \
		-p 8000:8000 \
		--env-file .env \
		currency-converter:latest

# Clean up build artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/

# Show current version
version:
	@echo "Version: $(grep VERSION src/core/config.py | cut -d'"' -f2)"

# Bump version
bump-patch:
	python scripts/bump_version.py patch

bump-minor:
	python scripts/bump_version.py minor

bump-major:
	python scripts/bump_version.py major

.PHONY: help install run test db docker docker-run clean version bump-patch bump-minor bump-major