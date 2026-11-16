# Private session logs

New game summaries and supervised diagnostic captures are written here. Only
this README and the blank CSV template are intended for Git. Games record
connection/frame/error summaries; `--trace-packets` adds full transport events.

Completed research runs, downloaded artwork and old logs have been compressed
under ignored `archive/private/`, preserving original paths and file hashes.
See [recovery instructions](../docs/development.md#private-archives).

The shared panel preference lives in `.state/panel-settings.json`, independent
of log retention. Legacy `snake-settings.json` is migrated on first use.
Review device identifiers and unrelated traffic before sharing captures.
