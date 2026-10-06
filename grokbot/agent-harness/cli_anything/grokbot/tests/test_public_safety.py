"""Additional filesystem protection checks for the public package."""
import os
from pathlib import Path
import pytest
from cli_anything.grokbot.utils.cdp import ControlError
from cli_anything.grokbot.utils.chat_control import Journal, private_state_dir


def test_state_directory_symlink_refused(tmp_path):
    real=tmp_path/'real';real.mkdir()
    link=tmp_path/'link';link.symlink_to(real,target_is_directory=True)
    with pytest.raises(ControlError):private_state_dir(link)


def test_state_directory_private_permissions(tmp_path):
    root=tmp_path/'state';root.mkdir(mode=0o755)
    private_state_dir(root)
    assert root.stat().st_mode&0o777==0o700


def test_journal_symlink_refused(tmp_path):
    other=tmp_path/'other';other.write_text('{}')
    journal=Journal('req','bot','hello',tmp_path)
    journal.path.symlink_to(other)
    with pytest.raises(ControlError):journal.check()


def test_journal_invalid_json_refused(tmp_path):
    journal=Journal('req','bot','hello',tmp_path)
    journal.path.write_text('not json')
    with pytest.raises(ControlError):journal.check()


def test_journal_array_refused(tmp_path):
    journal=Journal('req','bot','hello',tmp_path)
    journal.path.write_text('[]')
    with pytest.raises(ControlError):journal.check()
