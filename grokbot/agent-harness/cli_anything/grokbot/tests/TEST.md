# Test plan

## Offline default

- Unit tests use synthetic IDs, profiles and chat text. No user-specific fixtures.
- Validate exact target resolution, URL restrictions, input fields, draft safety,
  request-id conflicts, uncertain-result no-retry, mutation guards and JS behavior.
- Node.js executes isolated JavaScript fixtures; no network/app calls are made.
- Plain pytest ignores live modules. Explicitly naming a live module without the
  opt-in environment variable is also rejected. CI only runs the offline suite.

## Explicit live read-only integration

GROKBOT_LIVE_TESTS=1 CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest

Requires the real app, signed-in account, installed CLI and local CDP connection.
Missing dependencies must fail rather than fake success. Live tests read actual
app state, select chats, scroll and run dry-run operations. They do not send chat
messages or create/delete Bots. Do not publish stdout/artifacts without review.

## Separate mutation smoke

live_bot_smoke.py --apply is a standalone, explicitly authorized test. It creates
one uniquely named temporary Bot, verifies profile updates, deletes that ID, and
checks request replay. It writes private evidence under the user's local state
directory, not the repository. Do not blindly rerun after uncertain creation.

Development on Grok Bot 0.66.0 verified a personal-bot message/reply round trip and
individual temporary Bot CRUD. No real IDs, replies or receipts are published.
Group sending and arbitrary app versions are not claimed fully live-tested.

## Privacy checks

Run scripts/check_public_tree.py on staged files and inspect the diff. Secret
scanning supplements, not replaces, review for conversation content and identifiers.

## Public export offline results

The following output intentionally omits local machine paths and interpreter locations.
Live integration suites were not run as part of the public-export validation.

```text
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_profile_supported_fields PASSED [  1%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_profile_invalid[kwargs0] PASSED [  2%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_profile_invalid[kwargs1] PASSED [  4%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_profile_invalid[kwargs2] PASSED [  5%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_profile_invalid[kwargs3] PASSED [  6%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_profile_invalid[kwargs4] PASSED [  8%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_profile_invalid[kwargs5] PASSED [  9%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_profile_invalid[kwargs6] PASSED [ 11%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_protected_bot[patch0] PASSED [ 12%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_protected_bot[patch1] PASSED [ 13%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_protected_bot[patch2] PASSED [ 15%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_protected_bot[patch3] PASSED [ 16%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_protected_bot[patch4] PASSED [ 18%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_protected_bot[patch5] PASSED [ 19%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_protected_bot[patch6] PASSED [ 20%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_protected_bot[patch7] PASSED [ 22%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_protected_bot[patch8] PASSED [ 23%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_protected_bot[patch9] PASSED [ 25%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_main_unknown_roster_and_name_refused PASSED [ 26%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_delete_confirmation_and_group_membership PASSED [ 27%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_mutations_default_read_only[create] PASSED [ 29%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_mutations_default_read_only[update] PASSED [ 30%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_mutations_default_read_only[delete] PASSED [ 31%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_apply_requires_request_id[create] PASSED [ 33%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_apply_requires_request_id[update] PASSED [ 34%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_apply_requires_request_id[delete] PASSED [ 36%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_duplicate_create_and_no_delete_confirmation PASSED [ 37%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_rpc_readback_and_idempotency[create] PASSED [ 38%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_rpc_readback_and_idempotency[update] PASSED [ 40%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_rpc_readback_and_idempotency[delete] PASSED [ 41%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_uncertain_no_automatic_repeat PASSED [ 43%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_management_journal_account_and_payload_conflicts PASSED [ 44%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_bot.py::test_js_guard_and_response_shapes PASSED [ 45%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_exact_name_and_id PASSED [ 47%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_no_fuzzy_or_unknown[Bot] PASSED [ 48%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_no_fuzzy_or_unknown[bot a] PASSED [ 50%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_no_fuzzy_or_unknown[none] PASSED [ 51%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_no_fuzzy_or_unknown[] PASSED [ 52%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_duplicate_name_refused PASSED [ 54%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_disallow_remote_or_wrong_ws[ws://example.com:9337/devtools/page/a] PASSED [ 55%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_disallow_remote_or_wrong_ws[ws://127.0.0.1:9222/devtools/page/a] PASSED [ 56%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_disallow_remote_or_wrong_ws[wss://127.0.0.1:9337/devtools/page/a] PASSED [ 58%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_disallow_remote_or_wrong_ws[ws://user:pass@127.0.0.1:9337/devtools/page/a] PASSED [ 59%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_disallow_remote_or_wrong_ws[ws://127.0.0.1:9337/devtools/browser/a] PASSED [ 61%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_allow_local_page PASSED [ 62%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_committed_echo_not_draft_or_old_message PASSED [ 63%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_bad_request_id[../escape] PASSED [ 65%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_bad_request_id[a/b] PASSED [ 66%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_bad_request_id[] PASSED [ 68%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_bad_request_id[xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx] PASSED [ 69%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_journal_verified_idempotency_and_conflict PASSED [ 70%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_never_resend_uncertain[preparing] PASSED [ 72%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_never_resend_uncertain[submission-attempted] PASSED [ 73%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_never_resend_uncertain[draft-only] PASSED [ 75%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_never_resend_uncertain[uncertain] PASSED [ 76%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_dry_run_only_lists PASSED [ 77%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_actual_send_requires_request_id PASSED [ 79%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_dom_rejects_stale_target_and_voice_button PASSED [ 80%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_existing_draft_refuses_input PASSED [ 81%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_cached_send_never_navigates PASSED [ 83%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_submit_timeout_no_retry PASSED [ 84%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_name_argument_does_not_collide PASSED [ 86%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_chat.py::test_js_parses_and_payload_is_data PASSED [ 87%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_core.py::test_find_app_missing PASSED [ 88%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_core.py::test_url_schemes PASSED [ 90%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_core.py::test_desktop_status_missing PASSED [ 91%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_core.py::test_desktop_status_ignores_non_object PASSED [ 93%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_public_safety.py::test_state_directory_symlink_refused PASSED [ 94%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_public_safety.py::test_state_directory_private_permissions PASSED [ 95%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_public_safety.py::test_journal_symlink_refused PASSED [ 97%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_public_safety.py::test_journal_invalid_json_refused PASSED [ 98%]
grokbot/agent-harness/cli_anything/grokbot/tests/test_public_safety.py::test_journal_array_refused PASSED [100%]
============================== 72 passed in 0.52s ==============================
```

The public suite is smaller than the earlier development suite because real-account
integration tests are now opt-in; additional filesystem safety tests are included.
