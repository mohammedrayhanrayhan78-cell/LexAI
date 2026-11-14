#!/usr/bin/env bash
# Fail if innerHTML is assigned anywhere in frontend JS except:
#  - DOMPurify-sanitized assignments
#  - constant single-quoted string literals (no interpolation)
set -u
bad=$(git grep -n 'innerHTML' -- 'frontend/js/*.js' ':!frontend/js/vendor/*' \
  | grep -E 'innerHTML\s*[+]?=' \
  | grep -v 'DOMPurify\.sanitize(' \
  | grep -vE "innerHTML\s*=\s*'[^']*';" || true)
if [ -n "$bad" ]; then
  echo "ERROR: unsanitized innerHTML assignment(s) found:"
  echo "$bad"
  echo "Use textContent/createElement, or wrap HTML in DOMPurify.sanitize()."
  exit 1
fi
echo "innerHTML check passed."
