# Slide previews

Push slide changes to `slides-preview` to deploy a shared review version. GitHub Actions uploads it to Cloudflare Pages with `--branch slides-preview`; `main` remains the production branch. Each branch has its own workflow concurrency group.

- Production: `https://zhang-etal-biohack.pages.dev/<prefix>/talks/biohack/`
- Preview: `https://slides-preview.zhang-etal-biohack.pages.dev/<prefix>/talks/biohack/`
- Prototype: `https://slides-preview.zhang-etal-biohack.pages.dev/<prefix>/talks/process-prototype/`

`<prefix>` is the existing value in `slides/.pages-prefix`. Both environments keep the same unlisted path and noindex headers. These are unlisted links, not authentication.

Run `check_deck.py` before pushing. The preview branch is shared: fetch first and preserve others' changes; do not force-push. Preview publication does not merge changes into main. After review, merge only the intended changes.

Manual deployments must specify `main` or `slides-preview` when the current Git branch has another name:

```
slides/tools/deploy_unlisted.sh zhang-etal-biohack slides-preview
```

The workflow also supports manual dispatch for either named branch. Other branches are rejected by the deployment script to prevent accidental production publication.
