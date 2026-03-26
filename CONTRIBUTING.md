# Contributing to watchagent

Thanks for contributing.

## Development setup

1. Clone the repo.
2. Create a virtual environment.
3. Install dependencies.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Run locally

Python package:

```bash
watchagent list
watchagent show <id>
watchagent serve
```

Landing page:

```bash
cd watchagent-web
npm install
npm run dev
```

License server:

```bash
cd license-server
pip install -r requirements.txt
uvicorn app:app --reload
```

## Pull request checklist

- Add or update tests for changed behavior.
- Keep changes scoped and documented.
- Update README or docs when commands or APIs change.
- Ensure local build passes:

```bash
python -m compileall watchagent
cd watchagent-web && npm run build
```

## Code style

- Python: prefer clear type hints and small functions.
- Frontend: keep components readable and responsive.
- Keep public API names stable unless discussed in an issue.
