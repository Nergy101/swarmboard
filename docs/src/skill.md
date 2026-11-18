# The swarmboard skill

`.vibe/skills/swarmboard/SKILL.md` is the orchestrator playbook for routing a
swarm through this board (load it as `/swarmboard`; adapted from the
`kanban-orchestrator` workflow).

It covers:

- **Decomposition patterns** — how to break a goal into cards and wire
  dependencies with `swrm link` / `--parent`.
- **Parent-gating** — children stay in `todo` until all parents are `done`;
  `swrm complete` auto-promotes them.
- **Anti-temptation rules** — "route, don't execute": the orchestrator adds and
  links cards, workers `swrm claim --any` and do the work.
- **Stuck-card recovery** — `swrm reclaim` for expired claims, `swrm block` /
  `swrm unblock` for parked work, `swrm events` to audit what happened.

All expressed in `swrm` commands, so any agent with the skill loaded can drive
the board the same way.
