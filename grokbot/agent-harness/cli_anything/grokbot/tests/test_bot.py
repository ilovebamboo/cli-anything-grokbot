"""No live mutations. Tests management policy and local request journals."""
import copy
import json
import subprocess
import pytest
from cli_anything.grokbot.utils.bot_control import (
    BotControl, ManagementJournal, guard, profile_fields, BRIDGE)
from cli_anything.grokbot.utils.cdp import ControlError

MAIN='00000000-0000-4000-8000-000000000001'
BOT='00000000-0000-4000-8000-000000000002'
ROW={'id':BOT,'name':'Test','description':'old','title':'label','isGroup':False,'memberIds':[]}
STATE={'ready':True,'mainId':MAIN,'bots':[ROW],'scope':'app-client-roster'}


def test_profile_supported_fields():
    assert profile_fields(name='A',create=True)=={'name':'A','description':'','title':''}
    assert profile_fields(description='')=={'description':''}


@pytest.mark.parametrize('kwargs',[{}, {'name':''},{'name':' x'}, {'name':'a'*121},
    {'description':'x'*20001},{'title':'a\0b'},{'title':8}])
def test_profile_invalid(kwargs):
    with pytest.raises(ControlError):profile_fields(**kwargs)


@pytest.mark.parametrize('patch',[
    {'isGroup':True}, {'isTeamDefault':True}, {'purpose':'disk-saver'},
    {'viewerIsOwner':False}, {'viewerCanManage':False}, {'visibility':'team'},
    {'published':True},{'isRunning':True},{'isRunningTurn':True},{'isComposingMessage':True}])
def test_protected_bot(patch):
    state=copy.deepcopy(STATE);state['bots'][0].update(patch)
    with pytest.raises(ControlError):guard(state,BOT)


def test_main_unknown_roster_and_name_refused():
    for state, target in [(dict(STATE,mainId=BOT),BOT),(dict(STATE,ready=False),BOT),
                          (dict(STATE,mainId=None),BOT),(STATE,'Test')]:
        with pytest.raises(ControlError):guard(state,target)


def test_delete_confirmation_and_group_membership():
    with pytest.raises(ControlError):guard(STATE,BOT,delete=True)
    with pytest.raises(ControlError):guard(STATE,BOT,delete=True,confirm_name='WRONG',confirm_delete=True)
    assert guard(STATE,BOT,delete=True,confirm_name='Test',confirm_delete=True)==ROW
    state=copy.deepcopy(STATE);state['bots'].append({'id':'g','isGroup':True,'memberIds':[BOT]})
    with pytest.raises(ControlError,match='belongs to a group'):
        guard(state,BOT,delete=True,confirm_name='Test',confirm_delete=True)


class FakeCDP:
    def __init__(self):self.ops=[];self.state=copy.deepcopy(STATE)
    def evaluate(self,expression,timeout=15):
        assert timeout==45
        op,args=json.loads('['+expression.split('return grokbotManage(')[-1].removesuffix(');})()')+']')
        self.ops.append(op)
        if op=='list':return copy.deepcopy(self.state)
        if op=='refresh':return {'requested':True}
        if op=='create':
            row={**ROW,**args['profile'],'id':args['nonce']};self.state['bots'].append(row)
            return {'acknowledged':True,'bot':row}
        if op=='update':
            self.state['bots'][0].update(args['profile']);return {'acknowledged':True,'id':BOT}
        if op=='delete':self.state['bots']=[];return {'acknowledged':True,'id':BOT}
        raise AssertionError(op)
    def close(self):pass


@pytest.mark.parametrize('op',['create','update','delete'])
def test_mutations_default_read_only(op,tmp_path):
    cdp=FakeCDP();c=BotControl(transport=cdp,root=tmp_path)
    r=c.mutate(op,bot_id=BOT if op!='create' else None,profile={'name':'Unique'} if op!='delete' else None)
    assert r['dry_run'] and cdp.ops==['list']
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('op',['create','update','delete'])
def test_apply_requires_request_id(op,tmp_path):
    cdp=FakeCDP();c=BotControl(transport=cdp,root=tmp_path)
    with pytest.raises(ControlError,match='request-id'):
        c.mutate(op,bot_id=BOT if op!='create' else None,profile={'name':'Unique'} if op!='delete' else None,apply=True)
    assert cdp.ops==[]


