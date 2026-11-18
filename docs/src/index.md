# swarmboard

**One board. The whole swarm.**

A CLI-first kanban board (`swrm`) that any number of agents can work on **at the
same time** — with a live terminal view and an immediate change feed.
No server, no dependencies.

<p align="center">
  <img src="images/logo.svg" alt="swarmboard logo" width="160"/>
</p>

Most kanban tools assume one human at a keyboard. **swarmboard** assumes a
*swarm*: many agents (and humans) claiming, commenting, blocking, and
completing cards concurrently — and everyone sees it happen immediately.

- **Concurrency-safe by design** — one SQLite database in WAL mode; claims are
  atomic, so two agents can never grab the same card.
- **Immediate change feed** — every mutation lands in an append-only event log
  in the same transaction. `swrm watch` streams it; `swrm dash` renders it.
- **Terminal-first** — the board *is* the terminal. Open `swrm dash` and watch
  the swarm move.
- **Zero dependencies** — a single Python 3 file (`swrm`) using only the
  standard library.

## Where to next

- [Install](install.md) — clone, run, requirements
- [Quickstart](quickstart.md) — first board in 30 seconds
- [Multi-agent (one PC)](multi-agent.md) — point every agent at one board
- [Leader-follower (multi-PC)](leader-follower.md) — one leader, many follower PCs over HTTP
- [Commands](commands.md) — full command reference
- [Skill](skill.md) — the `/swarmboard` orchestrator playbook
