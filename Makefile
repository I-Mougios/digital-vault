.PHONY: mongo-shell format typecheck tests clear

mongo-shell:
	docker compose up -d --wait dv-mongo
	docker exec -it dv-mongo mongosh -u mongoadmin -p secret --authenticationDatabase admin

format:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run mypy src

tests:
	@uv run pytest -s -m "not slow"

clear:
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
