# Commands

| Command | What it does |
|---|---|
| `swrm init` | create the board database |
| `swrm add "title" [--body B] [--assignee A] [--priority N] [--label L]... [--parent ID]...` | create a card; starts `ready`, or `todo` if any parent isn't `done` |
| `swrm ls [--status S] [--assignee A] [--label L]` | list cards |
| `swrm board` | static column view |
| `swrm dash` (aliases `dashboard`, `live`) | **live-updating board view** — `--once`, `--follow`, `--interval`, `--feed N` |
| `swrm show <id>` | card detail + parents/children + full event history |
| `swrm claim <id>` / `swrm claim --any [--assignee A] [--ttl SECONDS]` | atomically claim a `ready` card |
| `swrm release <id> [--force]` | release a claim back to `ready` |
| `swrm reclaim [id] [--force]` | release expired claims back to `ready` |
| `swrm complete <id> --summary "..."` | mark `done`; auto-promotes children whose parents are all done |
| `swrm block <id> --reason "..."` / `swrm unblock <id>` | park / revive a card |
| `swrm move <id> <status>` | set status directly (`todo ready doing done blocked archived`) |
| `swrm assign <id> <agent>` | reassign |
| `swrm edit <id> [--title T] [--body B] [--priority N] [--label L]...` | edit fields |
| `swrm link <parent> <child>` / `swrm unlink <parent> <child>` | dependency links; linking demotes a runnable child to `todo` until parents finish |
| `swrm comment <id> "text"` | add a note to the card's history |
| `swrm rm <id>` / `swrm rm <status>` / `swrm rm --all` | archive one card, all cards in a status (`rm done`, `rm blocked`), or the whole board |
| `swrm prune [--dry-run]` | permanently delete archived cards, their links and their events |
| `swrm events [--task ID] [--limit N]` | dump the change feed |
| `swrm watch [--json] [--since N] [--interval S]` | stream the change feed live (Ctrl-C to stop) |
| `swrm serve [--host H] [--port P] [--passkey K]` | run the **leader server** (default 127.0.0.1:8765) so other PCs can connect via `KANBAN_URL`; `--passkey` requires followers to authenticate |

## Global flags

All commands accept:

| Flag | Env var | Meaning |
|---|---|---|
| `--db PATH` | `$KANBAN_DB` | board database location |
| `--actor NAME` | `$KANBAN_ACTOR` | who is acting |
| `--url URL` | `$KANBAN_URL` | run against a remote leader over HTTP |
| `--passkey SECRET` | `$KANBAN_PASSKEY` | authenticate to the leader |
| `--json` | — | machine-readable output |
