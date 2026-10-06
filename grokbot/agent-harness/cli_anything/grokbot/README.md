# cli-anything-grokbot

Experimental macOS CLI for a locally installed, signed-in Grok Bot desktop app.
Uses loopback Electron CDP. Chat commands operate the real shared UI, management
commands call guarded app-owned methods. No mouse injection or credential extraction.

Repository, installation and usage:
https://github.com/ilovebamboo/cli-anything-grokbot

Use --json BEFORE the command group. Start with app connect, chat list, or bot list.
Actual chat delivery requires --send and --request-id. Bot mutations require --apply
and --request-id, deletion additionally needs --confirm-name and --confirm-delete.
Read SECURITY.md before use: localhost CDP grants broad app control to local processes.
Never expose the port, publish transcripts, or run concurrent human/CLI edits.

Source install: python -m venv .venv; .venv/bin/pip install -e '.[dev]'.
Offline tests: .venv/bin/python -m pytest. Live tests require GROKBOT_LIVE_TESTS=1.
Test plan: tests/TEST.md. No official affiliation, public API or full history support.
