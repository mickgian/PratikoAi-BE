install:
	pip install uv
	uv sync

set-env:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make set-env ENV=development|staging|production"; \
		exit 1; \
	fi
	@if [ "$(ENV)" != "development" ] && [ "$(ENV)" != "staging" ] && [ "$(ENV)" != "production" ] && [ "$(ENV)" != "test" ]; then \
		echo "ENV is not valid. Must be one of: development, staging, production, test"; \
		exit 1; \
	fi
	@echo "Setting environment to $(ENV)"
	@bash -c "source scripts/set_env.sh $(ENV)"

prod:
	@echo "Starting server in production environment"
	@bash -c "source scripts/set_env.sh production && ./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

staging:
	@echo "Starting server in staging environment"
	@bash -c "source scripts/set_env.sh staging && ./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

dev:
	@echo "Starting server in development environment"
	@bash -c "source scripts/set_env.sh development && uv run uvicorn app.main:app --reload --port 8000"

# Evaluation commands
eval:
	@echo "Running evaluation with interactive mode"
	@bash -c "source scripts/set_env.sh ${ENV:-development} && python -m evals.main --interactive"

eval-quick:
	@echo "Running evaluation with default settings"
	@bash -c "source scripts/set_env.sh ${ENV:-development} && python -m evals.main --quick"

eval-no-report:
	@echo "Running evaluation without generating report"
	@bash -c "source scripts/set_env.sh ${ENV:-development} && python -m evals.main --no-report"

lint:
	ruff check .

format:
	ruff format .

clean:
	rm -rf .venv
	rm -rf __pycache__
	rm -rf .pytest_cache

# Testing targets
test:
	@echo "Running all tests..."
	@bash -c "source scripts/set_env.sh test && python -m pytest tests/ -v"

test-streaming:
	@echo "Running streaming protection tests..."
	@bash -c "source scripts/set_env.sh test && python -m pytest \
		tests/test_sse_format_validation.py \
		tests/api/test_chatbot_streaming_integration.py \
		tests/langgraph/test_buffered_streaming_timing.py \
		-v --tb=line"

test-quick:
	@echo "Running quick validation tests..."
	@bash -c "source scripts/set_env.sh test && python -m pytest \
		tests/test_sse_format_validation.py \
		tests/test_tool_guardrails.py \
		tests/test_retrieval_gate.py \
		-v --tb=line"

test-coverage:
	@echo "Running tests with coverage..."
	@bash -c "source scripts/set_env.sh test && python -m pytest tests/ \
		-v --cov=app --cov-report=html --cov-report=term-missing"

docker-build:
	docker build -t fastapi-langgraph-template .

docker-build-env:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make docker-build-env ENV=development|staging|production"; \
		exit 1; \
	fi
	@if [ "$(ENV)" != "development" ] && [ "$(ENV)" != "staging" ] && [ "$(ENV)" != "production" ]; then \
		echo "ENV is not valid. Must be one of: development, staging, production"; \
		exit 1; \
	fi
	@./scripts/build-docker.sh $(ENV)

docker-run:
	docker run -p 8000:8000 fastapi-langgraph-template

docker-run-env:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make docker-run-env ENV=development|staging|production"; \
		exit 1; \
	fi
	@if [ "$(ENV)" != "development" ] && [ "$(ENV)" != "staging" ] && [ "$(ENV)" != "production" ]; then \
		echo "ENV is not valid. Must be one of: development, staging, production"; \
		exit 1; \
	fi
	@./scripts/run-docker.sh $(ENV)

docker-logs:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make docker-logs ENV=development|staging|production"; \
		exit 1; \
	fi
	@if [ "$(ENV)" != "development" ] && [ "$(ENV)" != "staging" ] && [ "$(ENV)" != "production" ]; then \
		echo "ENV is not valid. Must be one of: development, staging, production"; \
		exit 1; \
	fi
	@./scripts/logs-docker.sh $(ENV)

docker-stop:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make docker-stop ENV=development|staging|production"; \
		exit 1; \
	fi
	@if [ "$(ENV)" != "development" ] && [ "$(ENV)" != "staging" ] && [ "$(ENV)" != "production" ]; then \
		echo "ENV is not valid. Must be one of: development, staging, production"; \
		exit 1; \
	fi
	@./scripts/stop-docker.sh $(ENV)

