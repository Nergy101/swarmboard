---
name: kanban-cli
description: Load this skill when routing multi-agent work through the `kanban` CLI board (the single-file SQLite kanban tool in this repo). Decomposition playbook + anti-temptation rules for an orchestrator agent: create cards with `kanban add`, gate them with `kanban link`/`--parent`, let workers self-claim with `kanban claim --any`, and follow the live change feed with `kanban watch`.
---

# kanban-cli — Orchestrator Playbook for the `kanban` CLI

This is the adapted playbook for the `kanban` command in this repo: a
CLI-first, SQLite-backed kanban board that any number of agents can use at
the same time, with a live change feed (`kanban watch`). It replaces the
Hermes `kanban_*` tool calls with shell commands.

> The board is one SQLite database (WAL mode), so concurrent agents are
> safe: claims are atomic and every mutation lands in the `events` feed in
> the same transaction. Point every agent at the same board with `--db
> PATH` or `$KANBAN_DB` (default `./.kanban/kanban.db`).

## The lifecycle

```
todo ──(all parents done)──> ready ──(kanban claim)──> doing ──> done
                                                              └────> blocked ──(kanban unblock)──> ready
```

- `kanban add "title"` creates a card in `ready` (or `todo` if it has unfinished parents).
- `kanban claim <id>` / `kanban claim --any --assignee <you>` atomically moves a card to `doing`. Two agents can never claim the same card.
- `kanban complete <id> --summary "..."` marks `done` and auto-promotes children whose parents are all done.
- `kanban block <id> --reason "..."` parks a card for human input; `kanban unblock <id>` returns it to `ready`.
- Claims expire (default TTL 900s, `--ttl` to change). `kanban reclaim` releases expired claims back to `ready`.

Every command accepts `--json` (machine-readable output) and `--actor NAME`
(or `$KANBAN_ACTOR`) so the feed shows who did what.

## Step 0 — discover the agents before planning

Assignees are free-form names — there is no fixed roster, and nothing
validates them, so a card assigned to a name nobody uses just sits in
`ready` forever. Ground your plan in the agents that actually exist:

- `kanban ls --assignee <name>` — sanity-check a single name (empty list = nobody has used it yet).
- Ask the user: "Which agents are working on this?" is a fine first turn.

Cache the answer; don't re-ask every turn.

## When to use the board (vs. just doing the work)

Create cards when any of these are true:

1. **Multiple agents are needed.** Research + implementation + review is three assignees.
2. **The work should survive a crash or restart.** The board persists in SQLite forever.
3. **The user might want to interject.** Human-in-the-loop at any step.
4. **Subtasks can run in parallel.** Fan-out for speed.
5. **Review / iteration is expected.** A reviewer loops on a drafter's output.
6. **The audit trail matters.** Every mutation is an event in the feed (`kanban events`, `kanban watch`).

If none apply — a small one-shot task — just do it or answer directly.

## The anti-temptation rules

Your job is to **route, don't execute**:

- **Do not do the work yourself.** If you find yourself "just fixing this quickly" — stop and create a card for the right agent.
- **For any concrete task, create a card and assign it.** Every single time.
- **Split multi-lane requests before creating cards.** One card per independent lane, not one bundled card.
- **Run independent lanes in parallel.** Leave them unlinked; link only true data dependencies.
- **Never create dependent work as an independent ready card.** Pass `--parent <id>` at creation time. Do not create-then-link later, and do not rely on prose like "wait for T1" in the body.
- **If no agent fits a lane, ask the user** which agent to use. Do not invent names.
- **Decompose, route, and summarize — that's the whole job.**

## Decomposition playbook

### Step 1 — Understand the goal

Ask clarifying questions if the goal is ambiguous. Cheap to ask; expensive to spawn the wrong fleet.

### Step 2 — Sketch the task graph

Draft the graph out loud before creating anything:

1. Extract the lanes from the request.
2. Map each lane to an agent from Step 0.
3. Decide whether each lane is independent or gated by another lane.
4. Independent lanes → parallel cards, no parents.
5. Synthesis/review cards → `--parent` links to the lanes they depend on. A child created with unfinished parents starts in `todo` and is auto-promoted to `ready` only after every parent reaches `done`.

Show the graph to the user before creating cards. Let them correct it, including which agent owns each lane.

### Step 3 — Create the cards

Create parents first, capture their ids, then pass them to children with `--parent` (repeatable):

```bash
T1=$(kanban add "research: Postgres cost vs current" --assignee researcher --json | jq -r .id)
T2=$(kanban add "research: Postgres performance vs current" --assignee researcher --json | jq -r .id)
T3=$(kanban add "synthesize migration recommendation" --assignee analyst \
     --parent "$T1" --parent "$T2" \
     --body "Read the findings from $T1 (cost) and $T2 (performance). Produce a 1-page recommendation with explicit trade-offs and a go/no-go call." \
     --json | jq -r .id)
T4=$(kanban add "draft decision memo" --assignee writer \
     --parent "$T3" \
     --body "Turn the analyst's recommendation into a 2-page memo for the CTO." \
     --json | jq -r .id)
```

`--parent` gates promotion — children stay in `todo` until every parent is `done`, then auto-promote to `ready`. No manual coordination needed.

