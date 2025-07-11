# Agent Instructions for Abyssal Tome

This document provides guidance for AI agents working on the Abyssal Tome codebase.

## Development Environment Setup

This project uses `uv` for managing Python environments and dependencies, targeting **Python 3.13**.

1.  **Install `uv`:**
    If you don't have `uv` installed, follow the official installation instructions from [Astral's `uv` documentation](https://astral.sh/docs/uv/install).

2.  **Create Virtual Environment:**
    Navigate to the project root directory and run:
    ```bash
    uv venv
    ```
    This will create a virtual environment named `.venv` in the project root.

3.  **Activate Virtual Environment:**
    ```bash
    source .venv/bin/activate  # On macOS/Linux
    # or
    .venv\\Scripts\\activate    # On Windows
    ```

4.  **Install Dependencies:**
    With the virtual environment activated, install project dependencies (including development dependencies) using:
    ```bash
    uv sync --all-extras # Or `uv pip install -e .[dev]` if using older uv conventions
    ```
    This command reads `pyproject.toml` and installs all specified packages.

## Code Style, Linting, and Type Checking

We use `ruff` for formatting and linting, and `ty` for type checking. These tools are managed via `uv tool` as defined in `pyproject.toml` and run via `pre-commit` hooks.

1.  **Formatting (`ruff format`):**
    Code formatting is enforced by `ruff format`. After activating your virtual environment (`source .venv/bin/activate`), you can run:
    ```bash
    ruff format .
    # OR, to be absolutely sure you're using the venv's ruff:
    # .venv/bin/python -m ruff format .
    ```

2.  **Linting (`ruff`):**
    Code linting is performed by `ruff`. After activating your virtual environment, you can run:
    ```bash
    ruff . --fix
    # OR, to be absolutely sure:
    # .venv/bin/python -m ruff . --fix
    ```

3.  **Type Checking:**
    Type checking setup has been deferred for now.

4.  **Pre-commit Hooks:**
    Formatting and linting checks are configured as pre-commit hooks. These hooks now explicitly call the tools from the `.venv/bin` directory. Ensure pre-commit is installed (`pip install pre-commit` or `uv pip install pre-commit`) and hooks are set up (`pre-commit install`). They will run automatically on each commit. You can run them manually via:
    ```bash
    pre-commit run --all-files
    ```

## Managing Dependencies with `uv`

-   **Adding a new dependency:**
    ```bash
    uv pip install <package-name>
    ```
    Then, manually add the package and its version to the appropriate section in `pyproject.toml` (`[project.dependencies]` or `[project.optional-dependencies.dev]`).

-   **Removing a dependency:**
    Manually remove the package from `pyproject.toml`.

-   **Updating dependencies:**
    Modify the version specifiers in `pyproject.toml` as needed.

-   After any changes to `pyproject.toml`, re-synchronize your environment:
    ```bash
    uv sync --all-extras
    ```

## Data Models & Processing Scripts

-   Core data structures are defined in `DATA_MODEL.md`. If you alter data structures, **update `DATA_MODEL.md`**.
-   Data processing scripts are in `scripts/`. If these are modified, consider if `assets/` data files need regeneration. Follow `README.md` for regeneration steps.

## Commits and Pull Requests

-   Write clear, concise commit messages.
-   Reference issues/features in commit messages or PR descriptions.

## General Guidelines

-   Write clear, maintainable, and well-documented code compatible with Python 3.13.
-   If unsure, ask for clarification.
-   Ensure all checks (linting, type checking, tests) pass before submitting.
---

*This `AGENTS.md` is based on the project's migration to `uv`, Python 3.13, `ruff`, and `ty`.*
