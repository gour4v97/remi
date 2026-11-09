.PHONY: help install dev-install test lint format clean run-remi run-dictation

help:
	@echo "Remi Suite - Development commands"
	@echo "  install         Install production dependencies"
	@echo "  dev-install     Install package in editable mode with dev dependencies"
	@echo "  test            Run pytest suite"
	@echo "  lint            Check code style with ruff"
	@echo "  format          Auto-format code with ruff"
	@echo "  clean           Remove build artifacts and cache"
	@echo "  run-remi        Launch Remi browser voice controller"
	@echo "  run-dictation   Launch Voice Trans dictation app"

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"

test:
	pytest tests/

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run-remi:
	python -m remi start

run-dictation:
	python -m remi dictation
