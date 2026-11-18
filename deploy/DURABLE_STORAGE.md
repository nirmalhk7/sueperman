# Persistent Compose storage and recovery

Owner-approved issue #7 deployment: one Linux Docker host, one API worker, the existing persistent `demo-state` volume, and a separate `state-backups` volume. This supports the shared synthetic-data demo. The shared workspace does not provide private account isolation. The existing App Platform demo remains ephemeral and is not migrated by these instructions.

Use a stable project name. Changing `-p sueperman` selects different volumes. Run all commands from the repository root, with Docker/Compose available:

```sh
docker compose -f compose.production.yaml -f compose.durable.yaml -p sueperman up -d --build
docker compose -f compose.production.yaml -f compose.durable.yaml -p sueperman ps
```

The loopback gateway defaults to http://127.0.0.1:3080. `CONTAINER_WEB_PORT` selects another port. The overlay keeps the existing named data volume and adds an operator-only, non-root backup service. It copies no `.env` or provider credentials into snapshots. Paid and public-source provider flags remain off in the checked-in Compose configuration.

**Do not run `down --volumes`, `down -v`, or remove these volumes on a real deployment. Those actions permanently delete the database and backups.** Recreating containers or rebuilding images with the same project and volumes preserves the records. The disposable `make container-test` and `make storage-test` intentionally remove only their own uniquely named test volumes.

## Backup policy and objectives

The backup service checks every 60 seconds and creates a consistent SQLite snapshot when the selected database has no valid snapshot from the last 24 hours. Successful history survives backup-container restart. Source identity includes the canonical path and filesystem identity; switching to a restored filename or replacing the database cannot reuse another source's daily success. The online backup API includes committed WAL data. Published snapshots contain only `database.sqlite3`, `manifest.json`, and an ownership marker. Directories are private (0700), files private (0600), and publication follows file/directory synchronization.

Normal retention expires owner-marked snapshots at seven days. The owner approved an outage exception: preserve the last valid recovery copy until a replacement succeeds, even beyond seven days. A failed attempt does not postpone the next poll. Unknown files, unexpected nested artifacts, symlinks, malformed names and future-dated snapshots are not automatically removed; review those manually. Corrupt or incomplete snapshots never count as successful history. Large or unhealthy databases can miss the daily objective; monitor backup health rather than assuming the schedule guarantees success.

The recovery-point target is the last successful daily snapshot: changes since that snapshot can be lost. Recovery is a manual restore into a new database filename, followed by integrity/API/browser verification. There is no promised recovery-time SLA. Both volumes remain on the same host, so they do not protect against losing that host or its disk. Off-host replication/encryption and host provisioning are not implemented here. Snapshots are plaintext domain databases protected by filesystem permissions, not authenticated archives from untrusted parties.

Inspect health and the selected source's last success:

```sh
docker compose -f compose.production.yaml -f compose.durable.yaml -p sueperman exec -T backup python -m app.storage status --database /data/sueperman.db --directory /backups
```

`status` returns 0 for a current selected-source backup, 1 for due/error status, and 2 for an invalid operation or unavailable source. Omitting `--database` provides an aggregate operator inventory, not health for a selected database. No public HTTP health endpoint exposes backup paths or data.

Create an additional snapshot immediately:

```sh
docker compose -f compose.production.yaml -f compose.durable.yaml -p sueperman exec -T backup python -m app.storage backup --database /data/sueperman.db --directory /backups
```

The command prints the exact snapshot path. Manual snapshots use the same private publication and validation. The scheduler performs retention; it also removes expired, owner-marked interrupted `.partial-` artifacts when safe. A second scheduler or simultaneous storage operation is rejected rather than racing publication/pruning/restoration.

## Restore without overwriting the original

1. Record the desired snapshot ID from status or the backup command. Prefer the most recent valid snapshot. Keep all paid features disabled during recovery.
2. Stop the stack while retaining volumes:

   ```sh
   docker compose -f compose.production.yaml -f compose.durable.yaml -p sueperman down
   ```

3. Restore into a **new** filename. Replace `SNAPSHOT_ID` with the actual ID; do not reuse an existing target or one with SQLite WAL/SHM/journal companions:

   ```sh
   docker compose -f compose.production.yaml -f compose.durable.yaml -p sueperman run --rm --no-deps backup python -m app.storage restore --snapshot /backups/SNAPSHOT_ID --database /data/restored.db
   ```

