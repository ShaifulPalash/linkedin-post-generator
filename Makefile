.PHONY: help install install-dev run test lint fmt preview-prompts smoke-test

help:
	@echo "make install         - install runtime dependencies"
	@echo "make install-dev     - install runtime + dev dependencies"
	@echo "make run             - run the Streamlit app"
	@echo "make preview-prompts - preview rendered prompts, no API key needed"
	@echo "make smoke-test      - run one real generation via chain.py (needs API key)"
	@echo "make test            - run the automated test suite (no API key needed)"
	@echo "make lint            - run ruff lint checks"
	@echo "make fmt             - auto-fix lint issues with ruff"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

run:
	streamlit run app.py

preview-prompts:
	python prompts.py

smoke-test:
	python chain.py

test:
	pytest tests/ -v

lint:
	ruff check .

fmt:
	ruff check . --fix
