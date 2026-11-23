# Commands

| Command | What it does |
|---|---|
| `swrm init` | create the board database |
| `swrm boards [ls] [add <naam> <pad>] [rename <oud> <nieuw>] [rm <naam>]` | manage the board registry (`~/.swarmboard/boards.json`); omit action (or `ls`) to list |
| `swrm switch <naam>` | make a registered board the **active** one used by default |
| `swrm add "title" [--body B] [--assignee A] [--priority N] [--label L]... [--parent ID]...` | create a card; starts `ready`, or `todo` if any parent isn't `done` |
| `swrm ls [--status S] [--assignee A] [--label L]...` | list cards; `--label` repeats (AND) |
| `swrm board [--status S] [--assignee A] [--label L]...` | static column view, optionally filtered |
| `swrm dash` (aliases `dashboard`, `live`) | **live-updating board view** — `--once`, `--follow`, `--interval`, `--feed N`, `--label L`... (AND) |
| `swrm show <id>` | card detail + parents/children + full event history |
| `swrm claim <id>` / `swrm claim --any [--assignee A] [--ttl SECONDS]` | atomically claim a `ready` card |
| `swrm release <id> [--force]` | release a claim back to `ready` |
| `swrm reclaim [id] [--force]` | release expired claims back to `ready` |
| `swrm complete <id> --summary "..."` | mark `done`; auto-promotes children whose parents are all done |
| `swrm block <id> --reason "..."` / `swrm unblock <id>` | park / revive a card |
| `swrm move <id> <status>` | set status directly (`todo ready doing done blocked archived`) |
| `swrm assign <id> <agent>` | reassign |
| `swrm edit <id> [--title T] [--body B] [--priority N] [--label L]...` | edit fields |
| `swrm label add <id> L [M...]` | attach one or more labels to a card |
| `swrm label rm <id> L [M...]` | remove labels from a card |
| `swrm label rm-all <id>` | clear all labels on a card |
| `swrm label ls` | list labels in use, with card counts and colors |
| `swrm label color <label> [<color>]` | set/clear a board-wide label color (`red green yellow blue magenta cyan white default`; empty clears) |
| `swrm link <parent> <child>` / `swrm unlink <parent> <child>` | dependency links; linking demotes a runnable child to `todo` until parents finish |
| `swrm comment <id> "text"` | add a note to the card's history |
| `swrm rm <id>` / `swrm rm <status>` / `swrm rm --all` | archive one card, all cards in a status (`rm done`, `rm blocked`), or the whole board |
| `swrm prune [--dry-run]` | permanently delete archived cards, their links and their events |
| `swrm events [--task ID] [--limit N]` | dump the change feed |
| `swrm watch [--json] [--since N] [--interval S] [--label L]...` | stream the change feed live (Ctrl-C to stop); `--label` filters to cards carrying the label(s) |
| `swrm serve [--host H] [--port P] [--passkey K]` | run the **leader server** (default 127.0.0.1:8765) so other PCs can connect via `KANBAN_URL`; `--passkey` requires followers to authenticate |

## Global flags

All commands accept:

| Flag | Env var | Meaning |
|---|---|---|
| `--db PATH` | `$KANBAN_DB` | board database location |
| `-b NAME` / `--board NAME` | — | pick a board by its registry name (see below) |
| `--actor NAME` | `$KANBAN_ACTOR` | who is acting |
| `--url URL` | `$KANBAN_URL` | run against a remote leader over HTTP |
| `--passkey SECRET` | `$KANBAN_PASSKEY` | authenticate to the leader |
| `--json` | — | machine-readable output |

## Labels and colors

Cards carry any number of plain-text labels. `ls`, `board`, `watch` and `dash`
all accept a repeatable `--label` flag; several labels mean a card must carry
**all** of them (AND).

```bash
swrm add "Polish login form" --label frontend --label urgent
swrm label add t_ab12cd34 ux polish
swrm label ls                     # label, card count, color
swrm label color frontend cyan    # colorize '#frontend' in ls/board/dash
swrm ls --label frontend --label urgent
swrm watch --label frontend       # only feed events for labeled cards
```

Colors are per board (stored in the database) and rendered in `ls`, `board` and
the plain-text `dash` frames. Valid names: `red`, `green`, `yellow`, `blue`,
`magenta`, `cyan`, `white`, `default`; set an empty color to clear. The curses
TUI shows labels without color to keep card widths predictable. Every label
change is emitted to the feed (`labeled` / `unlabeled` / `label-color`), and the
remote snapshot (`GET /snapshot`) exposes the color map so followers render the
same colors.

## Multiple boards

Every board is its own SQLite database. Register boards once, then pick one per
command or switch the default. Like the other global flags, `-b/--board` comes
**after** the subcommand.

```bash
swrm init --db ~/boards/project-a.db
swrm boards add project-a ~/boards/project-a.db
swrm boards add project-b ~/boards/project-b.db
swrm boards                 # list, '->' marks the active board
swrm switch project-a       # project-a becomes the default board
swrm ls                     # uses the active board
swrm ls -b project-b        # peek at another board without switching
swrm boards rename project-a proj-a
swrm boards rm proj-a       # unregister only; the .db file is never touched
```

Resolution order when picking the database: `--db` > `-b/--board` (registry
lookup) > `$KANBAN_DB` > `./.kanban/kanban.db` (if it exists) > the **active**
board from the registry > `./.kanban/kanban.db`. An unknown board name exits
with code 2 before anything is written. Use `swrm boards --json` for a
machine-readable list. The registry lives in `~/.swarmboard/boards.json`
(override with `$SWRM_HOME`); `dash`, `watch` and `serve` show the board name in
their title bar when a named board is selected.
