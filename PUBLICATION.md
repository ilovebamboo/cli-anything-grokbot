# Public export review

This repository was prepared as a new, allowlisted source-only export, not as a
push of a development directory or its history.

## Excluded

- Real Bot/group IDs, names, transcripts, acknowledgements and run receipts
- Local absolute home paths, account configuration and project handoff documents
- Cookies, credential stores, encrypted gateway files, environment files and tokens
- Virtual environments, caches, logs, build metadata and screenshots
- Grok Bot binaries, extracted application bundles and third-party application code

Only synthetic test identifiers remain. Upstream CLI-Anything REPL skin is retained
with its Apache-2.0 license and attribution. Runtime integration must use a separately
installed application that the operator is authorized to control.

## Checks performed before publication

- 72 offline tests passed; live suites are opt-in and were not used for this export
- Explicit live-file collection without opt-in is rejected
- Indexed-file path/identifier/secret-pattern audit: no findings
- Gitleaks 8.30.1 scan of the indexed source export: no findings
- Wheel inspected for both JavaScript assets, absence of live fixtures/tests/caches,
  and absence of personal home paths
- Commit identity uses GitHub's no-reply email rather than a personal email address

These checks are not a claim that the software is vulnerability-free. CDP's broad
local access and the private app bridge remain significant trust boundaries; read
SECURITY.md. Future commits must be reviewed and scanned independently.