Avoid creating all cards in parallel and linking them afterward with `kanban link` — that leaves a window where a worker can claim a child before its inputs exist. (`kanban link <parent> <child>` still exists for fixing graphs after the fact; note it demotes a runnable child back to `todo` if the new parent isn't done.)

### Step 4 — Workers pick up their own cards

There is no central dispatcher — agents self-serve from the board:

```bash
kanban claim --any --assignee researcher --actor researcher   # best ready card assigned to me
kanban show "$ID"                                             # read the card
kanban comment "$ID" "started; will post findings"            # progress note in the feed
kanban complete "$ID" --summary "..."                         # done
kanban block "$ID" --reason "need credentials for X"          # stuck
```

### Step 5 — Report back to the user

Tell them what you created in plain prose, naming the actual agents:

> I've queued 4 cards:
> - **T1** (`researcher`): cost comparison
> - **T2** (`researcher`): performance comparison, in parallel with T1
> - **T3** (`analyst`): synthesizes T1 + T2 into a recommendation
> - **T4** (`writer`): turns T3 into a CTO memo
>
> T1 and T2 are `ready` now. T3 starts when both finish. Follow along with `kanban watch` or `kanban show <id>`.

## Multiple machines — leader-follower mode

The board file is single-host SQLite, so across PCs one machine is the
**leader** and the rest are followers:

```bash
# leader PC — owns the database, serves the API
kanban serve --host 0.0.0.0 --port 8765

# every other PC / agent
export KANBAN_URL=http://leader:8765
kanban add "task" --assignee researcher      # identical commands, run remotely
kanban claim --any --assignee researcher
kanban dash                                   # live board long-polled from the leader
```

Claims stay atomic across all machines because only the leader touches the
database. `watch`/`dash` long-poll the leader's event feed. The API is
unauthenticated — trusted LAN/VPN only. Same board on one PC? Just share
`$KANBAN_DB` and skip `serve` entirely.

## Following the work live

```bash
kanban dash                  # LIVE board in the terminal: columns re-render as work happens,
                             # doing rows show [worker 12m30s] claim countdowns, feed at the bottom
kanban dash --once           # single snapshot (default when piped)
kanban watch                 # human-readable live feed of every mutation, Ctrl-C to stop
kanban watch --json          # NDJSON stream — pipe into jq or another agent
kanban watch --since 42      # replay the feed from event #42
kanban board                 # static column view
kanban events --task t_ab12cd34 --limit 100
```

## Common patterns

**Fan-out + fan-in (research → synthesize):** N research cards with no parents, one synthesis card with all of them as `--parent`s.

**Parallel implementation + validation:** one implementer card makes the change while one researcher card verifies config/docs/source. A reviewer card can depend on both. Don't make the implementer own unrelated verification just because the user mentioned both in one sentence.

**Pipeline with gates:** `planner → implementer → reviewer`, each stage's `--parent` pointing at the previous card. If the reviewer blocks, the operator unblocks with feedback (`kanban unblock`) or creates a new fix card.

**Same-agent queue:** N cards, all `--assignee` the same agent, no dependencies. The agent processes them in priority order (`--priority`, higher first) via repeated `kanban claim --any --assignee <name>`.

**Human-in-the-loop:** any card can `kanban block <id> --reason "..."` to wait for input; the comment thread (`kanban comment`) carries the context.

## Pitfalls

**Inventing agent names that don't exist.** Nothing validates assignees — the card just sits in `ready` forever. Always assign to an agent from your Step 0 discovery; ask the user if unsure.

**Bundling independent lanes into one card.** "Fix blockers and check model variants" is two cards: one for the fixes, one for the variant check, optionally gated review on both.

**Over-linking because of wording.** "Finally check X" may still run in parallel if X is static config or docs. Link only when the check depends on the other card's output.

**Forgetting dependency links.** If the graph is `research → implement → review`, do not create all three as independent ready cards. Use `--parent` so implement/review cannot run before their inputs exist.

**Reassignment vs. new task.** If a reviewer blocks with "needs changes," create a NEW card with `--parent <reviewer-card>` assigned to the original implementer — don't just unblock the same card.

**Argument order for links.** `kanban link <parent> <child>` — parent first. Mixing them up demotes the wrong task to `todo`.

**Don't pre-create the whole graph if the shape depends on intermediate findings.** Let the synthesis card exist as "read parent handoffs and plan the rest." Orchestrators can spawn orchestrators.

**Board selection.** If `$KANBAN_DB` is set, every agent must use the same board — pass `--db "$KANBAN_DB"` (or export the env var) on every call so cards stay in the same namespace.

## Long-running cards (persistent workers)

A worker normally gets one shot at a card: claim, work, `kanban complete`/`kanban block`. For open-ended cards where one pass rarely finishes the job:

- Write the body as **explicit acceptance criteria** — "Translate every section of the README to French; no English sentences remain" beats "translate the README".
- Claim with a long TTL: `kanban claim <id> --ttl 86400`.
- Post progress with `kanban comment <id> "..."` so the feed shows the card is alive.
- If the claim expires while work continues, `kanban reclaim` (or the worker re-claiming after `kanban release`) puts it back — never leave a stale `doing` card without a comment.

## Recovering stuck cards

When a card sits in `doing` forever (crashed worker, lost agent):

1. **Reclaim** — `kanban reclaim` releases all expired claims back to `ready` (claim TTL is 900s by default). For one specific card: `kanban reclaim <id> --force`.
2. **Reassign** — `kanban assign <id> <new-agent>` after `kanban release <id> --force`, so another agent can `kanban claim` it fresh.
3. **Check the trail** — `kanban show <id>` prints the full event history; hallucinated or missing handoffs show up there and stay there for debugging.
