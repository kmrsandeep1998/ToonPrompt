#!/usr/bin/env bash
set -euo pipefail

REPO="${1:-kmrsandeep1998/ToonPrompt}"

echo "Configuring branch protection for ${REPO} main..."

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/${REPO}/branches/main/protection" \
  -f required_status_checks.strict=true \
  -F required_status_checks.contexts[]="test (ubuntu-latest, 3.12)" \
  -F required_status_checks.contexts[]="lint" \
  -F required_status_checks.contexts[]="property-tests" \
  -f enforce_admins=true \
  -f required_pull_request_reviews.dismiss_stale_reviews=true \
  -f required_pull_request_reviews.required_approving_review_count=1 \
  -f restrictions=

echo "Branch protection updated."
