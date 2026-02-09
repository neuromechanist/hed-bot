# Python Development Standards

## Version & Environment
- **Python 3.12+** minimum
- **Package Manager:** `uv` (fast Python package installer)
- **Virtual Environment:** `uv venv`
- **Install:** `uv pip install -e ".[dev]"`

## Code Style
- **Formatter:** `ruff format`
- **Linter:** `ruff check --fix --unsafe-fixes`
- **Line Length:** 88 characters (Black standard)
- **Imports:** Sorted with isort (via ruff)
- **Pre-commit hooks:** Ruff on staged files only

## Type Hints
- **Required for:** All public functions and methods
- **Tool:** `ty` for type checking
- **Example:**
```python
def process_data(items: list[dict[str, Any]]) -> pd.DataFrame:
    """Process raw data into DataFrame."""
    ...
```

## Project Structure
```
hedit/
├── src/
│   ├── agents/         # LangGraph agent implementations
│   ├── validation/     # HED validation integration
│   ├── utils/          # Helper functions
│   ├── api/            # FastAPI backend
│   ├── cli/            # CLI with Typer
│   └── telemetry/      # Usage telemetry
├── tests/              # Real tests only (pytest + coverage)
├── pyproject.toml      # Project config
└── .gitignore
```

## Common Patterns
- **Context Managers:** For resource management
- **Dataclasses/TypedDict:** For data structures and state
- **Pathlib:** For file operations (not os.path)
- **F-strings:** For string formatting
- **Async/await:** For API and LangGraph workflows

## Error Handling
```python
# Be specific with exceptions
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise  # Re-raise or handle appropriately
```

## Documentation
- **Docstrings:** Google style
- **Module docs:** At file top
- **Type hints:** Self-documenting code

---
*Use uv for everything. Ruff for formatting/linting. Real tests only.*
