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

<!-- Tech stack, commands to build/test/lint, and architecture notes go here as they are decided. -->
