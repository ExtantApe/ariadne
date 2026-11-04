#!/bin/bash
# Blocks publishing personal info. Private terms live OUTSIDE the repo, one per line:
#   ~/.theseus-private-terms   (e.g. your name, employer, family names, business names, phone numbers)
# Usage: scripts/leak-check.sh [--staged]   (exit 1 = leak found)
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TERMS="${THESEUS_PRIVATE_TERMS:-$HOME/.theseus-private-terms}"
cd "$ROOT"
if [[ "${1:-}" == "--staged" ]]; then
  FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)
else
  FILES=$(git ls-files 2>/dev/null || find . -type f -not -path './.git/*')
  [[ -n "$FILES" ]] || FILES=$(find . -type f -not -path './.git/*')
fi
FILES=$(echo "$FILES" | grep -v -E '(^|/)scripts/leak-(check\.sh|allow\.txt)$' || true)
ALLOW="$ROOT/scripts/leak-allow.txt"
allowed() {   # drop hit lines that contain an allow-listed public phrase
  if [[ -f "$ALLOW" ]]; then grep -v -F -f <(grep -v -E '^\s*(#|$)' "$ALLOW") || true; else cat; fi
}
[[ -n "$FILES" ]] || { echo "leak-check: nothing to scan"; exit 0; }
fail=0
if [[ -f "$TERMS" ]]; then
  while IFS= read -r term; do
    [[ -z "$term" || "$term" == \#* ]] && continue
    hits=$(echo "$FILES" | xargs grep -n -i -w -F -- "$term" 2>/dev/null | allowed || true)
    if [[ -n "$hits" ]]; then echo "❌ private term found: '$term'"; echo "$hits" | head -5; fail=1; fi
  done < "$TERMS"
else
  echo "⚠️  No private terms file at $TERMS. Create it (one term per line) so the check can protect you."
fi
# Phone numbers (US-style) and email addresses that aren't obvious placeholders
phones=$(echo "$FILES" | xargs grep -n -E '\(?\b[2-9][0-9]{2}\)?[ .-][0-9]{3}[ .-][0-9]{4}\b' 2>/dev/null | grep -v -E '555[ .-]?[0-9]{4}' || true)
[[ -n "$phones" ]] && { echo "❌ possible phone numbers:"; echo "$phones" | head -5; fail=1; }
emails=$(echo "$FILES" | xargs grep -n -o -E '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' 2>/dev/null \
  | grep -v -E '@(example\.(com|org|net)|slack\.com|slack-mail\.com|anthropic\.com)' | allowed || true)
[[ -n "$emails" ]] && { echo "❌ possible real email addresses:"; echo "$emails" | head -5; fail=1; }
[[ $fail == 0 ]] && echo "✅ leak-check passed ($(echo "$FILES" | wc -l | tr -d ' ') files)"
exit $fail