# Docker Compose commands for the entire stack
docker-compose-up:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make docker-compose-up ENV=development|staging|production"; \
		exit 1; \
	fi
	@if [ "$(ENV)" != "development" ] && [ "$(ENV)" != "staging" ] && [ "$(ENV)" != "production" ]; then \
		echo "ENV is not valid. Must be one of: development, staging, production"; \
		exit 1; \
	fi
	APP_ENV=$(ENV) docker-compose up -d

docker-compose-down:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make docker-compose-down ENV=development|staging|production"; \
		exit 1; \
	fi
	APP_ENV=$(ENV) docker-compose down

docker-compose-logs:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make docker-compose-logs ENV=development|staging|production"; \
		exit 1; \
	fi
	APP_ENV=$(ENV) docker-compose logs -f

# Monitoring automation commands
monitoring-daily:
	@echo "Running daily monitoring report..."
	@python monitoring/scripts/run_monitoring.py daily-report --email --format html

monitoring-costs:
	@echo "Running cost optimization analysis..."
	@python monitoring/scripts/run_monitoring.py optimize-costs --detailed

monitoring-health:
	@echo "Running system health check..."
	@python monitoring/scripts/run_monitoring.py health-check

monitoring-backup:
	@echo "Backing up Grafana dashboards..."
	@python monitoring/scripts/run_monitoring.py backup-dashboards

monitoring-suite:
	@echo "Running full monitoring suite..."
	@python monitoring/scripts/run_monitoring.py full-suite --email --webhook

monitoring-setup:
	@echo "Setting up monitoring task scheduling..."
	@python monitoring/scripts/run_monitoring.py schedule

monitoring-compare:
	@echo "Comparing current dashboards with backups..."
	@python monitoring/scripts/backup_dashboards.py --compare

monitoring-test:
	@echo "Testing alert configurations..."
	@python monitoring/test_alerts.py --test all

# Complete monitoring stack management
monitoring-up:
	@echo "Starting complete monitoring stack..."
	@docker-compose up -d prometheus grafana alertmanager redis-exporter postgres-exporter node-exporter cadvisor

monitoring-start: monitoring-up
	@echo "Monitoring stack started successfully!"
	@echo "Access URLs:"
	@echo "  Grafana:     http://localhost:3000 (admin/admin)"
	@echo "  Prometheus:  http://localhost:9090"
	@echo "  AlertManager: http://localhost:9093"

monitoring-stop:
	@echo "Stopping monitoring stack..."
	@docker-compose stop prometheus grafana alertmanager redis-exporter postgres-exporter node-exporter cadvisor

monitoring-down:
	@echo "Stopping and removing monitoring containers..."
	@docker-compose down prometheus grafana alertmanager redis-exporter postgres-exporter node-exporter cadvisor

monitoring-logs:
	@echo "Viewing monitoring stack logs..."
	@docker-compose logs -f prometheus grafana alertmanager

monitoring-status:
	@echo "Monitoring stack status:"
	@docker-compose ps prometheus grafana alertmanager redis-exporter postgres-exporter node-exporter cadvisor

monitoring-reset:
	@echo "Resetting monitoring data (WARNING: This will delete all metrics and dashboards)..."
	@read -p "Are you sure? Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ] || exit 1
	@echo "Stopping monitoring stack..."
	@docker-compose down prometheus grafana alertmanager
	@echo "Removing monitoring volumes..."
	@docker volume rm pratikoai-be_prometheus-data pratikoai-be_grafana-storage pratikoai-be_alertmanager-data 2>/dev/null || true
	@echo "Restarting monitoring stack..."
	@make monitoring-up
	@echo "Monitoring stack reset complete!"

monitoring-backup-volumes:
	@echo "Backing up monitoring volumes..."
	@mkdir -p monitoring/backups/volumes
	@docker run --rm -v pratikoai-be_prometheus-data:/data -v $(PWD)/monitoring/backups/volumes:/backup alpine tar czf /backup/prometheus-data-$(shell date +%Y%m%d_%H%M%S).tar.gz -C /data .
	@docker run --rm -v pratikoai-be_grafana-storage:/data -v $(PWD)/monitoring/backups/volumes:/backup alpine tar czf /backup/grafana-storage-$(shell date +%Y%m%d_%H%M%S).tar.gz -C /data .
	@echo "Volume backups completed in monitoring/backups/volumes/"

monitoring-restore-volumes:
	@echo "Available volume backups:"
	@ls -la monitoring/backups/volumes/ 2>/dev/null || echo "No backups found"
	@echo "To restore, specify backup file: make monitoring-restore-volume BACKUP=filename.tar.gz"

