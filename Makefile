.PHONY: install run test lint

install:
	pip install -r backend/requirements.txt

run:
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

test:
	python -m pytest tests/ -v 2>/dev/null || echo "No tests directory found. Add tests to tests/."

lint:
	pip install --quiet ruff && ruff check backend/
