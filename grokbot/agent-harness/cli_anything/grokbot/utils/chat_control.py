"""Chat operations through the real Electron renderer, guarded and serialized."""
from __future__ import annotations
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
import uuid

from cli_anything.grokbot.utils.cdp import CDP, ControlError

DOM = Path(__file__).with_name('chat_dom.js').read_text()
STATE_DIR = Path.home() / '.local/state/cli-anything-grokbot'


def resolve_chat(chats: list[dict], selector: str) -> dict:
    matches = [c for c in chats if c['id'] == selector]
    if not matches:
        matches = [c for c in chats if c['name'] == selector]
    if len(matches) != 1:
        raise ControlError(f"Expected one exact chat name/ID, found {len(matches)}. Use chat list; no fuzzy matching.")
    return matches[0]


def committed_echo(messages: list[dict], text: str, before: set[str]) -> dict | None:
    return next((m for m in messages if m['role'] == 'user' and m['key'] not in before
                 and m['text'].strip() == text.strip() and m.get('sequence') is not None), None)


def private_state_dir(root: Path) -> None:
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise ControlError('State directory must be an owned real directory, not a symlink')
    os.chmod(root, 0o700)


@contextmanager
def control_lock(root: Path = STATE_DIR):
    private_state_dir(root)
    fd = os.open(root / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a+') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise ControlError('Another Grok Bot CLI operation is running') from e
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


class Journal:
    """A local at-most-once guard, not a claim of server-side idempotency."""
    def __init__(self, request_id: str, chat_id: str, text: str, root: Path = STATE_DIR):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', request_id):
            raise ControlError('request-id must be 1..80 letters/digits/_/-')
        self.path = root / ('send-' + request_id + '.json')
        self.data = {'request_id': request_id, 'chat_id': chat_id,
                     'sha256': hashlib.sha256(text.encode()).hexdigest()}

    def check(self) -> dict | None:
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ControlError('Cannot safely read request journal') from exc
        with os.fdopen(fd, 'r') as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                raise ControlError('Request journal must be an owned regular file')
            try:
                saved = json.load(handle)
            except (ValueError, UnicodeError) as exc:
                raise ControlError('Invalid request journal; inspect locally, do not blindly retry') from exc
        if not isinstance(saved, dict):
            raise ControlError('Invalid request journal object')
        if any(saved.get(k) != v for k,v in self.data.items()):
            raise ControlError('request-id already used for a different target/message')
        if saved.get('state') == 'verified': return saved['result']
        raise ControlError(f"Previous request {self.data['request_id']} is {saved.get('state')}; "
                           'inspect chat before retrying. Automatic resend is blocked.')

    def save(self, state: str, result: dict | None = None):
        private_state_dir(self.path.parent)
        temp = self.path.with_name(self.path.name + '.' + uuid.uuid4().hex)
        payload = {**self.data, 'state': state, 'updated': time.time()}
        if result: payload['result'] = result
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as handle:
            json.dump(payload, handle, ensure_ascii=False)
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temp, self.path)


class ChatControl:
    def __init__(self, port=9337, transport=None):
        self.cdp = transport or CDP(port)

    def action(self, operation, **args):
        return self.cdp.evaluate('(() => {' + DOM + '\nreturn grokbotAction(' +
                                 json.dumps(operation) + ',' + json.dumps(args, ensure_ascii=False) + ');})()')

    def list(self): return self.action('list')

    def target(self, selector): return resolve_chat(self.list()['chats'], selector)

    def wait_state(self, target, timeout=12):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            state = self.action('state')
            if state['id'] == target['id'] and state['name'] == target['name'] and state['composer']:
                return state
            time.sleep(.15)
        raise ControlError('Target did not become ready; no message sent')

    def open_target(self, target):
        self.action('open', **target)
        state = self.wait_state(target)
        return {**state, 'verified': True}

    def open(self, selector): return self.open_target(self.target(selector))

    def read(self, selector=None, limit=20, latest=False):
        if not 1 <= limit <= 500: raise ControlError('limit must be 1..500')
        if selector:
            target = self.target(selector)
            self.open_target(target)
        else:
            state = self.action('state')
            if not state['id']: raise ControlError('No unique open chat')
            target = {'id': state['id'], 'name': state['name']}
        if latest:
            self.action('latest', **target)
            time.sleep(.3)
        result = self.action('read', **target)
        result['messages'] = result['messages'][-limit:]
        return result

    def send(self, selector, text, deliver=False, request_id=None, timeout=20):
        if not text or not text.strip() or len(text) > 20000:
            raise ControlError('Message must contain 1..20000 characters')
        text = text.replace('\r\n','\n')
        target = self.target(selector)
        if not deliver:
            return {'dry_run': True, 'target': target, 'characters': len(text),
                    'note': 'No navigation, typing or send. Use --send and --request-id to deliver.'}
        if not request_id:
            raise ControlError('Actual sends require --request-id so retries cannot silently duplicate messages')
        journal = Journal(request_id, target['id'], text)
        cached = journal.check()
        if cached: return {**cached, 'reused': True}
        state = self.open_target(target)
        if state['draft']:
            raise ControlError('Existing draft in target chat. Refusing to overwrite or append.')
        self.action('latest', **target)
        time.sleep(.25)
        before = {m['key'] for m in self.action('read', **target)['messages']}
        self.action('prepare', **target)
        journal.save('preparing')
        submitted = False
        try:
            self.cdp.call('Input.insertText', {'text': text})
            end = time.monotonic() + 5
            while time.monotonic() < end:
                state = self.action('draft', **target)
                if state['draft'] == text.strip(): break
                time.sleep(.1)
            else: raise ControlError('Draft readback mismatch; not submitted')
            # Persist uncertainty BEFORE clicking; a dropped response must not cause a duplicate.
            journal.save('submission-attempted')
            submitted = True
            self.action('submit', **target, text=text)
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                observed = self.action('read', **target)
                echo = committed_echo(observed['messages'], text, before)
                if echo:
                    result = {'verified': True, 'verification': 'new-user-row-with-transcript-sequence',
                              'request_id': request_id, 'target': target,
                              'message_key': echo['key'], 'sequence': echo['sequence'],
                              'note': 'Verified in app transcript; not proof that the bot finished the task.'}
                    journal.save('verified', result)
                    return result
                time.sleep(.3)
            raise ControlError('No committed user message observed before timeout')
        except Exception as e:
            journal.save('uncertain' if submitted else 'draft-only')
            raise ControlError(f'{e}; request-id={request_id}. Do not resend blindly; inspect chat.') from e

    def wait_reply(self, selector, after: int, timeout=30):
        target = self.target(selector)
        self.open_target(target)
        self.action('latest', **target)
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            result = self.action('read', **target)
            replies = [m for m in result['messages'] if m['role'] == 'assistant'
                       and m.get('sequence') is not None and m['sequence'] > after]
            if replies: return {'target': target, 'messages': replies, 'task_complete': False}
            time.sleep(.5)
        raise ControlError('No assistant reply observed before timeout; message may still be processing')

    def __enter__(self): return self
    def __exit__(self, *_): self.cdp.close()
