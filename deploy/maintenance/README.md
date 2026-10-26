# Server resource policy

These files are for an explicitly authorized server-maintenance run, not application startup or an unattended cleanup job.

Run on the target Linux host as root:

```sh
python3 apply_resource_policy.py          # Preview paths and validate empty legacy volumes only
python3 apply_resource_policy.py --apply  # Apply log limits, rotate/compress, clean dnf cache, remove verified empty legacy volumes
```

The script never removes a project, tagged image, nonempty data volume, database, test artifact, build dependency cache, or deployment backup. It validates the exact volume paths and references again immediately before removal. Existing target configuration is saved below `/opt/cling-maintenance-backups` and restored on failure; successfully expired journal data is not recoverable through configuration rollback. Text logs are compressed rather than discarded during the initial run.

Review the dated maintenance report before any additional pruning. In particular, an unreferenced image may be a rollback image, and a separate Compose project may still serve a platform module.
