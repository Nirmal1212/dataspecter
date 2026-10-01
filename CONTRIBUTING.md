# Development process

How work moves from idea to release in dataspecter. The same process applies to all my projects:

- **OpenSpec** decides *what* gets built (a reviewed proposal before any code).
- **Git Flow** decides *where* the work lives (which branch, and how it merges).
- **Conventional Commits** and **SemVer** record *what changed* (history, changelog, version).

## Branches

| Branch | Cut from | Merges into | Purpose |
|---|---|---|---|
| `main` | — | — | Released code only. Every commit on it is a tagged release. |
| `develop` | `main` | — | Integration branch. Default target for pull requests. |
| `feature/<change-name>` | `develop` | `develop`, squash | One OpenSpec change. |
| `fix/<name>`, `chore/<name>`, `docs/<name>` | `develop` | `develop`, squash | Small work that needs no spec. |
| `release/<X.Y.Z>` | `develop` | `main`, merge commit, then back into `develop` | Stabilise and ship a version. |
| `hotfix/<X.Y.Z>` | `main` | `main`, merge commit, then back into `develop` | Urgent fix to released code. |

- Nothing is committed directly to `main` or `develop`; they only receive merges.
- Work branches are short-lived and deleted after they merge.
- Work branches are squash-merged so `develop` carries one Conventional Commit per change. Release and hotfix branches use a merge commit (`--no-ff`) so the release stays visible in history.

## When a change needs a spec

Write an OpenSpec proposal when the work adds a capability, changes behaviour a user or caller can observe, breaks compatibility, or changes the architecture.

Skip the spec and use a `fix/`, `chore/` or `docs/` branch for bug fixes that restore already-specified behaviour, dependency bumps, refactors with no behaviour change, and documentation.

## Lifecycle of a change

One OpenSpec change = one `feature/` branch = one pull request.

1. **Branch.** Name the change in kebab-case starting with a verb (`add-`, `update-`, `remove-`, `fix-`), and use the same name for the branch.

   ```bash
   git switch develop
   git pull            # when a remote exists
   git switch -c feature/add-weighted-ranges
   ```

2. **Propose.** Run `/opsx:propose add-weighted-ranges` (use `/opsx:explore` first if the idea is still fuzzy). Review the proposal, design, spec deltas and tasks, then commit them before writing code:

   ```bash
   openspec validate add-weighted-ranges --strict
   git commit -m "docs(openspec): propose add-weighted-ranges"
   ```

3. **Implement.** Run `/opsx:apply` and work through `tasks.md`. Commit each task group as one Conventional Commit and tick the tasks off as they land. If the plan turns out to be wrong, update the proposal first (`/opsx:update`), then the code.

4. **Verify.** Tests and linters pass, and `openspec validate --strict` is clean.

5. **Archive.** Run `/opsx:archive` on the feature branch. This folds the spec deltas into `openspec/specs/`, so the specs on `develop` always describe the code on `develop`. Add an entry under `[Unreleased]` in `CHANGELOG.md`, then commit:

   ```bash
   git commit -m "docs(openspec): archive add-weighted-ranges"
   ```

6. **Merge.** Open a pull request into `develop` with a Conventional Commit title, and squash-merge it. Delete the branch.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org): `<type>(<scope>)!: <summary>`

- **type**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- **scope** (optional): the capability or area touched, e.g. `feat(generator): ...`
- **summary**: imperative mood, lower case, no trailing full stop, 72 characters or fewer
- **breaking change**: add `!` after the type or scope and a `BREAKING CHANGE:` footer explaining the migration

```
feat(generator): add weighted probability ranges
fix(export): quote CSV fields that contain commas
feat(config)!: rename `entities` key to `models`
```

The `commit-msg` hook in `.githooks/` rejects messages that do not follow this format. A fresh clone enables it with:

```bash
git config core.hooksPath .githooks
```

## Versioning and changelog

Versions follow [SemVer](https://semver.org). The commits since the last release decide the bump:

| Commits since last release | Bump | Before 1.0.0 |
|---|---|---|
| Any breaking change (`!` or `BREAKING CHANGE:`) | major | minor |
| At least one `feat` | minor | minor |
| Only `fix`, `perf` and the rest | patch | patch |

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com). Each change adds its entry under `[Unreleased]` when it is archived (step 5); a release moves those entries under the new version.

## Releasing

```bash
git switch develop
git switch -c release/0.2.0
```

On the release branch: bump the version wherever the project declares it, rename `[Unreleased]` in `CHANGELOG.md` to `[0.2.0] - YYYY-MM-DD` and add a fresh empty `[Unreleased]` above it, then commit as `chore(release): 0.2.0`. Only release fixes go on this branch; new features wait on `develop`.

```bash
git switch main
git merge --no-ff release/0.2.0 -m "chore(release): 0.2.0"
git tag -a v0.2.0 -m "v0.2.0"
git switch develop
git merge --no-ff main -m "chore(release): merge 0.2.0 back into develop"
git branch -d release/0.2.0
git push origin main develop --follow-tags   # when a remote exists
```

## Hotfixes

For a fix that cannot wait for the next release. The version is the next patch after the latest tag.

```bash
git switch main
git switch -c hotfix/0.2.1
```

Fix, add a `CHANGELOG.md` entry under a new `[0.2.1]` heading, bump the version, and commit. Then finish exactly like a release: merge into `main` with `--no-ff`, tag `v0.2.1`, merge `main` back into `develop`, delete the branch.

## Definition of done

- [ ] The change has an approved OpenSpec proposal, or is small enough not to need one
- [ ] Tests and linters pass
- [ ] `openspec validate --strict` is clean
- [ ] The change is archived and `openspec/specs/` is up to date
- [ ] `CHANGELOG.md` has an entry under `[Unreleased]`
- [ ] The pull request title is a Conventional Commit and targets `develop`
