#!/bin/bash
# Theseus and Ariadne share a design system. These files must stay identical in both repos, and brand/shared.sha256 is how each repo knows that
# without seeing the other. After changing one: copy it to the other repo, then run this with --update in both, and commit both.
set -euo pipefail
cd "$(dirname "$0")/.."
FILES="MANIFESTO.md apps/desktop/src/ui/Icon.tsx apps/desktop/src/ui/family.css apps/desktop/src/ui/useDrag.ts brand/README.md"
if [[ "${1:-}" == "--update" ]]; then shasum -a 256 $FILES > brand/shared.sha256; echo "brand/shared.sha256 updated"; exit 0; fi
shasum -a 256 -c brand/shared.sha256 --quiet || { echo "A file shared with the other app changed. See the top of scripts/check-shared.sh."; exit 1; }
