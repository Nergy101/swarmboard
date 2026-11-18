# Multi-agent usage (one PC)

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
Claims are atomic: two agents can never grab the same card.
