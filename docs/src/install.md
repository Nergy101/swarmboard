# Install

## pipx (recommended)

```bash
pipx install swarmboard    # command: swrm
swrm init                  # create ./.kanban/kanban.db

The first `swrm init` prints a one-time welcome guide with the everyday
commands; `swrm help` shows it again any time.
```

## Homebrew (needs the tap once)

```bash
brew tap Nergy101/swrm
brew install swrm
```

## From source (zero install)

```bash
git clone https://github.com/Nergy101/swarmboard.git
cd swarmboard
chmod +x swrm                   # already executable
ln -s "$PWD/swrm" ~/.local/bin/swrm   # optional: put it on PATH
swrm init                       # create ./.kanban/kanban.db

The first `swrm init` prints a one-time welcome guide with the everyday
commands; `swrm help` shows it again any time.
```

`./swrm` is a two-line shim that runs the CLI next to it (`swrm.py`); a
pipx/Homebrew install provides the exact same `swrm` command through the
entry point in `pyproject.toml`.

## Keeping swrm up to date

```bash
swrm update            # check PyPI and self-update
swrm update --dry-run  # show what would happen
swrm update --yes      # no prompt
```

`swrm update` detects how swrm was installed (pipx, Homebrew, git checkout
or a loose script) and does the right thing: `pipx upgrade swarmboard`,
`brew upgrade swrm`, `git pull --ff-only`, or a clear instruction.

Requires **Python 3.9+**. Nothing else — `swrm` is a single module using only
the standard library.

## Configuration

Everything is configurable via flags or environment variables:

| Setting | Flag | Env var | Default |
|---|---|---|---|
| Board location | `--db PATH` | `$KANBAN_DB` | `./.kanban/kanban.db` |
| Actor name | `--actor NAME` | `$KANBAN_ACTOR` | `$USER` |
| Remote leader | `--url URL` | `$KANBAN_URL` | _(local mode)_ |
| Leader passkey | `--passkey SECRET` | `$KANBAN_PASSKEY` | _(none)_ |

Every command also accepts `--json` for machine-readable output.

!!! tip "Remote mode"
    Set `$KANBAN_URL` (or pass `--url`) and every command runs against the
    leader over HTTP instead of a local database — see
    [Leader-follower mode](leader-follower.md).