4. Select that filename consistently for future Compose commands:

   ```sh
   export SUEPERMAN_DATABASE_FILE=restored.db
   docker compose -f compose.production.yaml -f compose.durable.yaml -p sueperman up -d
   ```

5. Check API health, purchase history, source citations and a previously approved local draft in the browser. Confirm a newly required review remains blocked. Inspect the selected source's backup status and make a fresh manual snapshot. Retain the original database for deliberate operator rollback; it was not overwritten. Persist the selected filename in the deployment's operator configuration so a later command does not silently select the old database again.

Restore verifies private ownership markers, checksum, SQLite integrity, foreign keys, schema columns and known version markers before publishing a new target. It refuses incompatible historical collaboration layouts and unknown schema versions; it never drops/rebuilds old tables to make a backup fit. Missing additive tables may be created by normal supported application startup, with old rows preserved. Incompatible databases need a separately reviewed migration on a copy. No automatic migration of the older alternate runtime is claimed.

Historical snapshots cannot prove what executed after their capture. The owner approved conservative recovery: unfinished restored investigations become partial and require a fresh user action; pending case tasks are cancelled. Interrupted source watches retain opt-in but wait at least another day, with related approvals revoked. Completed data, existing approval bindings, quota counters and watch history otherwise retain their snapshot values. Calls or purchases after the snapshot cannot be reconstructed. Reconcile post-snapshot provider usage before re-enabling paid features; application counters are not a provider billing guarantee.

Purchase deletion history has a separate, private journal at the database's persisted authority path. Keep that journal on the persistent data volume. Ordinary database snapshots deliberately do not copy it: restoring yesterday's database must still apply today's deletion records. Restore verifies the snapshot's source identity against the current journal, removes deleted purchases and associated local history before publishing the new database, and preserves other purchases. Retained drafts whose investigation history was removed require a fresh check and approval. Normal startup must reconcile the journal again before serving data or starting workers.

A missing, unreadable, corrupt or mismatched journal blocks restore. Do not replace it with an empty file, move it, restore an older journal over it, or remove deletion records while an older database copy could still be recovered. Minimal purchase identifiers and import fingerprints remain in this journal; receipt contents are not stored there. Losing the data volume loses this authority too. The same-host backup setup does not recover that loss safely.

Snapshots taken before the deletion policy was installed require an explicit current journal, already bound to the original source database. Initialize the policy against the intact original source before recovery, then add `--deletion-journal /data/ACTUAL_JOURNAL_FILE` to the restore command. Use its actual canonical path. An unrelated empty journal is rejected; if the original source and its verified authority cannot be established, automatic restore is refused and requires a separately reviewed migration. An explicit journal cannot override a different authority persisted in a newer snapshot.

## Executable acceptance

`make storage-test` builds a disposable production stack, inserts synthetic state, takes a WAL-safe snapshot, recreates containers on the same volumes, restores into a new filename, and compares every domain table without changing the original. It checks approval/export, receipt quota and watch/job state, and private non-root backup storage. The original synthetic draft is exported and hash-verified through the API; the public browser correctly hides its historical demo approval and shows the imported purchase. Positive public browser export is tested separately with controlled vendor responses, not live-provider proof. These checks do not touch the real `sueperman` project or deploy anything publicly.

`make test` includes focused CLI/scheduler/retention/restore safety checks. `storage.e2e.ts` is excluded from bare `make e2e` because it requires the isolated restored database; `make storage-test` supplies it and requires the browser scenario to execute without skip. Existing test/lint/typecheck/build/smoke/browser/container checks remain mandatory.

Implementation references: [Python SQLite backup API](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup), [SQLite WAL read-only behavior](https://www.sqlite.org/wal.html#read_only_databases), and [Docker volume lifecycle](https://docs.docker.com/engine/storage/volumes/#a-volumes-lifecycle).

## Install deletion history on an existing database

Fresh, empty installations create a private journal automatically. An existing populated database without a deletion policy keeps ordinary features available but refuses deletion until the operator installs its authority. Stop the app first, keep the original database file in place, then run:

```sh
docker compose -f compose.production.yaml -f compose.durable.yaml -p sueperman run --rm --no-deps backup python -m app.deletion initialize --database /data/sueperman.db
```

Use the actual selected database filename. The command prints its fixed journal path and lineage. Restart the app with that same data volume. Re-running installation validates the existing authority; it cannot recreate a missing established journal. Retain the journal and its private permissions. Restored filenames retain the same journal authority; only one application worker may own that lineage at a time.