def test_duplicate_create_and_no_delete_confirmation(tmp_path):
    cdp=FakeCDP();c=BotControl(transport=cdp,root=tmp_path)
    with pytest.raises(ControlError,match='already exists'):c.mutate('create',profile={'name':'Test'})
    with pytest.raises(ControlError,match='confirm-name'):
        c.mutate('delete',bot_id=BOT,apply=True,request_id='no-confirm')
    assert set(cdp.ops)=={'list'}


@pytest.mark.parametrize('op',['create','update','delete'])
def test_rpc_readback_and_idempotency(op,tmp_path):
    cdp=FakeCDP();c=BotControl(transport=cdp,root=tmp_path)
    kwargs={'bot_id':BOT if op!='create' else None,'profile':{'name':'Unique'} if op!='delete' else None,
            'apply':True,'request_id':op,'confirm_name':'Test','confirm_delete':True}
    first=c.mutate(op,**kwargs)
    assert first['verified'] and cdp.ops.count(op)==1
    second=c.mutate(op,**kwargs)
    assert second['reused'] and cdp.ops.count(op)==1
    if op=='update':assert first['after']['description']=='old'


def test_uncertain_no_automatic_repeat(tmp_path):
    cdp=FakeCDP();c=BotControl(transport=cdp,root=tmp_path)
    real=c.action
    def fail(op,**kw):
        if op=='create':raise ControlError('timeout')
        return real(op,**kw)
    c.action=fail
    with pytest.raises(ControlError,match='uncertain'):
        c.mutate('create',profile={'name':'Unique'},apply=True,request_id='attempt')
    with pytest.raises(ControlError,match='Automatic resend is blocked'):
        c.mutate('create',profile={'name':'Unique'},apply=True,request_id='attempt')


def test_management_journal_account_and_payload_conflicts(tmp_path):
    j=ManagementJournal('req',MAIN,'create',{'name':'A'},tmp_path)
    j.save('verified',{'verified':True,'id':BOT})
    assert j.path.stat().st_mode&0o777==0o600
    assert j.path.name=='manage-req.json'
    for account,op in [('another-account','create'),(MAIN,'delete')]:
        with pytest.raises(ControlError):ManagementJournal('req',account,op,{'name':'A'},tmp_path).check()


def test_js_guard_and_response_shapes():
    fixture=r'''
const assert=require('node:assert/strict');
const row={id:'bot',name:'Test',description:'',title:'',isGroup:false,memberIds:[]};
const state={ready:true,mainId:'main',bots:[row]};
const args={id:'bot',mainId:'main',expected:{name:'Test',description:'',title:''},confirmName:'Test',confirmDelete:true};
assert.equal(managementGuard(state,args,'delete').id,'bot');
assert.throws(()=>managementGuard(state,{...args,expected:{name:'wrong'}},'update'),/Profile changed/);
assert.throws(()=>managementGuard(state,{...args,confirmName:'wrong'},'delete'),/confirmation/);
assert.throws(()=>managementGuard(state,{...args,mainId:'other'},'delete'),/Account/);
assert.throws(()=>validateProfile({model:'foo'}),/Unsupported/);
let calls=0;
let result={};
const client={mainAgent:{snapshots:{get:()=>({status:'ready',value:{agentId:'main'}})}},
 roster:{snapshots:{get:()=>({agents:{rows:[row]},hasCompleteRoster:true,hasCompleteTemporalRoster:true,isShowingRestoredRoster:false,loadState:'ready'})},
 createAgent:()=>{},updateAgent:()=>{},deleteAgents:async ids=>{assert.deepEqual(ids,['bot']);calls++;return result;}}};
const anchor={'__reactFiber$test':{memoizedProps:{value:client}}};
global.document={querySelector:()=>anchor};
(async()=>{
 const r=await grokbotManage('delete',args);assert.equal(r.acknowledged,true); // absent lists mean empty
 result={refusedAgentIds:['bot']};await assert.rejects(()=>grokbotManage('delete',args),/refused/);
 result={failedAgentIds:['bot']};await assert.rejects(()=>grokbotManage('delete',args),/failed/);
 result=null;await assert.rejects(()=>grokbotManage('delete',args),/Unrecognized/);
 const before=calls;await assert.rejects(()=>grokbotManage('delete',{...args,confirmDelete:false}),/confirmation/);
 assert.equal(calls,before);
})().catch(e=>{console.error(e);process.exit(1)});
'''
    subprocess.run(['node','-e',BRIDGE+fixture],capture_output=True,check=True)
