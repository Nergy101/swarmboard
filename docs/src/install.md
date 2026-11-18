# Install

```bash
git clone https://github.com/Nergy101/swarmboard.git
cd swarmboard
chmod +x swrm                   # already executable
ln -s "$PWD/swrm" ~/.local/bin/swrm   # optional: put it on PATH
swrm init                       # create ./.kanban/kanban.db
```

Requires **Python 3.8+**. Nothing else — `swrm` is a single file using only
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
