<p align="center">
  <img src="assets/logo.svg" alt="swarmboard logo" width="160"/>
</p>

<h1 align="center">swarmboard</h1>

<p align="center">
  <b>One board. The whole swarm.</b><br/>
  A CLI-first kanban board that any number of agents can work on <b>at the same time</b> —
  with a live terminal view and an immediate change feed. No server, no dependencies.
</p>

<p align="center">
  <a href="#install">Install</a> ·
  <a href="#watch-it-live">Live board</a> ·
  <a href="#multi-agent-usage">Multi-agent</a> ·
  <a href="#commands">Commands</a> ·
  <a href="#the-kanban-cli-skill">Skill</a>
</p>

---

## Why swarmboard

Most kanban tools assume one human at a keyboard. **swarmboard** assumes a *swarm*:
many agents (and humans) claiming, commenting, blocking, and completing cards
concurrently — and everyone sees it happen immediately.

- **Concurrency-safe by design** — one SQLite database in WAL mode; claims are
  atomic, so two agents can never grab the same card.
- **Immediate change feed** — every mutation lands in an append-only event log
  in the same transaction. `kanban watch` streams it; `kanban dash` renders it.
- **Terminal-first** — the board *is* the terminal. Open `kanban dash` and watch
  the swarm move.
- **Zero dependencies** — a single Python 3 file using only the standard library.

## Install

```bash
git clone https://github.com/Nergy101/swarmboard.git
cd swarmboard
chmod +x kanban                 # already executable
ln -s "$PWD/kanban" ~/.local/bin/kanban   # optional: put it on PATH
./kanban init                   # create ./.kanban/kanban.db
```

Requires Python 3.8+. Board location: `--db PATH`, else `$KANBAN_DB`, else
`./.kanban/kanban.db`. Actor name: `--actor NAME`, else `$KANBAN_ACTOR`, else
`$USER`. Every command also accepts `--json`. Remote mode: set `$KANBAN_URL`
(or pass `--url`) and every command runs against the leader over HTTP — see
"Across multiple PCs".

## Watch it live

Open a terminal and run:

```bash
kanban dash        # full-screen live board, re-rendered every 0.5s
```

```
 KANBAN /proj/.kanban/kanban.db   2026-11-17T23:21:40Z
todo:1  ready:2  doing:1  blocked:0  done:12
----------------------------------------------------------------
TODO (1)        READY (2)       DOING (1)       BLOCKED (0)  DONE (12)
--------------  --------------  --------------  -----------  ------
t_aa11 P1 @dev  t_bb22 P3 @qa   t_9f4b P0 [dev 14m59s] polish dashboard
 feed: #41 dev claimed t_9f4b ...  #42 qa done t_cc33 ...
```

`doing` rows show **which worker picked up which task** and the time left on
their claim. Ctrl-C to stop. `kanban dash --once` prints one snapshot (default
when piped); `kanban watch --json` is the NDJSON feed for piping into other
agents.

## Lifecycle

```
todo ──(all parents done)──> ready ──(claim)──> doing ──> done
                                            └───────> blocked ──(unblock)──> ready
```

## Multi-agent usage (one PC)

Point every agent at the same board and give each a distinct actor name:

```bash
export KANBAN_DB=/shared/project/.kanban/kanban.db

# orchestrator fans work out — children wait for their parents automatically
T1=$(kanban add "research costs" --assignee researcher --json | jq -r .id)
T2=$(kanban add "research perf"  --assignee researcher --json | jq -r .id)
kanban add "synthesize" --assignee analyst --parent "$T1" --parent "$T2"

# workers self-serve from the board
kanban claim --any --assignee researcher --actor researcher   # atomic claim
kanban comment "$T1" "started" --actor researcher
kanban complete "$T1" --actor researcher --summary "costs done"

# anyone can watch the swarm live
kanban dash
```

Parallel `add`/`claim`/`complete` calls from many processes never lose events.
Claims expire (default TTL 900 s, `--ttl` to change); `kanban reclaim` releases
stale ones back to `ready`.

## Across multiple PCs — leader-follower mode

