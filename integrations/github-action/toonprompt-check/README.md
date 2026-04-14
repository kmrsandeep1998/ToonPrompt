# toonprompt-check (Standalone Action Scaffold)

This folder is a portable scaffold for publishing a standalone GitHub Action.

## Suggested target repository

- `kmrsandeep1998/toonprompt-check-action`

## Usage

```yaml
jobs:
  prompt-budget:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: kmrsandeep1998/toonprompt-check-action@v1
        with:
          max-tokens: "4096"
          pattern: ".prompt"
```

## Publishing notes

1. Copy this directory into its own repository root.
2. Add tags (`v1`, `v1.0.0`) after release.
3. Add marketplace metadata in the target repo README and topics.
