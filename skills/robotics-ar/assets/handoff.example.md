# Robot-AR Handoff

## Last Stable Checkpoint

`batch-checkpoint.json` and its hash.

## Active Session / Batch / Trial

Record session, batch, and trial identifiers.

## Active Contract Hash

`...`

## Project Core Hash

`...`

## Baseline Receipt

Path and SHA-256.

## Git Branch / Commit / Dirty Diff

Record the exact branch, commit, and dirty-worktree status.

## Environment Fingerprint

`...`

## Exact Reproduction Commands

List argv commands, not shell snippets.

## Exact Resume Command

```bash
python3 skills/robotics-ar/scripts/robotics_ar.py takeover-status --project-root /path/to/project
```

## Known Risks and Pending User Decision

List unresolved blocks and the safe rollback point.

# English

# Robot-AR Handoff

This machine-facing handoff must preserve hashes, branch/commit, processes, leases,
environment fingerprint, artifact paths, exact commands, rollback point, and the safe
resume command. A new session must not depend on the previous conversation.
