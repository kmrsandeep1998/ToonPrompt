# Changelog

All notable changes to this project will be documented in this file.

The format is intentionally simple while the project is in public alpha.

## [Unreleased]

- Repository scaffolding and public release docs.
- Alpha packaging metadata and CI workflows.

## [0.1.0a2] - 2026-04-13

- Drafted trusted publishing release flow for GitHub Actions and added `twine check` to the publish path.
- Documented PyPI trusted publishing setup and the tag-driven release checklist.
- Refreshed the compatibility notes and bumped package metadata for the `0.1.0a2` release cut.
- Introduced a strategy-based token estimator architecture with optional `tiktoken` backend and heuristic fallback.
- Added local telemetry opt-in with `toon metrics` summary and non-blocking metrics/logging behavior.
- Expanded compatibility and regression coverage with new matrix validation tests and additional golden fixtures.

## [0.1.0a1] - 2026-04-12

- First public alpha package metadata.
- Initial CLI wrapper, prompt transformation pipeline, and test suite.
