# Owner decisions — November 17, 2026 Pacific

These decisions were made in the active issue-by-issue implementation chat. They do not record implementation or passing evidence.

- Issue #6: resume only durably queued, never-started jobs automatically. Interrupted jobs with uncertain external effects stay partial and require a fresh user action. Interrupted public watches retain opt-in and resume on the next daily schedule, with no immediate retry.
- Issue #6: extend the exact additive, byte-preserving frozen audit to collaboration/controller.py and collaboration/ledger.py. Preserve original bytes and frozen outcomes; retain existing approved team API safety insertions.
- Issue #7: use the existing persistent Docker Compose deployment arrangement, daily backups, seven-day retention and a tested restore runbook. The existing App Platform demo remains explicitly ephemeral unless separately migrated.
- Issue #8: “For now keep a dummy authentication: no need to build a proper one.” This supersedes implementing real authentication for this pass. Dummy sign-in does not establish private account isolation; shared synthetic-data labeling remains required. Do not claim the original private-isolation capability is delivered.
- Issue #9: purchases retained until user deletion. Deletion removes associated local records and watches. Backups expire after seven days; restore must reapply deletion records.
- Issue #10: evidence preparation is guidance-only, with no private file uploads.
- Issue #2: owner asked to use subagents where needed. Agent proxy review and automation must remain labeled as such; they cannot be recorded as real human participants. No human sessions have occurred in the recorded protocol.

Commits must reference the relevant issue ID. An issue may close only after an independent subagent verifies its actual completion; implementation intent, a partial test run, or a narrowed unsupported completion claim does not qualify. No unrelated comments, deployments, paid provider runs or publication are authorized by this local implementation record.
