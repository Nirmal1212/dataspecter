# dataspecter

Config-driven synthetic data simulator: define entities, value ranges and probability distributions in YAML or JSON, then export realistic data as CSV, JSON, or a stream to an HTTP endpoint.

## How to work in this repo

The full development process is in [CONTRIBUTING.md](CONTRIBUTING.md). Read it before branching, committing, merging or releasing. The rules that matter most:

- **Spec first.** New capabilities and behaviour changes start as an OpenSpec proposal (`/opsx:propose`) that is reviewed before any code is written. Specs live in `openspec/specs/`, in-flight changes in `openspec/changes/`.
- **Git Flow.** `main` holds tagged releases only; `develop` is the integration branch. Never commit directly to either. Branch `feature/<change-name>` off `develop` for an OpenSpec change (`fix/`, `chore/`, `docs/` for small work without a spec), and merge back by squash.
- **One change, one branch, one PR.** The branch name matches the OpenSpec change name. Archive the change (`/opsx:archive`) on its branch before it merges.
- **Conventional Commits.** `type(scope): summary`. A `commit-msg` hook enforces it.
- **Changelog.** Every archived change adds an entry under `[Unreleased]` in `CHANGELOG.md`.
- **Releases.** `release/<X.Y.Z>` off `develop`, merged to `main` with `--no-ff`, tagged `vX.Y.Z`, then merged back into `develop`.
- **No AI attribution.** Do not add `Co-Authored-By` or "Generated with" lines to commits or pull requests.
- **Ask before anything outward-facing**: pushing, creating a remote repository, opening a PR, tagging a release.

## Project notes

**Stack:** Python 3.11+, packaged with hatchling in a `src/` layout. PyYAML is the only runtime dependency; everything else at runtime is standard library, and new runtime dependencies need a justification in the change's design. pytest and ruff are dev-only.

**Commands** (run from the repo root):

```bash
uv sync --extra dev        # create or update the environment
uv run pytest              # tests
uv run ruff check .        # lint
uv run ruff format .       # format
uv run dataspecter --help  # the CLI
```

**Layout:** package in `src/dataspecter/`, tests in `tests/`, example specs in `examples/`. The version lives in `src/dataspecter/_version.py`.
