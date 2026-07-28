#!/usr/bin/env bash
# Render the competency map from its canonical markdown source
# (curriculum/*.md) into distribution artifacts (dist/).
#
# The docx is a BUILD PRODUCT now, not the source. Edit curriculum/,
# run scripts/check_map_refs.py, then this script.
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p dist

# v0.26 section order: front matter, domains 1-14 (original),
# assessment design principles, new domains 15-18, version history.
# Domain numbers are stable IDs (R1); reading order is set by this
# manifest, not by the number. New domains append at the end.
ORDER=(
  00-front-matter.md
  01-scripting-automation.md
  02-identity-hybrid-iam.md
  03-networking-fundamentals.md
  04-certificate-pki-management.md
  05-storage-architecture.md
  06-compute-architecture.md
  07-cloud-primitives-and-abstraction.md
  08-security-reasoning.md
  09-change-management-discipline.md
  10-backup-recovery-resilience.md
  11-log-reading-diagnosis.md
  12-minimum-viable-linux-administration.md
  assessment-design-principles.md
  13-frameworks-as-tools-synthesis.md
  14-theory-of-mind.md
  15-directing-ai-agents.md
  16-observability-and-alert-design.md
  17-minimum-viable-devops.md
  18-minimum-viable-database-administration.md
  version-history.md
)

python3 scripts/check_map_refs.py

combined=$(mktemp)
trap 'rm -f "$combined"' EXIT
for f in "${ORDER[@]}"; do
  # strip yaml front matter blocks; keep everything else
  awk 'BEGIN{fm=0; n=0} /^---$/{n++; if(n<=2){fm=(n==1); next}} !fm||n>=2' \
    "curriculum/$f" >> "$combined"
  printf '\n\n' >> "$combined"
done

pandoc -f gfm -t docx --wrap=none \
  -o dist/sysadmin_competency_map.docx "$combined"
pandoc -f gfm -t html --standalone --metadata \
  title="Modern Systems Administration — Competency Map" \
  -o dist/sysadmin_competency_map.html "$combined"
wc -c dist/sysadmin_competency_map.docx dist/sysadmin_competency_map.html
echo "rendered from $(ls curriculum/*.md | wc -l) source files"
