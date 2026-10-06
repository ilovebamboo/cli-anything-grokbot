"""Chat transport and safety tests; never sends a live message."""
import json
from pathlib import Path
import subprocess

import pytest
from cli_anything.grokbot.utils.cdp import ControlError, validate_ws
from cli_anything.grokbot.utils.chat_control import ChatControl, Journal, committed_echo, resolve_chat

CHATS = [dict(id='one',name='Bot A',kind='bot'),dict(id='two',name='Group B',kind='group')]


def test_exact_name_and_id():
    assert resolve_chat(CHATS, 'Bot A')['id'] == 'one'
    assert resolve_chat(CHATS, 'two')['name'] == 'Group B'


@pytest.mark.parametrize('selector', ['Bot','bot a','none',''])
def test_no_fuzzy_or_unknown(selector):
    with pytest.raises(ControlError): resolve_chat(CHATS, selector)


def test_duplicate_name_refused():
    with pytest.raises(ControlError):
        resolve_chat([CHATS[0],dict(CHATS[0],id='other')], 'Bot A')


@pytest.mark.parametrize('url', ['ws://example.com:9337/devtools/page/a',
    'ws://127.0.0.1:9222/devtools/page/a','wss://127.0.0.1:9337/devtools/page/a',
    'ws://user:pass@127.0.0.1:9337/devtools/page/a','ws://127.0.0.1:9337/devtools/browser/a'])
def test_disallow_remote_or_wrong_ws(url):
    with pytest.raises(ControlError): validate_ws(url,9337)


def test_allow_local_page():
    url='ws://127.0.0.1:9337/devtools/page/abc'
    assert validate_ws(url,9337)==url


def test_committed_echo_not_draft_or_old_message():
    row=dict(key='k',role='user',text='hello',sequence=8)
    assert committed_echo([row], 'hello', set())==row
    assert committed_echo([row], 'hello', {'k'}) is None
    assert committed_echo([dict(row,sequence=None)], 'hello', set()) is None
    assert committed_echo([dict(row,role='assistant')], 'hello', set()) is None
    assert committed_echo([dict(row,text='helloworld')], 'hello', set()) is None


@pytest.mark.parametrize('request_id', ['../escape','a/b','','x'*81])
def test_bad_request_id(request_id,tmp_path):
    with pytest.raises(ControlError): Journal(request_id,'one','hello',tmp_path)


def test_journal_verified_idempotency_and_conflict(tmp_path):
    journal=Journal('abc','one','hello',tmp_path)
    assert journal.check() is None
    journal.save('verified',{'verified':True,'sequence':3})
    assert journal.check()['sequence']==3
    assert journal.path.stat().st_mode & 0o777 == 0o600
    assert 'hello' not in journal.path.read_text()
    with pytest.raises(ControlError): Journal('abc','two','hello',tmp_path).check()
    with pytest.raises(ControlError): Journal('abc','one','other text',tmp_path).check()


@pytest.mark.parametrize('state', ['preparing','submission-attempted','draft-only','uncertain'])
def test_never_resend_uncertain(state,tmp_path):
    journal=Journal('abc','one','hello',tmp_path); journal.save(state)
    with pytest.raises(ControlError,match='Automatic resend is blocked'): journal.check()


class NoIO:
    def evaluate(self,*args): raise AssertionError('Unexpected eval')
    def call(self,*args): raise AssertionError('Unexpected send/input')


def test_dry_run_only_lists(monkeypatch):
    c=ChatControl(transport=NoIO())
    monkeypatch.setattr(c,'list',lambda:{'chats':CHATS})
    assert c.send('Bot A','hi')['dry_run'] is True


def test_actual_send_requires_request_id(monkeypatch):
    c=ChatControl(transport=NoIO())
    monkeypatch.setattr(c,'list',lambda:{'chats':CHATS})
    with pytest.raises(ControlError,match='require --request-id'):
        c.send('Bot A','hello',True)


