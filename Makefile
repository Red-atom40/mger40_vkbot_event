.PHONY: run seed clean

run:
	uv run python src/main.py

seed:
	uv run python seed/seed.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
