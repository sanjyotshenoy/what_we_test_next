#!/usr/bin/env bash
# Assemble the published site in one folder: the front page, every talk, and what they load (web/, vendor/).
# Also publish the explicitly selected OT-2 demonstration video and thumbnail.
#
#   tools/build_site.sh [out]        default out: site/ in the repo
#
# Cloudflare Pages runs this on every push to main (build command "bash tools/build_site.sh", output "site");
# tools/deploy_pages.sh uses it for a manual upload.
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
out=$(realpath -m "${1:-$repo/site}")
rm -rf "$out"
mkdir -p "$out"
cp "$repo/index.html" "$out/"
# -L: copy what symlinks point to, so a talk can link in a folder kept elsewhere (talks/biohack/demo -> /demo)
cp -rL "$repo/web" "$repo/vendor" "$repo/talks" "$out/"
# Public demonstration assets; select files explicitly rather than publishing the protocol folder.
mkdir -p "$out/media"
cp "$repo/../Opentrons/media/ot2-run-demo.mp4" "$repo/../Opentrons/media/ot2-run-demo.jpg" "$out/media/"
# the checker's pictures (talks/*/check/), if any are lying around locally
find "$out/talks" -mindepth 2 -maxdepth 2 -type d -name check -exec rm -rf {} +
echo "site: $(find "$out" -type f | wc -l) files, $(du -sh "$out" | cut -f1) in $out"
