# Across multiple PCs — leader-follower mode

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

## Passkey authentication

`swrm serve --passkey SECRET` (or `$KANBAN_PASSKEY`) makes the leader require an
`X-Swrm-Passkey: SECRET` header on every request — anything missing/wrong gets
`401`. Followers set the same secret via `KANBAN_PASSKEY` or `--passkey`.
Without a passkey the API is open — trusted LANs/VPNs only, or front it with an
auth-ing reverse proxy.

## HTTP endpoints

| Endpoint | Description |
|---|---|
| `POST /cmd/<command>` | any CLI command, JSON args |
| `GET /events?since=N&timeout=25` | long-poll change feed |
| `GET /events?max=1` | latest event |
| `GET /snapshot?feed=N` | full board snapshot |
| `GET /health` | health check |
