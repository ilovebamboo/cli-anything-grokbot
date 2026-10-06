#!/usr/bin/env python3
"""Check staged public files without printing matched private/secret values.
Not a comprehensive secret detector: also run gitleaks and review the diff.
"""
import re
import subprocess
import sys
from pathlib import PurePosixPath

UUID = re.compile(r'(?i)\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b')
SYNTHETIC = {'00000000-0000-4000-8000-000000000001', '00000000-0000-4000-8000-000000000002'}
RULES = {
    'personal-home-path': re.compile(r'/(?:Users|home)/[A-Za-z0-9_.-]+/'),
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'github-token': re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})'),
    'bearer-value': re.compile(r'(?i)Bearer\s+[A-Za-z0-9_./+=-]{24,}'),
    'email-address': re.compile(r'[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),
}
BLOCK_PARTS={'.venv','venv','__pycache__','.pytest_cache','.pi','.claude',
             'artifacts','private','state','logs'}
BLOCK_SUFFIX={'.png','.jpg','.jpeg','.webp','.sqlite','.db','.log','.pem','.key','.p12','.pfx','.asar','.zip','.tar','.gz'}

def main():
    files=subprocess.check_output(['git','ls-files','--stage','-z']).split(b'\0')
    failures=[];count=0
    for record in files:
        if not record:continue
        meta,name=record.split(b'\t',1)
        mode,oid,stage=meta.decode().split()
        path=name.decode();p=PurePosixPath(path);count+=1
        if mode!='100644' and mode!='100755':failures.append((path,'non-regular-file'))
        if any(part in BLOCK_PARTS or part.endswith('.egg-info') for part in p.parts):
            failures.append((path,'private/build-directory'))
        if p.suffix in BLOCK_SUFFIX or p.name.startswith(('.env','LIVE-','send-','manage-')):
            failures.append((path,'private/artifact-filename'))
        data=subprocess.check_output(['git','cat-file','blob',oid])
        if len(data)>300000 or b'\0' in data:
            failures.append((path,'unexpected-large/binary-file'));continue
        try:text=data.decode('utf-8')
        except UnicodeError:
            failures.append((path,'non-utf8'));continue
        for rule,pattern in RULES.items():
            if pattern.search(text):failures.append((path,rule))
        if any(m.group().lower() not in SYNTHETIC for m in UUID.finditer(text)):
            failures.append((path,'non-synthetic-uuid'))
    for path,rule in failures:print(f'{path}: {rule}')
    print(f'Public-tree audit: {count} indexed files, {len(failures)} findings (values redacted)')
    return bool(failures)

if __name__=='__main__':sys.exit(main())
