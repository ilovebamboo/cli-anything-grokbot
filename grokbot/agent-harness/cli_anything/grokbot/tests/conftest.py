"""Default tests are offline. Live tests must be explicitly selected and enabled."""
import os
import pytest

LIVE_MODULES = {"test_chat_live.py", "test_full_e2e.py"}

def pytest_ignore_collect(collection_path, config):
    if collection_path.name in LIVE_MODULES and os.environ.get("GROKBOT_LIVE_TESTS") != "1":
        return True


def pytest_collection_modifyitems(config, items):
    # Explicitly requesting a live file can bypass ignore_collect; still fail closed.
    if os.environ.get("GROKBOT_LIVE_TESTS") != "1":
        if any(item.path.name in LIVE_MODULES for item in items):
            raise pytest.UsageError("Live tests require GROKBOT_LIVE_TESTS=1 and a signed-in local app")