SQLite is single-host (WAL locking doesn't survive network filesystems), so the
board file lives on **one leader PC**; every other PC is a thin follower that
talks HTTP. All commands work unchanged — set one env var on the followers:

```bash
# PC1 — the leader (owns the database)
kanban serve --host 0.0.0.0 --port 8765        # bind 127.0.0.1 for localhost-only

# PC2, PC3, ... — followers
export KANBAN_URL=http://pc1:8765
kanban add "task from pc2" --assignee qa
kanban claim --any --assignee qa --actor qa
kanban dash                                     # live board, long-polled from the leader
kanban watch --json                             # NDJSON feed, long-polled from the leader
```

```
PC2 (follower)              PC1 (leader)
kanban claim --any ──HTTP──> kanban serve ──> SQLite (WAL, atomic claims)
kanban dash        <──GET /snapshot / /events?since=N (long-poll)──
```

- The leader runs the exact same command functions in-process, so claims stay
  **atomic across all PCs** — two followers can never grab the same card.
- `watch`/`dash` on followers long-poll `GET /events?since=N` / `GET /snapshot`,
  so the live feed works over the network with ~LAN-latency updates.
- `--url http://pc1:8765` works per-command as an alternative to `$KANBAN_URL`.
- The HTTP API is unauthenticated (stdlib `http.server`) — use it on trusted
  LANs/VPNs only; put it behind a reverse proxy with auth if you expose it.
- HTTP endpoints: `POST /cmd/<command>` (any CLI command, JSON args),
  `GET /events?since=N&timeout=25` (long-poll feed), `GET /events?max=1` (latest),
  `GET /snapshot?feed=N`, `GET /health`.

## Commands

| Command | What it does |
|---|---|
| `kanban init` | create the board database |
| `kanban add "title" [--body B] [--assignee A] [--priority N] [--label L]... [--parent ID]...` | create a card; starts `ready`, or `todo` if any parent isn't `done` |
| `kanban ls [--status S] [--assignee A] [--label L]` | list cards |
| `kanban board` | static column view |
| `kanban dash` (aliases `dashboard`, `live`) | **live-updating board view** — `--once`, `--follow`, `--interval`, `--feed N` |
| `kanban show <id>` | card detail + parents/children + full event history |
| `kanban claim <id>` / `kanban claim --any [--assignee A] [--ttl SECONDS]` | atomically claim a `ready` card |
| `kanban release <id> [--force]` | release a claim back to `ready` |
| `kanban reclaim [id] [--force]` | release expired claims back to `ready` |
| `kanban complete <id> --summary "..."` | mark `done`; auto-promotes children whose parents are all done |
| `kanban block <id> --reason "..."` / `kanban unblock <id>` | park / revive a card |
| `kanban move <id> <status>` | set status directly (`todo ready doing done blocked archived`) |
| `kanban assign <id> <agent>` | reassign |
| `kanban edit <id> [--title T] [--body B] [--priority N] [--label L]...` | edit fields |
| `kanban link <parent> <child>` / `kanban unlink <parent> <child>` | dependency links; linking demotes a runnable child to `todo` until parents finish |
| `kanban comment <id> "text"` | add a note to the card's history |
| `kanban rm <id>` | archive |
| `kanban events [--task ID] [--limit N]` | dump the change feed |
| `kanban watch [--json] [--since N] [--interval S]` | stream the change feed live (Ctrl-C to stop) |
| `kanban serve [--host H] [--port P]` | run the **leader server** (default 127.0.0.1:8765) so other PCs can connect via `KANBAN_URL` |

## The kanban-cli skill

`.vibe/skills/kanban-cli/SKILL.md` is the orchestrator playbook for routing a
swarm through this board (adapted from the `kanban-orchestrator` workflow):
decomposition patterns, parent-gating, anti-temptation rules ("route, don't
execute"), and stuck-card recovery — all expressed in these CLI commands.

## Development

Single file: `kanban` (Python 3 stdlib only). Schema: `tasks`, `links`
(parent→child), `events` (append-only audit feed). Logo: `assets/logo.svg`.
