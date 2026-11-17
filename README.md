# kanban — CLI-first multi-agent kanban board

A single-file, stdlib-only Python CLI for running a kanban board that many
agents (or humans) can use **at the same time**, with an **immediate change
feed**. No server, no dependencies — state lives in one SQLite database in
WAL mode, so concurrent processes are safe and every mutation is visible to
watchers within ~200 ms.

## Install

```bash
chmod +x kanban          # it's already executable
./kanban init            # create ./.kanban/kanban.db
# optional: put it on PATH
ln -s "$PWD/kanban" ~/.local/bin/kanban
```

Requires Python 3.8+. Board location: `--db PATH`, else `$KANBAN_DB`, else
`./.kanban/kanban.db`. Actor name: `--actor NAME`, else `$KANBAN_ACTOR`,
else `$USER`. Every command also accepts `--json`.

## Lifecycle

```
todo ──(all parents done)──> ready ──(claim)──> doing ──> done
                                            └───────> blocked ──(unblock)──> ready
```

## Commands

| Command | What it does |
|---|---|
| `kanban init` | create the board database |
| `kanban add "title" [--body B] [--assignee A] [--priority N] [--label L]... [--parent ID]...` | create a card; starts `ready`, or `todo` if any parent isn't `done` |
| `kanban ls [--status S] [--assignee A] [--label L]` | list cards |
| `kanban board` | column view |
| `kanban show <id>` | card detail + parents/children + full event history |
| `kanban claim <id>` / `kanban claim --any [--assignee A] [--ttl SECONDS]` | atomically claim a `ready` card (two agents can never claim the same card) |
| `kanban release <id> [--force]` | release a claim back to `ready` |
| `kanban reclaim [id] [--force]` | release expired claims (default TTL 900 s) back to `ready` |
| `kanban complete <id> --summary "..."` | mark `done`; auto-promotes children whose parents are all done |
| `kanban block <id> --reason "..."` / `kanban unblock <id>` | park / revive a card |
| `kanban move <id> <status>` | set status directly (`todo ready doing done blocked archived`) |
| `kanban assign <id> <agent>` | reassign |
| `kanban edit <id> [--title T] [--body B] [--priority N] [--label L]...` | edit fields |
| `kanban link <parent> <child>` / `kanban unlink <parent> <child>` | dependency links; linking demotes a runnable child to `todo` until parents finish |
| `kanban comment <id> "text"` | add a note to the card's history |
| `kanban rm <id>` | archive |
| `kanban events [--task ID] [--limit N]` | dump the change feed |
| `kanban watch [--json] [--since N] [--interval S]` | **stream the change feed live** (Ctrl-C to stop) |
| `kanban dash` (aliases: `dashboard`, `live`) | **live-updating board view in the terminal** — columns re-render as events land, `doing` rows show `[worker 12m30s]` claim countdowns, bottom shows the event feed. Ctrl-C to stop. `--once` for a single snapshot (default when piped), `--follow` to stream frames when piped, `--interval`, `--feed N` |

## Multi-agent usage

Point every agent at the same board and give each a distinct actor name:

```bash
export KANBAN_DB=/shared/project/.kanban/kanban.db
kanban add "research costs" --assignee researcher --json | jq -r .id   # orchestrator
kanban claim --any --assignee researcher --actor researcher             # worker picks up work
kanban watch --json                                                     # anyone, live feed
kanban complete "$ID" --actor researcher --summary "..."
```

Concurrency is handled by SQLite WAL + atomic claim updates: parallel
`add`/`claim`/`complete` calls from many processes never lose events (the
`events` table is appended in the same transaction as each mutation).

## Watching the board live

Open a terminal and run:

```bash
kanban dash        # full-screen live board: columns + who is doing what + event feed
```

It re-renders every 0.5 s as agents claim, comment, block, and complete
cards — `doing` rows show the claiming worker and the time left on their
claim (e.g. `t_9d144eb5 P3 [dev 14m59s] build api`). `kanban dash --once`
prints a single snapshot (handy in scripts); `kanban watch --json` is the
machine-readable feed for piping into other agents.

## Agent skill

`.vibe/skills/kanban-cli/SKILL.md` is the orchestrator playbook for routing
work through this board (adapted from the `kanban-orchestrator` workflow):
decomposition patterns, parent-gating, anti-temptation rules, and stuck-card
recovery — all expressed in these CLI commands.

## Development

Single file: `kanban` (Python 3 stdlib only). Schema: `tasks`, `links`
(parent→child), `events` (append-only audit feed). Tests are exercised via
the shell; see the lifecycle commands above.
