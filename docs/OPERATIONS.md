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

Set these in repository settings:

- `HOMEBREW_TAP_TOKEN`: PAT with write access to `kmrsandeep1998/homebrew-toonprompt`

Optional if using external repos:

- `VSCODE_MARKETPLACE_TOKEN`

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

## 5) External Repositories

These are separate deployment units:

- Homebrew tap repo: `kmrsandeep1998/homebrew-toonprompt`
- VS Code extension repo: `kmrsandeep1998/toonprompt-vscode`
- Optional standalone GitHub Action repo for token budget checks

This repository includes scaffolding under:

- `packaging/homebrew/`
- `integrations/vscode/toonprompt-vscode/`
- `integrations/github-action/toonprompt-check/`
