#!/usr/bin/env bash
# Upload the decks to Cloudflare Pages at an unlisted address: the whole site (tools/build_site.sh) sits under
# a long random path, the bare domain is a plain "Not found", and search engines are told not to index it.
# Anyone with the link can view it; nobody can find it without the link. Never use the template's project
# here: its production branch is the public site.
#
#   tools/deploy_unlisted.sh <project>      prints https://<project>.pages.dev/<prefix>/talks/<talk>/
#
# The prefix is made on the first run and kept in .pages-prefix (git-ignored), so redeploys keep the same
# link; delete that file for a new one. Needs wrangler, logged in (wrangler login) or CLOUDFLARE_API_TOKEN set.
set -euo pipefail

project=${1:?usage: tools/deploy_unlisted.sh <pages project>}
repo=$(cd "$(dirname "$0")/.." && pwd)
prefix_file="$repo/.pages-prefix"
[ -s "$prefix_file" ] || python3 -c 'import secrets; print(secrets.token_hex(24))' > "$prefix_file"
prefix=$(cat "$prefix_file")

site=$(mktemp -d)
trap 'rm -rf "$site"' EXIT
"$repo/tools/build_site.sh" "$site/$prefix"
printf '<!doctype html><meta charset="utf-8"><title>Not found</title><p>Not found.</p>\n' > "$site/404.html"
printf '/*\n  X-Robots-Tag: noindex, nofollow\n' > "$site/_headers"

# a new project the first time (an existing one just answers that it exists)
wrangler pages project create "$project" --production-branch main >/dev/null 2>&1 || true
wrangler pages deploy "$site" --project-name "$project" --branch main --commit-dirty=true

echo
for talk in "$repo"/talks/*/; do
  echo "https://$project.pages.dev/$prefix/talks/$(basename "$talk")/"
done
