# Contributing

This document outlines the development workflow, quality checks, continuous integration requirements, and testing standards for contributing to Pipecat Voice Studio.

## Prerequisites

Development requires the following toolchains and environments defined in [pyproject.toml](file:///D:/AI/Github/pipecat-voice-studio/pyproject.toml) and [.github/workflows/quality.yml](file:///D:/AI/Github/pipecat-voice-studio/.github/workflows/quality.yml):

- Supported operating systems:
  - Native 64-bit Windows AMD64 (`sys_platform == 'win32' and platform_machine == 'AMD64'`).
  - Native 64-bit Linux x86_64 (`sys_platform == 'linux' and platform_machine == 'x86_64'`) with glibc 2.34 or newer.
  - macOS, Apple Silicon, and ARM64 Linux are not supported due to PyTorch CUDA wheel constraints.
- Python: `>=3.13,<3.15` (CI and launchers use `3.14.7` with fallback to `3.13.13`).
- Package manager: [uv](https://docs.astral.sh/uv/).
- Node.js: Node.js 24 and npm (for compiling the React frontend component).

## Local development setup

1. Clone the repository and navigate to the project root:
   ```bash
   git clone <repo-url>
   cd pipecat-voice-studio
   ```

2. Synchronize Python virtual environment and locked dependencies:
   ```bash
   uv sync --frozen
   ```

3. Create the local configuration file:
   - On Windows (PowerShell):
     ```powershell
     Copy-Item .env.example .env
     ```
   - On Linux (Bash):
     ```bash
     cp .env.example .env
     ```
   Populate `OPENAI_API_KEY` in `.env`.

4. Install frontend dependencies and compile the client bundle:
   ```bash
   cd src/pipecat_voice_studio/ui/frontend
   npm ci
   npm run build
   cd ../../../..
   ```

## Quality gates

Every pull request must pass the automated checks defined in [.github/workflows/quality.yml](file:///D:/AI/Github/pipecat-voice-studio/.github/workflows/quality.yml). Run these commands locally before submitting changes:

### 1. Lockfile check

Ensure [uv.lock](file:///D:/AI/Github/pipecat-voice-studio/uv.lock) is consistent with [pyproject.toml](file:///D:/AI/Github/pipecat-voice-studio/pyproject.toml):
```bash
uv lock --check
```

### 2. Linting

Run Ruff lint checks across the entire codebase:
```bash
uv run ruff check .
```

To automatically format or fix safe lint issues:
```bash
uv run ruff check --fix .
uv run ruff format .
```

### 3. Static type checking

Run the `ty` static type checker:
```bash
uv run ty check
```

### 4. Automated unit tests and coverage

Run the test suite using pytest:
```bash
uv run pytest
```
As configured in `[tool.pytest.ini_options]`, pytest enforces a minimum test coverage threshold of 80% (`--cov-fail-under=80`).

### 5. Frontend typecheck and build

Validate TypeScript types and build production bundles for the custom Streamlit component:
```bash
cd src/pipecat_voice_studio/ui/frontend
npm run typecheck
npm run build
cd ../../../..
```

### 6. Launcher dry-run validation

Validate launcher scripts without launching persistent servers:
- On Windows (PowerShell):
  ```powershell
  .\launch.ps1 -SetupOnly
  ```
- On Linux (Bash):
  ```bash
  bash -n launch.sh
  ./launch.sh --setup-only
  ```

### 7. Package build validation

Ensure the Python package builds cleanly via uv:
```bash
uv build
```

## Continuous integration workflows

### Quality workflow (`.github/workflows/quality.yml`)

The Quality workflow executes on:
- Pushes to branch `master`
- Pull requests targeting `master`
- Manual workflow dispatch (`workflow_dispatch`)

The job matrix runs in parallel across `windows-latest` and `ubuntu-latest`. It validates:
- Python dependency resolution with `uv sync --frozen` and `uv lock --check`
- Ruff linting and `ty` type checking
- Pytest test execution and coverage thresholds
- Frontend npm dependencies, typecheck, and Vite production build
- Platform launcher setup-only executions (`launch.ps1 -SetupOnly` and `launch.sh --setup-only`)
- Wheel and source distribution package build (`uv build`)

### Live evaluations workflow (`.github/workflows/live-evaluations.yml`)

Live evaluations run real speech conversations against model APIs. This workflow is manual only:
- Triggered via `workflow_dispatch`
- Target environment: `windows-latest`
- Environment secret required: `OPENAI_API_KEY`
- Parameter `scenario`: selects an allowlisted scenario (`all`, `happy-path`, `unavailable-slot`, `policy-denial`, `interruption`, `synthetic-audio-smoke`)
- Execution command:
  ```bash
  uv run pytest -m live_eval tests/test_live_evaluations.py --no-cov -q
  ```
- Uploads `artifacts/live-evaluations.json` upon completion.
