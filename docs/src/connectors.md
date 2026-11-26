# Connectors

Connectors mirror swarmboard cards to external systems. A connector is a
small piece of config next to your board database plus a per-connector sync
state in the board itself. **Linear is the first connector**; GitHub Issues,
Jira, Trello and Notion are worked out at design level below (NER-331) so
they can reuse the same interface.

## How a connector works

- **Config**: `connectors.json` next to the board database
  (`$KANBAN_DB/../connectors.json` or `./.kanban/connectors.json`).
- **Secrets**: `connectors.secrets.json` next to it (mode `600`), written by
  `swrm connector auth`. Tokens are **never** stored in the board database;
  a per-type environment variable (`$SWRM_LINEAR_TOKEN`) works too.
- **Sync state**: the `connector_state` table in the board database (push
  cursor, pull cursor, per-issue markers, last sync, last error).
- **Card ↔ issue link**: the `external_ref` column on tasks holds the external
  issue id.
- **Sync direction**: one `swrm connector sync` cycle first **pushes** board
  events (title, body, status) to the external system, then **pulls** external
  changes back onto the board. Conflict policy is **last-write-wins**; every
  applied pull change is logged in the event feed with actor
  `connector:<naam>` so the history stays replayable.
- **Idempotent & resumable**: cursors make every cycle safe to repeat; on
  error the cursor stays at the failing event and the next run retries.
  429/5xx/network errors get exponential backoff (honoring `Retry-After`).
- `sync --full` forgets cursors and resyncs everything (still idempotent:
  linked cards are updated, not duplicated).

## Commands

```bash
swrm connector ls                                  # what is configured?
swrm connector add linear werk --key team=NER \
    --key project="Swarmboard" --map blocked=Blocked
swrm connector auth werk --token lin_api_...       # or --token-file / $SWRM_LINEAR_TOKEN
swrm connector sync [werk] [--full]                # werk, or all unpaused connectors
swrm connector pause werk && swrm connector resume werk
swrm connector status [werk]                       # cursors, last sync, last error
swrm connector rm werk                             # also clears sync state
```

Status mapping defaults to:

| Board | Linear |
|---|---|
| todo / ready | Todo |
| doing | In Progress |
| blocked | In Review (default; override with `--map blocked=Blocked`) |
| done | Done |

`--map` is repeatable and maps *board status → external status name*.
For pull, the reverse mapping is used (first match wins: `Todo → todo`).
Unknown external statuses leave the card alone and count as skipped.
Config keys: `team`, `project`, `pull_new` (create cards for unknown issues
while pulling; default off), `api_base` (default: `https://api.linear.app/graphql`).

!!! note
    The Linear issue text mentioned a "REST v1" API, but Linear only offers a
    GraphQL API; the connector therefore speaks GraphQL over stdlib `urllib`.
    No extra dependencies.

## Linear quickstart

```bash
swrm init                                            # or use an existing board
swrm connector add linear ner --key team=NER         # team key, name or id
swrm connector auth ner --token lin_api_xxx           # personal API key
swrm add "Fix login bug"                              # a card on the board
swrm connector sync ner
swrm show t_abc12345          # the card now carries the Linear issue id
```

Pull direction: change the issue's status in Linear, then `swrm connector
sync ner` moves the card (`In Progress → doing`). If you want new Linear
issues to appear on the board automatically, add `--key pull_new=true`.

## Design: follow-up connectors

All follow-ups reuse the same interface. `pull(delta)`, `push(event)`,
`map_fields` and `conflict` stay the same shape; only the transport differs.

### GitHub Issues

- **Scope**: one repository (`--key repo=Nergy101/swarmboard`); optional label
  filter (`--key require_label=agent`) to keep human issues out.
- **Auth**: GitHub token (`$SWRM_GITHUB_TOKEN`), REST v3 + GraphQL where
  needed.
- **Mapping**: card ↔ issue by `external_ref` (issue node id); `body` ↔ issue
  body; board status ↔ issue state (open/closed) plus a status label
  (`blocked`, `doing`) for in-between states. Linked PRs land as `link`s on
  the card so a card waits for its PR.
- **Direction**: two-way, same cursors as Linear. PR merges can mark cards done.

### Jira

- **Scope**: one project key + a JQL filter (`--key jql=...`).
- **Auth**: API token + email Basic auth, or PAT.
- **Mapping**: board status ↔ Jira workflow status by name
  (`--map doing="In Progress"`); configurable through the same `--map`.
- **Direction**: two-way. Jira's `updated` cursor replaces the Linear cursor;
  last-write-wins, decisions as events.

### Trello

- **Scope**: one Trello board; card ↔ Trello card by `external_ref` (card id).
- **Auth**: app key + token (`$SWRM_TRELLO_TOKEN`).
- **Mapping**: board status ↔ Trello list id (`--map doing=<list-id>`).
- **Direction**: two-way, list moves in both directions.

### Notion

- **Scope**: one Notion database; card ↔ database row.
- **Auth**: integration token (`$SWRM_NOTION_TOKEN`), database shared with
  the integration.
- **Mapping**: property mapping (`--map title=Name --map status=Status`);
  select/status property values map like status names elsewhere.
- **Direction**: two-way, with a `--key pull_new=true` toggle like Linear.
