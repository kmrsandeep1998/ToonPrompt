# Ecosystem Roadmap

ToonPrompt follows a monorepo-first model. All integration assets live in this repository and are versioned with core changes.

## Homebrew Tap

- Formula template: `packaging/homebrew/Formula/toonprompt.rb`
- Release formula artifact workflow: `.github/workflows/homebrew-tap.yml`
- Optional: mirror formula to a dedicated tap repo if you later want independent distribution.

## VS Code Extension

- Extension project: `integrations/vscode/toonprompt-vscode`
- Initial command implemented: `ToonPrompt: Optimize Selection`

## GitHub Action

- In-repo composite action: `.github/actions/toonprompt-check/action.yml`
- Standalone action scaffold: `integrations/github-action/toonprompt-check`
- Purpose: fail CI when prompt files exceed token budgets.
