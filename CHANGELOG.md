# Changelog

All notable changes to swarmboard are documented here (Keep a Changelog style).
The version lives in one place: `__version__` in `swrm.py`; `pyproject.toml`
reads it dynamically and `swrm --version` prints it.

## [Unreleased]

Planned first tagged release: `v0.1.0`.

### Added since the first PyPI-compatible packaging

- `NER-328` card labels: per-board label colors, repeatable `--label` filters
  on `ls` / `board` / `watch` / `dash`, and `swrm label` management commands.
- `NER-330` multi-board: board registry (`swrm boards` / `swrm switch`),
  `-b/--board` selection next to `--db`.
- `NER-331` connectors: two-way Linear sync (`swrm connector add|auth|sync|
  pause|resume|status`) with cursors, last-write-wins conflict policy and
  tokens kept out of the board database.
- `NER-329` distribution: `pipx install swarmboard`, a Homebrew formula
  (`packaging/homebrew/swrm.rb`) and `swrm update` self-update against the
  PyPI JSON API.
- Onboarding: a one-time welcome guide on `swrm init` and the first
  interactive `swrm dash`, and `swrm help` to show it any time.

### Release steps

1. Bump `__version__` in `swrm.py`.
2. Add a section to this file.
3. Commit, then tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. The `release` workflow builds an sdist/wheel and publishes to PyPI via
   [trusted publishing](https://docs.pypi.org/trusted-publishers/) - no tokens.
5. Update `packaging/homebrew/swrm.rb`: fill in the new `version` and the
   sdist's `sha256` (available on the PyPI release page), then push the tap.

The `pypi` GitHub environment needs trusted publishing configured once:
project `swarmboard`, workflow `release.yml`, from this repository.
