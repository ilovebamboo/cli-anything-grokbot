"""Explicit live CRUD smoke on one unique temporary Bot. Not collected by pytest.
Run: .venv/bin/python cli_anything/grokbot/tests/live_bot_smoke.py --apply
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid


def run(*args):
    p=subprocess.run([shutil.which('cli-anything-grokbot'),'--json','bot',*args],
                     capture_output=True,text=True,timeout=75)
    if p.returncode:raise RuntimeError(p.stdout or p.stderr)
    return json.loads(p.stdout)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true')
    if not parser.parse_args().apply:parser.error('--apply required: creates, updates and deletes a temporary Bot')
    key='crud-'+uuid.uuid4().hex[:12]
    name='CLI_TEST_'+key
    evidence={'request_prefix':key}
    bot_id=None
    try:
        created=run('create','--name',name,'--description','Temporary CRUD test. No tools or tasks.',
                    '--title','test','--apply','--request-id',key+'-create')
        evidence['create']=created;bot_id=created['id']
        assert created['verified'] and created['after']['name']==name
        reused=run('create','--name',name,'--description','Temporary CRUD test. No tools or tasks.',
                   '--title','test','--apply','--request-id',key+'-create')
        assert reused['reused'] and reused['id']==bot_id
        evidence['create_retry_reused']=True
        updated=run('update','--id',bot_id,'--name',name+'-edited','--description','Updated temporary profile.',
                    '--title','edited','--apply','--request-id',key+'-update')
        evidence['update']=updated
        assert updated['verified'] and updated['after']['description']=='Updated temporary profile.'
        assert updated['after']['title']=='edited'
        info=run('info',bot_id);evidence['info']=info
        assert info['bot']['name']==name+'-edited'
    finally:
        if bot_id:
            current=run('info',bot_id)['bot']
            if not current['name'].startswith(name):raise RuntimeError('Temporary Bot renamed externally; refuse cleanup')
            evidence['delete']=run('delete','--id',bot_id,'--confirm-name',current['name'],
                 '--confirm-delete','--apply','--request-id',key+'-delete')
            assert evidence['delete']['verified']
            assert all(b['id']!=bot_id for b in run('list')['bots'])
            replay=run('delete','--id',bot_id,'--confirm-name',current['name'],
                 '--confirm-delete','--apply','--request-id',key+'-delete')
            assert replay['reused']
            evidence['delete_retry_reused']=True
        out=Path.home()/'.local/state/cli-anything-grokbot'/('LIVE-'+key+'.json')
        out.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
        fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as handle:
            json.dump(evidence,handle,ensure_ascii=False,indent=2)
            handle.write('\n')
        print(str(out))
    print(json.dumps({'verified':True,'id':bot_id,'operations':['create','update','info','delete'],
                      'create_retry_reused':True,'delete_retry_reused':True}))

if __name__=='__main__':main()
