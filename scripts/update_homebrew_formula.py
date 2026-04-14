from __future__ import annotations

import argparse
from pathlib import Path
import re


def main() -> int:
    parser = argparse.ArgumentParser(description="Update Homebrew formula version/url/sha for ToonPrompt.")
    parser.add_argument("--formula", required=True, help="Path to Formula/toonprompt.rb")
    parser.add_argument("--version", required=True, help="Release version without leading v, e.g. 0.2.0")
    parser.add_argument("--sha256", required=True, help="SHA256 for source tarball")
    args = parser.parse_args()

    formula_path = Path(args.formula)
    text = formula_path.read_text()
    version = args.version
    text = re.sub(
        r'url "https://github\.com/kmrsandeep1998/ToonPrompt/archive/refs/tags/v[^"]+\.tar\.gz"',
        f'url "https://github.com/kmrsandeep1998/ToonPrompt/archive/refs/tags/v{version}.tar.gz"',
        text,
    )
    text = re.sub(r'sha256 "[^"]+"', f'sha256 "{args.sha256}"', text)
    formula_path.write_text(text)
    print(f"Updated {formula_path} to v{version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
