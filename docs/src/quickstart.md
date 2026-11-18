# Quickstart

```bash
swrm init                                   # create the board
swrm add "research costs" --assignee researcher
swrm add "ship it" --parent t_aa11          # starts in todo until parent is done
swrm claim --any --assignee researcher --actor researcher
swrm comment t_aa11 "started" --actor researcher
swrm complete t_aa11 --actor researcher --summary "costs done"
swrm dash                                   # live board
```

## Watch it live

```bash
swrm dash          # full-screen live board, re-rendered every 0.5s (alias: swrm dashboard)
```

```
 KANBAN /proj/.kanban/kanban.db   2026-11-17T23:21:40Z
todo:1  ready:2  doing:1  blocked:0  done:12
----------------------------------------------------------------
TODO (1)        READY (2)       DOING (1)       BLOCKED (0)  DONE (12)
--------------  --------------  --------------  -----------  ------
┌────────────┐  ┌────────────┐  ┌────────────┐
│research    │  │ship the    │  │polish      │
│costs       │  │API         │  │dashboard   │
│t_aa11 P1   │  │t_bb22 P3   │  │t_9f4b P0   │
│@dev        │  │@qa         │  │[dev 14m59s]│
└────────────┘  └────────────┘  └────────────┘
 feed: #41 dev claimed t_9f4b ...  #42 qa done t_cc33 ...
```

Each card is a bordered box (tinted with its column color): **title first**,
with a dim meta line underneath (`id`, priority, assignee or claim time left).

`doing` rows show **which worker picked up which task** and the time left on
their claim. In the live full-screen view the column headers and feed stay
pinned; move the cursor with ↑/↓/←/→ (or hjkl) and press **Enter or click a
card** to open a detail modal (history, parents/children, body); `q` closes the
modal / quits. `swrm dash --once` prints one snapshot (default when piped);
`swrm watch --json` is the NDJSON feed for piping into other agents.

## Lifecycle

```
todo ──(all parents done)──> ready ──(claim)──> doing ──> done
                                            └───────> blocked ──(unblock)──> ready
```

Claims expire (default TTL 900 s, `--ttl` to change); `swrm reclaim` releases
stale ones back to `ready`.
