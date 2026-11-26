# Development

## The CLI

Two files: `swrm` (a two-line shim for `./swrm` usage) and `swrm.py` (the real
CLI - Python 3 stdlib only). Schema: `tasks`, `links` (parent→child), `events`
(append-only audit feed), `label_colors`, `connector_state`. The version lives
in `__version__` in `swrm.py` (`swrm --version`).

## Releasing

1. Bump `__version__` in `swrm.py` and add a `CHANGELOG.md` section.
2. Tag `vX.Y.Z`; the `release` workflow runs the tests, builds sdist + wheel
   and publishes to PyPI via **trusted publishing** (no tokens; configure the
   `pypi` GitHub environment once).
3. Update `packaging/homebrew/swrm.rb` in the tap repo: new version + the
   sdist's `sha256` from the PyPI release page (the placeholder checksum
   refuses to install until you do).

## Brand assets

`assets/` holds the hive-cell brand set:

| File | Use |
|---|---|
| `logo.svg` | hive mark on dark tile (used in the README) |
| `logo-mark.svg` | mark only, transparent background |
| `logo-wordmark.svg` | mark + wordmark + tagline |
| `favicon.svg` / `favicon.ico` | favicons, 16–256 px |

## These docs

This site is built with [MkDocs](https://www.mkdocs.org/) + the
[Material theme](https://squidfunk.github.io/mkdocs-material/). Sources are the
Markdown files in `docs/`; config is `mkdocs.yml` at the repo root.

```bash
pip install -r docs/requirements.txt
python3 -m mkdocs serve        # live preview at http://127.0.0.1:8000
python3 -m mkdocs build        # writes static HTML to docs/site/
```

The built site in `docs/site/` is plain static HTML — serve it with anything:

```bash
python3 -m http.server -d docs/site 8000     # or nginx / GitHub Pages / etc.
```
