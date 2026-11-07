# What we test next

**Closing the Loop Between Knowledge and Discovery**: Team Zhang et al., Nucleate Pittsburgh BioHack 2026.

## Slides

**Live deck:** https://zhang-etal-biohack.pages.dev/075d295f820d3892ac1d1010c3ffdc8f31a597f041dc3d2d/talks/biohack/

The link is unlisted: anyone who has it can view the deck, but it is not linked from anywhere or indexed by
search engines, so share it only with people who should see it. The deck is in `slides/talks/biohack/`, built on
[protein-design-interactive-slides](https://github.com/ramithuh/protein-design-interactive-slides) (see
`slides/README.md` and `slides/AGENTS.md`).

- **Present locally:** `cd slides && python -m http.server 8000`, then open http://localhost:8000/talks/biohack/
  (or open `slides/talks/biohack/index.html` straight from disk).
- **Check every slide:** `python slides/tools/check_deck.py slides/talks/biohack` (needs Playwright).
- **Deploy:** every push to `main` that touches `slides/` redeploys the link above
  (`.github/workflows/deploy-slides.yml`; needs the `CLOUDFLARE_API_TOKEN` repository secret). By hand:
  `slides/tools/deploy_unlisted.sh zhang-etal-biohack` (needs `wrangler login`). Both keep the same link because
  its random part is committed in `slides/.pages-prefix`.
