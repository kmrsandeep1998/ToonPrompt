from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def main() -> int:
    checks = [
        _check_required_files(),
        _check_workflows(),
        _check_pyproject_version(),
        _check_git_clean(),
        _check_optional_envs(),
    ]
    failed = [c for c in checks if not c.ok]
    for c in checks:
        status = "OK" if c.ok else "FAIL"
        print(f"[{status}] {c.name}: {c.detail}")
    if failed:
        print(f"\nRelease readiness failed: {len(failed)} check(s) failed.")
        return 1
    print("\nRelease readiness checks passed.")
    return 0


def _check_required_files() -> CheckResult:
    required = [
        ROOT / ".github" / "workflows" / "release.yml",
        ROOT / ".github" / "workflows" / "ci.yml",
        ROOT / "pyproject.toml",
        ROOT / "CHANGELOG.md",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        return CheckResult("required-files", False, f"missing: {', '.join(missing)}")
    return CheckResult("required-files", True, "all required files present")


def _check_workflows() -> CheckResult:
    workflows = [
        "release.yml",
        "ci.yml",
        "docs.yml",
        "docker.yml",
    ]
    path = ROOT / ".github" / "workflows"
    missing = [name for name in workflows if not (path / name).exists()]
    if missing:
        return CheckResult("workflows", False, f"missing: {', '.join(missing)}")
    return CheckResult("workflows", True, "core workflows present")


def _check_pyproject_version() -> CheckResult:
    path = ROOT / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    marker = 'version = "'
    if marker not in text:
        return CheckResult("pyproject-version", False, "version key not found")
    start = text.index(marker) + len(marker)
    end = text.index('"', start)
    version = text[start:end]
    return CheckResult("pyproject-version", True, f"version={version}")


def _check_git_clean() -> CheckResult:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return CheckResult("git-clean", False, proc.stderr.strip() or "git status failed")
    if proc.stdout.strip():
        return CheckResult("git-clean", False, "working tree is dirty")
    return CheckResult("git-clean", True, "working tree is clean")


def _check_optional_envs() -> CheckResult:
    optional = ["HOMEBREW_TAP_TOKEN"]
    present = [name for name in optional if os.environ.get(name)]
    return CheckResult("optional-secrets", True, f"present: {present or 'none'}")


if __name__ == "__main__":
    raise SystemExit(main())
