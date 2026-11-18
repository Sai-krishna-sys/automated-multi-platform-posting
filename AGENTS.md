# AGENTS.md

- Python 3.11 project; virtualenv lives in `venv/` (Python 3.11.9, isolated). Activate with `venv\Scripts\activate` (Windows) or use `venv\Scripts\python` / `venv\Scripts\pip` directly.
- Dependencies pinned in `requirements.txt` (FastAPI, uvicorn, httpx, pydantic, python-dotenv, PyYAML, pytest). Install: `venv\Scripts\pip install -r requirements.txt`.
- Run tests: `venv\Scripts\pytest` (or `venv\Scripts\python -m pytest`). Single file/test: `venv\Scripts\pytest tests\test_posting.py` / `...::test_name`.
- No lint, typecheck, formatter, or CI config exists in the repo; do not invent commands for them.
- Source layout: `app/` (config, schemas, main, `platforms/`, `services/`), tests in `tests/`. App source files are currently empty scaffolds.
- README, `.env.example`, and `.gitignore` are empty; no documented env vars or setup steps exist yet.