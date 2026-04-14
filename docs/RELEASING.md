# Releasing

This project is shipped as a public alpha. Releases should stay small and traceable.

## Trusted publishing setup

PyPI publishing is configured through GitHub Actions trusted publishing instead of a long-lived API token.

Before the first release from a new environment, verify the PyPI project has a trusted publisher entry for:

- GitHub repository: `kmrsandeep1998/ToonPrompt`
- workflow: `.github/workflows/release.yml`
- trigger: tag pushes that match `v*`

The release workflow must keep `permissions.id-token: write` so the publish action can request an OIDC token from GitHub. No PyPI password or API token should be stored in the repository.

## Before tagging

1. Update the version in `pyproject.toml` and `src/toonprompt/__init__.py`.
2. Add a short entry to `CHANGELOG.md`.
3. Run the test suite.
4. Build distributions with `python -m build`.
5. Run `twine check dist/*` on the built artifacts.
6. Review the generated wheel and sdist contents if the packaging surface changed.

## Tagging convention

- Use annotated tags that match the version, such as `v0.1.0a2`.
- Keep tag messages short and descriptive.

## Suggested release flow

```bash
python -m build
twine check dist/*
git tag -a v0.1.0a2 -m "Release v0.1.0a2"
git push origin v0.1.0a2
```

When the tag push triggers GitHub Actions, the release workflow builds the artifacts, validates them with `twine check`, uploads them as workflow artifacts, and publishes to PyPI through trusted publishing. A manual `workflow_dispatch` run is build-only and does not publish.

## Post-release

- Verify the published artifact metadata.
- Update the changelog with the release date if it was not included in the draft entry.
- Keep the next version bump on the main branch explicit so alpha history remains readable.
