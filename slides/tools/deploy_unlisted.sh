#!/usr/bin/env bash
# Publish the current deck at the main domain and keep the original long URLs working.
# Search engines are told not to index the site; the short URL is publicly accessible.
# Usage: tools/deploy_unlisted.sh <project> [main|slides-preview]
# The committed .pages-prefix preserves legacy bookmarks.
set -euo pipefail

project=${1:?usage: tools/deploy_unlisted.sh <pages project> [main|slides-preview]}
branch=${2:-$(git rev-parse --abbrev-ref HEAD)}
case "$branch" in
  main|slides-preview) ;;
  *) echo "Choose an explicit deployment branch: main or slides-preview" >&2; exit 1 ;;
esac
repo=$(cd "$(dirname "$0")/.." && pwd)
prefix_file="$repo/.pages-prefix"
[ -s "$prefix_file" ] || python3 -c 'import secrets; print(secrets.token_hex(24))' > "$prefix_file"
prefix=$(cat "$prefix_file")

site=$(mktemp -d)
trap 'rm -rf "$site"' EXIT
"$repo/tools/build_site.sh" "$site"
"$repo/tools/build_site.sh" "$site/$prefix"
printf '<!doctype html><meta charset="utf-8"><title>Not found</title><p>Not found.</p>\n' > "$site/404.html"
printf '/*\n  X-Robots-Tag: noindex, nofollow\n' > "$site/_headers"

# a new project the first time (an existing one just answers that it exists)
wrangler pages project create "$project" --production-branch main >/dev/null 2>&1 || true
wrangler pages deploy "$site" --project-name "$project" --branch "$branch" --commit-dirty=true

host="$project.pages.dev"
[ "$branch" = main ] || host="$branch.$host"
echo
echo "Main deck: https://$host/"
for talk in "$repo"/talks/*/; do
  echo "https://$host/$prefix/talks/$(basename "$talk")/"
done
