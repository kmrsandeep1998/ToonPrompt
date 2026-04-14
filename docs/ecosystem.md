# Ecosystem Roadmap

This repository now includes scaffolding for ecosystem deliverables that can be split into dedicated repos.

## Homebrew Tap

- Formula template: `packaging/homebrew/Formula/toonprompt.rb`
- Auto-bump workflow: `.github/workflows/homebrew-tap.yml`
- Required secret: `HOMEBREW_TAP_TOKEN` with write access to `kmrsandeep1998/homebrew-toonprompt`

## VS Code Extension

- Starter project: `integrations/vscode/toonprompt-vscode`
- Intended destination repo: `kmrsandeep1998/toonprompt-vscode`
- Initial command implemented: `ToonPrompt: Optimize Selection`

## GitHub Action

- Composite action scaffold: `.github/actions/toonprompt-check/action.yml`
- Purpose: fail CI when prompt files exceed token budgets.
