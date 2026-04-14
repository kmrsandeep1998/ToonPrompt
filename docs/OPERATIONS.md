# Operations Runbook

This runbook covers the non-code operational items required for production usage.

## 1) Release Tag + PyPI Publish

1. Ensure CI is green on `main`.
2. Create a new version tag:
   ```bash
   git checkout main
   git pull --ff-only origin main
   git tag v0.1.0b1
   git push origin v0.1.0b1
   ```
3. Confirm `Release build` workflow succeeds (build, `twine check`, SBOM, PyPI publish).

## 2) Required GitHub Secrets

No external-repo secret is required for core monorepo workflows.

Optional:

- `VSCODE_MARKETPLACE_TOKEN` (only if publishing extension externally)

## 3) GitHub Pages for Docs

1. In repo settings, set **Pages source** to GitHub Actions.
2. Ensure `.github/workflows/docs.yml` succeeds on `main`.
3. Verify published URL:
   - `https://kmrsandeep1998.github.io/ToonPrompt/`

## 4) Branch Protection

Recommended protection for `main`:

- Require pull request before merging
- Require status checks:
  - CI / test (all matrix jobs)
  - CI / lint
- Require branches to be up to date
- Require conversation resolution
- Restrict force pushes and deletions

## 5) Monorepo Integration Assets

All integration assets are kept in this repository:

- `packaging/homebrew/`
- `integrations/vscode/toonprompt-vscode/`
- `integrations/github-action/toonprompt-check/`

You can later mirror any of these into dedicated repositories without changing core ToonPrompt code.
