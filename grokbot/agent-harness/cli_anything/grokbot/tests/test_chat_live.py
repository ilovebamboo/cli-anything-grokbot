"""Read-only live CDP tests against the installed CLI; no messages submitted."""
import json
import os
from pathlib import Path
import shutil
import subprocess


def _resolve_cli(name):
    path=shutil.which(name)
    if not path: raise RuntimeError(f'Install {name} before live tests')
    return [path]


CLI=_resolve_cli('cli-anything-grokbot')


def run(*args):
    result=subprocess.run(CLI+['--json',*args],capture_output=True,text=True,check=True,timeout=25)
    return json.loads(result.stdout)


def test_live_chat_list_and_groups():
    data=run('chat','list')
    assert data['total']>0
    assert any(c['kind']=='group' for c in data['chats'])
    assert any(c['kind']=='bot' for c in data['chats'])
    assert len({c['id'] for c in data['chats']})==len(data['chats'])


def test_live_dry_run_does_not_navigate_or_modify_draft():
    before=run('chat','list')
    target=next(c for c in before['chats'] if not c['active'])
    plan=run('chat','send','--to',target['id'],'--text','never submitted')
    after=run('chat','list')
    assert plan['dry_run']
    assert before['current']==after['current']


def test_live_switch_bot_group_read_and_restore():
    before=run('chat','list')
    original=before['current']['id']
    try:
        for kind in ('bot','group'):
            target=next(c for c in before['chats'] if c['kind']==kind)
            opened=run('chat','open',target['id'])
            assert opened['verified'] and opened['id']==target['id']
            data=run('chat','read','--limit','2','--latest')
            assert data['id']==target['id'] and isinstance(data['messages'],list)
    finally:
        if original: run('chat','open',original)


def test_live_management_list_and_dry_run():
    roster=run('bot','list')
    assert roster['ready'] and roster['mainId']
    assert any(b['id']==roster['mainId'] for b in roster['bots'])
    before=run('chat','list')['current']
    plan=run('bot','create','--name','CLI_DRY_RUN_NOT_CREATED_EXAMPLE','--description','dry-run')
    assert plan['dry_run']
    after=run('bot','list')
    assert {b['id'] for b in roster['bots']}=={b['id'] for b in after['bots']}
    assert run('chat','list')['current']==before


def test_live_main_bot_delete_blocked():
    main=run('bot','list')['mainId']
    result=subprocess.run(CLI+['--json','bot','delete','--id',main],
                          capture_output=True,text=True,timeout=20)
    assert result.returncode!=0
    assert 'Protected/system' in json.loads(result.stdout)['error']


def test_live_unknown_name_json_error():
    result=subprocess.run(CLI+['--json','chat','open','nonexistent-gbcli-chat-xx'],
                          capture_output=True,text=True,timeout=20)
    assert result.returncode!=0
    assert json.loads(result.stdout)['ok'] is False
