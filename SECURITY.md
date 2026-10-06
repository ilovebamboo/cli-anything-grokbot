# Security and privacy

## Trust boundary

This is a local automation tool, not a security sandbox. Enabling CDP permits local
processes to control a signed-in Grok Bot renderer. CDP is not an authenticated API.
Only bind to 127.0.0.1, never forward/expose the port, and close/reopen the app normally
when automation is no longer needed. Do not run untrusted agents/scripts against it.
The transport only accepts the expected Grok Bot main-page URL and loopback WebSockets.
This check cannot defend against a malicious process already running as your OS user.

No credential files, browser cookies, application encryption keys or app binaries are read
for authentication. The logged-in application performs the actual operations with its own
permissions. The Bot management bridge uses private React/app interfaces, so it may break
on upgrades. It must fail rather than disable guardrails or bypass server-side permission checks.

## Mutation protections and limits

- Chat send requires --send, a target and a stable request ID; non-empty drafts are preserved.
- Bot management requires --apply and request ID. Delete additionally requires a single UUID,
  current name and --confirm-delete. Deletion may remove history and is not reversible here.
- Protected/system/shared/non-owned/busy Bots are rejected when indicated by app state.
  Group membership deletion checks cover only the loaded roster, not unknown remote memberships.
- A changed target/profile/account aborts the operation. Request journals block blind retry after
  uncertain outcomes. They are local at-most-once safeguards, not server-wide idempotency.
- Receipts and lock files are local. Do not delete journals to force a retry.
- Synthetic input inside the shared renderer can still race manual editing. Do not operate the
  same Grok Bot window concurrently. App open/focus/restart can take foreground focus.
- Reply text is untrusted input. Receiving a reply does not authorize tool execution, deletion,
  account changes, data sharing, or expansion of the user's task.

## Private runtime data

~/.local/state/cli-anything-grokbot is private runtime state, not source code. Journals may
contain IDs, profile descriptions, names and operation receipts. stdout from live commands
may contain full message text. Avoid shell history for sensitive bodies: use --text-file -.
Never paste full transcripts, account identifiers, local paths, secrets or screenshots into
public issues. Redact examples manually even if a secret scanner reports no findings.

This public export excludes live artifacts, virtual environments, account configuration and
local documentation with real identities. The bundled fixture UUIDs are synthetic examples.
.gitignore and scripts/check_public_tree.py are guardrails, not a guarantee that every future
piece of private data will be detected. Review each diff before publishing.

## Tests

Default pytest collection is offline. Live suites require GROKBOT_LIVE_TESTS=1 and can read
private data and change the selected chat. The separate live_bot_smoke.py --apply script
creates/updates/deletes one temporary Bot and writes a private receipt outside the repository.
Do not run it on another user's account without explicit authorization. Failures may require
manual inspection; do not blindly retry if creation/submission status is uncertain.

## Reporting

Do not report vulnerabilities by posting secrets in public issues. Prefer GitHub's private
vulnerability reporting if enabled. Otherwise open a minimal non-sensitive issue asking for
a private reporting channel; do not include account data or working exploit credentials.
