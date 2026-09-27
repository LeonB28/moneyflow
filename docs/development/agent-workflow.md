## Kata `work.*` conventions (agent orchestration)

This repo's kata board uses the `work.*` metadata contract; see kata's
<https://katatracker.com/docs/operations/agent-orchestration/> for the full
recipe.

**When you work a kata-tracked issue:**

1. When you claim or start a kata issue, immediately mark it actively tracked:
  `kata meta set <ref> work.attention ok`. This makes in-flight work visible
  to coordinators and dashboards from the moment it is grabbed. 
2. Check if the work branch defined and if so create worktree.
  To get branch use - `kata meta get <ref> work.branch`
  if defined use `git worktree add -b <work.branch> ../moneyflow-worktrees/moneyflow-<ref>`
3. Check if the work plan defined:
   check `kata meta get <ref> work.need_plan` if true then:
   create plan.md. write all steps and decisions, and set work.attention to need-human
4. Keep your live state truthful on the issue:
  `kata meta set <ref> work.attention stuck|needs-human|ok`, with a one-line
  `kata meta set <ref> work.attention_msg "<why>"`. Raise `stuck` when you
  cannot proceed, `needs-human` when you want input or review (you may keep
  working), and clear back to `ok` when unblocked.
5. Never end a session with the signal stale: before stopping, either close
  the issue or set the attention pair to reflect the hand-off.

**When you delegate work as separate kata issues (fan-out/join):**

- Create each sub-issue with `--meta work.branch=...` and an idempotency key;
  capture refs from `--json` (`.issue.short_id`).
- Join with `kata wait <refs> --until attention --any` (matches `needs-human`
  or `stuck`; a close also completes the wait, and the reported reason
  distinguishes which). Use `--timeout` so a wrapper can tell timeout from
  satisfaction. As coordinator you read `work.*`; you never write it on
  issues you delegated.

**Always:** one writer per key; `work.*` on closed issues is meaningless, so
never write it there and ignore it when reading.