monitoring-restore-volume:
	@if [ -z "$(BACKUP)" ]; then echo "Usage: make monitoring-restore-volume BACKUP=filename.tar.gz"; exit 1; fi
	@echo "Restoring volume from $(BACKUP)..."
	@make monitoring-down
	@docker volume rm pratikoai-be_prometheus-data pratikoai-be_grafana-storage 2>/dev/null || true
	@docker volume create pratikoai-be_prometheus-data
	@docker volume create pratikoai-be_grafana-storage
	@docker run --rm -v pratikoai-be_prometheus-data:/data -v $(PWD)/monitoring/backups/volumes:/backup alpine tar xzf /backup/$(BACKUP) -C /data
	@make monitoring-up
	@echo "Volume restoration completed!"

# Help
help:
	@echo "Usage: make <target>"
	@echo "Targets:"
	@echo "  install: Install dependencies"
	@echo "  set-env ENV=<environment>: Set environment variables (development, staging, production, test)"
	@echo "  run ENV=<environment>: Set environment and run server"
	@echo "  prod: Run server in production environment"
	@echo "  staging: Run server in staging environment"
	@echo "  dev: Run server in development environment"
	@echo "  eval: Run evaluation with interactive mode"
	@echo "  eval-quick: Run evaluation with default settings"
	@echo "  eval-no-report: Run evaluation without generating report"
	@echo "  test: Run all tests"
	@echo "  test-streaming: Run streaming protection tests"
	@echo "  test-quick: Run quick validation tests"
	@echo "  test-coverage: Run tests with coverage report"
	@echo "  clean: Clean up"
	@echo "  docker-build: Build default Docker image"
	@echo "  docker-build-env ENV=<environment>: Build Docker image for specific environment"
	@echo "  docker-run: Run default Docker container"
	@echo "  docker-run-env ENV=<environment>: Run Docker container for specific environment"
	@echo "  docker-logs ENV=<environment>: View logs from running container"
	@echo "  docker-stop ENV=<environment>: Stop and remove container"
	@echo "  docker-compose-up: Start the entire stack (API, Prometheus, Grafana)"
	@echo "  docker-compose-down: Stop the entire stack"
	@echo "  docker-compose-logs: View logs from all services"
	@echo ""
	@echo "Monitoring Commands:"
	@echo "  monitoring-daily: Generate daily monitoring report with email"
	@echo "  monitoring-costs: Run cost optimization analysis"
	@echo "  monitoring-health: Run comprehensive health check"
	@echo "  monitoring-backup: Backup Grafana dashboards"
	@echo "  monitoring-suite: Run full monitoring automation suite"
	@echo "  monitoring-setup: Set up automated monitoring scheduling"
	@echo "  monitoring-compare: Compare dashboards with previous backups"
	@echo "  monitoring-test: Test alert configurations"
	@echo "  monitoring-start: Start monitoring stack (Prometheus + Grafana)"
	@echo "  monitoring-stop: Stop monitoring stack"
	@echo "  monitoring-logs: View monitoring stack logs"

# PDF Quality Repair Commands
repair-qa:
	@echo "Running PDF quality repair QA batch (limit: 5)..."
	@bash scripts/ops/repair_one_click.sh --env development --limit 5

repair-full:
	@echo "Running full PDF quality repair pass..."
	@bash scripts/ops/repair_one_click.sh --env development --full

quality-report:
	@echo "Generating quality report..."
	@mkdir -p reports/quality/$$(date +%Y%m%d_%H%M)
	@bash -c "source scripts/set_env.sh development && \
		python scripts/diag/find_junk_chunks.py | tee reports/quality/$$(date +%Y%m%d_%H%M)/find_junk.txt && \
		python scripts/diag/quality_report.py | tee reports/quality/$$(date +%Y%m%d_%H%M)/quality_report.txt"
	@echo "Reports saved to reports/quality/$$(date +%Y%m%d_%H%M)/"

repair-dry-run:
	@echo "Running PDF repair in dry-run mode..."
	@bash scripts/ops/repair_one_click.sh --env development --limit 5 --dry-run --skip-dump

repair-mark-junk:
	@echo "Marking obvious junk chunks..."
	@bash -c "source scripts/set_env.sh development && python scripts/diag/find_junk_chunks.py --mark"
