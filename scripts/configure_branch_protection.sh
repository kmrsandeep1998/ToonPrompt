#!/usr/bin/env bash
set -euo pipefail

REPO="${1:-kmrsandeep1998/ToonPrompt}"

echo "Configuring branch protection for ${REPO} main..."

tmp_json="$(mktemp)"
cat > "${tmp_json}" <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "test (ubuntu-latest, 3.12)",
      "lint",
      "property-tests"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_linear_history": true
}
JSON

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/${REPO}/branches/main/protection" \
  --input "${tmp_json}" >/dev/null

rm -f "${tmp_json}"

echo "Branch protection updated."
