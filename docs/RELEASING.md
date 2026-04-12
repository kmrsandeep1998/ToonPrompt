# Releasing

This project is shipped as a public alpha. Releases should stay small and traceable.

## Before tagging

1. Update the version in `pyproject.toml` and `src/toonprompt/__init__.py`.
2. Add a short entry to `CHANGELOG.md`.
3. Run the test suite.
4. Build distributions with `python -m build`.
5. Review the generated wheel and sdist contents if the packaging surface changed.

## Tagging convention

- Use annotated tags that match the version, such as `v0.1.0a1`.
- Keep tag messages short and descriptive.

## Suggested release flow

```bash
python -m build
git tag -a v0.1.0a1 -m "Release v0.1.0a1"
git push origin v0.1.0a1
```

## Post-release

- Verify the published artifact metadata.
- Update the changelog with the release date if it was not included in the draft entry.
- Keep the next version bump on the main branch explicit so alpha history remains readable.