def test_dom_rejects_stale_target_and_voice_button():
    from cli_anything.grokbot.utils.chat_control import DOM
    fixture = r"""
const assert = require('node:assert/strict');
let activeId='wrong'; let label='发起语音聊天'; let clicked=0;
const send={disabled:false,getAttribute:()=>label,click:()=>clicked++};
const form={querySelector:s=>s==='.sand-prompt-send'?send:null};
const editor={innerText:'hello',closest:()=>form};
global.document={
  querySelector:s=>s==='#sand-conversation-heading'?{getAttribute:()=> 'Bot A'}:
      s.includes('sand-prompt-field')?editor:null,
  querySelectorAll:s=>s.includes('data-active')?[{dataset:{agentId:activeId}}]:[],
};
assert.throws(()=>grokbotAction('submit',{id:'one',name:'Bot A',text:'hello'}),/Target changed/);
activeId='one';
assert.throws(()=>grokbotAction('submit',{id:'one',name:'Bot A',text:'hello'}),/not a text-send button/);
label='发送消息';
assert.throws(()=>grokbotAction('submit',{id:'one',name:'Bot A',text:'other'}),/Draft does not match/);
assert.equal(clicked,0);
grokbotAction('submit',{id:'one',name:'Bot A',text:'hello'});
assert.equal(clicked,1);
"""
    subprocess.run(['node','-e',DOM+fixture],check=True,capture_output=True)


def test_existing_draft_refuses_input(monkeypatch,tmp_path):
    monkeypatch.setattr(Journal, 'check', lambda _: None)
    c=ChatControl(transport=NoIO())
    monkeypatch.setattr(c,'list',lambda:{'chats':CHATS})
    monkeypatch.setattr(c,'open_target',lambda t:{'draft':'my draft'})
    with pytest.raises(ControlError,match='Existing draft'):
        c.send('Bot A','hi',True,request_id='test-existing-draft')


def test_cached_send_never_navigates(monkeypatch):
    c=ChatControl(transport=NoIO())
    monkeypatch.setattr(c,'list',lambda:{'chats':CHATS})
    monkeypatch.setattr(Journal,'check',lambda _: {'verified':True,'sequence':10})
    assert c.send('Bot A','hi',True,request_id='cached')['reused']


def test_submit_timeout_no_retry(monkeypatch):
    c=ChatControl(transport=NoIO()); ops=[]; saves=[]
    monkeypatch.setattr(c,'list',lambda:{'chats':CHATS})
    monkeypatch.setattr(c,'open_target',lambda t:{'draft':''})
    monkeypatch.setattr(Journal,'check',lambda _:None)
    monkeypatch.setattr(Journal,'save',lambda self,state,result=None:saves.append(state))
    monkeypatch.setattr(c.cdp,'call',lambda *a:None)
    def action(op,**kw):
        ops.append(op)
        if op=='read':return {'messages':[]}
        if op=='draft':return {'draft':'hi'}
        if op=='submit':raise ControlError('connection lost')
    monkeypatch.setattr(c,'action',action)
    with pytest.raises(ControlError,match='Do not resend blindly'):
        c.send('Bot A','hi',True,request_id='uncertain')
    assert ops.count('submit')==1
    assert saves==['preparing','submission-attempted','uncertain']


def test_name_argument_does_not_collide():
    class Eval:
        def evaluate(self,expr):
            assert '"name": "Bot A"' in expr
            return {'clicked':'one'}
    c=ChatControl(transport=Eval())
    assert c.action('open',id='one',name='Bot A')['clicked']=='one'


def test_js_parses_and_payload_is_data():
    # Syntax-check payload encoding including quotes/newlines, no browser actions.
    class Eval:
        def evaluate(self,expr):
            payload='new Function('+json.dumps('return '+expr)+');'
            subprocess.run(['node','-e',payload],check=True,capture_output=True)
            return True
    assert ChatControl(transport=Eval()).action('submit',id='one',name='Bot A',text='中文"\n${oops}\\')
