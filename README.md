<p align="center">
  <img src="assets/logo.svg" alt="swarmboard logo" width="160"/>
</p>

<h1 align="center">swarmboard</h1>

<p align="center">
  <b>One board. The whole swarm.</b><br/>
  A CLI-first kanban board (`swrm`) that any number of agents can work on <b>at the same time</b> —
  with a live terminal view and an immediate change feed. No server, no dependencies.
</p>

<p align="center">
  <a href="#install">Install</a> ·
  <a href="#watch-it-live">Live board</a> ·
  <a href="#multi-agent-usage-one-pc">Multi-agent</a> ·
  <a href="#across-multiple-pcs--leader-follower-mode">Multi-PC</a> ·
  <a href="#commands">Commands</a> ·
  <a href="#the-swarmboard-skill">Skill</a>
</p>

---

## Why swarmboard

Most kanban tools assume one human at a keyboard. **swarmboard** assumes a *swarm*:
many agents (and humans) claiming, commenting, blocking, and completing cards
concurrently — and everyone sees it happen immediately.

- **Concurrency-safe by design** — one SQLite database in WAL mode; claims are
  atomic, so two agents can never grab the same card.
- **Immediate change feed** — every mutation lands in an append-only event log
  in the same transaction. `swrm watch` streams it; `swrm dash` renders it.
- **Terminal-first** — the board *is* the terminal. Open `swrm dash` and watch
  the swarm move.
- **Zero dependencies** — a single Python 3 file (`swrm`) using only the standard library.

## Install

```bash
git clone https://github.com/Nergy101/swarmboard.git
cd swarmboard
chmod +x swrm                   # already executable
ln -s "$PWD/swrm" ~/.local/bin/swrm   # optional: put it on PATH
swrm init                       # create ./.kanban/kanban.db
```

Requires Python 3.8+. Board location: `--db PATH`, else `$KANBAN_DB`, else
`./.kanban/kanban.db`. Actor name: `--actor NAME`, else `$KANBAN_ACTOR`, else
`$USER`. Every command also accepts `--json`. Remote mode: set `$KANBAN_URL`
(or pass `--url`) and every command runs against the leader over HTTP — see
"Across multiple PCs".

## Watch it live

Open a terminal and run:

```bash
swrm dash          # full-screen live board, re-rendered every 0.5s (alias: swrm dashboard)
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
their claim. In the live full-screen view the column headers and feed stay
pinned while you scroll the task rows with ↑/↓ (or j/k); `q` quits. `swrm dash
--once` prints one snapshot (default when piped); `swrm watch --json` is the
NDJSON feed for piping into other agents.

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
T1=$(swrm add "research costs" --assignee researcher --json | jq -r .id)
T2=$(swrm add "research perf"  --assignee researcher --json | jq -r .id)
swrm add "synthesize" --assignee analyst --parent "$T1" --parent "$T2"

# workers self-serve from the board
swrm claim --any --assignee researcher --actor researcher   # atomic claim
swrm comment "$T1" "started" --actor researcher
swrm complete "$T1" --actor researcher --summary "costs done"

# anyone can watch the swarm live
swrm dash
```

Parallel `add`/`claim`/`complete` calls from many processes never lose events.
Claims expire (default TTL 900 s, `--ttl` to change); `swrm reclaim` releases
stale ones back to `ready`.

## Across multiple PCs — leader-follower mode

SQLite is single-host (WAL locking doesn't survive network filesystems), so the
board file lives on **one leader PC**; every other PC is a thin follower that
talks HTTP. All commands work unchanged — set one env var on the followers:

```bash
# PC1 — the leader (owns the database)
swrm serve --host 0.0.0.0 --port 8765 --passkey s3cret   # bind 127.0.0.1 for localhost-only

# PC2, PC3, ... — followers
export KANBAN_URL=http://pc1:8765 KANBAN_PASSKEY=s3cret  # or --passkey s3cret per command
swrm add "task from pc2" --assignee qa
swrm claim --any --assignee qa --actor qa
swrm dash                                     # live board, long-polled from the leader
swrm watch --json                             # NDJSON feed, long-polled from the leader
```

```
PC2 (follower)              PC1 (leader)
swrm claim --any ──HTTP──>  swrm serve ──> SQLite (WAL, atomic claims)
swrm dash       <──GET /snapshot / /events?since=N (long-poll)──
```

- The leader runs the exact same command functions in-process, so claims stay
  **atomic across all PCs** — two followers can never grab the same card.
- `watch`/`dash` on followers long-poll `GET /events?since=N` / `GET /snapshot`,
  so the live feed works over the network with ~LAN-latency updates.
- `--url http://pc1:8765` works per-command as an alternative to `$KANBAN_URL`.
- **Passkey**: `swrm serve --passkey SECRET` (or `$KANBAN_PASSKEY`) makes the
  leader require an `X-Swrm-Passkey: SECRET` header on every request — anything
  missing/wrong gets `401`. Followers set the same secret via
  `KANBAN_PASSKEY` or `--passkey`. Without a passkey the API is open — trusted
  LANs/VPNs only, or front it with an auth-ing reverse proxy.
- HTTP endpoints: `POST /cmd/<command>` (any CLI command, JSON args),
  `GET /events?since=N&timeout=25` (long-poll feed), `GET /events?max=1` (latest),
  `GET /snapshot?feed=N`, `GET /health`.

## Commands

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
| `swrm rm <id>` | archive |
| `swrm events [--task ID] [--limit N]` | dump the change feed |
| `swrm watch [--json] [--since N] [--interval S]` | stream the change feed live (Ctrl-C to stop) |
| `swrm serve [--host H] [--port P] [--passkey K]` | run the **leader server** (default 127.0.0.1:8765) so other PCs can connect via `KANBAN_URL`; `--passkey` requires followers to authenticate |
| all commands | `--url http://leader:8765` / `$KANBAN_URL` to run remotely; `--passkey` / `$KANBAN_PASSKEY` to authenticate |

## The swarmboard skill

`.vibe/skills/swarmboard/SKILL.md` is the orchestrator playbook for routing a
swarm through this board (load it as `/swarmboard`; adapted from the
`kanban-orchestrator` workflow): decomposition patterns, parent-gating,
anti-temptation rules ("route, don't execute"), and stuck-card recovery — all
expressed in `swrm` commands.

## Docs

Docs live at **[nergy101.github.io/swarmboard](https://nergy101.github.io/swarmboard/)** —
deployed automatically to GitHub Pages by `.github/workflows/docs.yml` on every
push to `main` that touches `docs/`. Sources are the Markdown files in `docs/src/`
(MkDocs + Material); the built static HTML is in `docs/site/` and can also be
served locally with any static file server:

```bash
python3 -m http.server -d docs/site 8000     # or rebuild: python3 -m mkdocs build
```

## Development

Single file: `swrm` (Python 3 stdlib only). Schema: `tasks`, `links`
(parent→child), `events` (append-only audit feed). Brand assets in `assets/`:
`logo.svg` (hive mark on dark tile, used above), `logo-mark.svg` (mark only,
transparent), `logo-wordmark.svg` (mark + wordmark + tagline),
`favicon.svg` / `favicon.ico` (16–256 px).
