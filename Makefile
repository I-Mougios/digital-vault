.PHONY: mongo-shell fmt typecheck

mongo-shell:
	docker compose up -d --wait dv-mongo
	docker exec -it dv-mongo mongosh -u mongoadmin -p secret --authenticationDatabase admin

format:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run mypy src

