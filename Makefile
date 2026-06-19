.PHONY: load ratios test report dashboard api clean setup

# Environment
VENV=venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

setup: $(VENV)
	$(PIP) install -r requirements.txt

$(VENV):
	python3 -m venv $(VENV)

# Load full data pipeline
load:
	$(PYTHON) -m src.etl.loader

# Execute financial ratio computations
ratios:
	$(PYTHON) -c "from src.etl.loader import compute_ratios; compute_ratios()"

# Run unit testing suite
test:
	$(PYTHON) -m pytest tests/ -v --cov=src/etl --cov-report=term

# Generate automated quality and processing logs
report:
	$(PYTHON) -c "from src.etl.validator import generate_report; generate_report()"

# Launch data overview telemetry interfaces
dashboard:
	$(PYTHON) -c "from src.etl.loader import launch_dashboard; launch_dashboard()"

# Set up downstream service entry points
api:
	$(PYTHON) -c "import uvicorn; uvicorn.run('src.etl.api:app', host='0.0.0.0', port=8000, reload=True)"

# Reset temporary build, environment, and database outputs
clean:
	rm -rf $(VENV)
	rm -f nifty100.db
	rm -rf __pycache__ src/__pycache__ src/etl/__pycache__ tests/__pycache__
	rm -f output/*.csv
	rm -rf .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
