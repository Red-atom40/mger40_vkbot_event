.PHONY: run seed clean

run:
	uv run python src/main.py

seed:
	uv run python seed/seed.py

clean:
	uv run python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__') if p.is_dir()]"
