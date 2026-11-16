# Private captures

Save scans as JSON, notifications as streaming JSONL, and official-app HCI captures
with experiment notes here. Raw data is ignored by Git; only this README and the
blank CSV template are intended for source control. Store filenames with timestamps
or experiment IDs; discovery tools refuse to overwrite existing files.

Review identifiers and unrelated traffic before sharing. Full Android bugreports
can contain personal data. Keep a private original and create a target-only extract.
`listen` observes the PC's selected notification subscription; use phone HCI logging
to observe the official app's writes. See [HARDWARE_TESTS.md](../HARDWARE_TESTS.md).

No real captures are supplied yet. Synthetic objects in tests are explicitly mocks.
