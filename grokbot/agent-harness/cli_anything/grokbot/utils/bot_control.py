"""Guarded single-Bot management using the application's existing client methods."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import time
import uuid

from cli_anything.grokbot.utils.cdp import CDP, ControlError
from cli_anything.grokbot.utils.chat_control import Journal, STATE_DIR

BRIDGE=Path(__file__).with_name('bot_bridge.js').read_text()
ID_RE=re.compile(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}')


def profile_fields(name=None, description=None, title=None, create=False):
    fields={k:v for k,v in {'name':name,'description':description,'title':title}.items() if v is not None}
    limits={'name':120,'description':20000,'title':120}
    for key,value in fields.items():
        if not isinstance(value,str) or len(value)>limits[key] or '\0' in value:
            raise ControlError(f'Invalid {key}; maximum {limits[key]} characters')
    if 'name' in fields and (not fields['name'].strip() or fields['name']!=fields['name'].strip()):
        raise ControlError('Name must be non-empty with no leading/trailing whitespace')
    if create:
        if 'name' not in fields: raise ControlError('Name required')
        fields.setdefault('description','');fields.setdefault('title','')
    if not fields: raise ControlError('Provide at least one profile field')
    return fields


def profile_of(row):
    return {k:row.get(k) for k in ('name','description','title')}


def guard(state, bot_id=None, delete=False, confirm_name=None, confirm_delete=False):
    if not state.get('ready') or not state.get('mainId'):
        raise ControlError('Roster/main Bot not ready; mutations disabled')
    if bot_id is None: return None
    if not ID_RE.fullmatch(bot_id): raise ControlError('Management mutations require an exact UUID, not a name')
    row=next((b for b in state['bots'] if b['id']==bot_id),None)
    if not row: raise ControlError('Bot not found; use bot list')
    if row['id']==state['mainId'] or row.get('isTeamDefault') or row.get('purpose'):
        raise ControlError('Protected/system Bot')
    if row.get('isGroup'): raise ControlError('bot management does not support groups')
    if row.get('viewerIsOwner') is False or row.get('viewerCanManage') is False or row.get('visibility')=='team' or row.get('published'):
        raise ControlError('Shared/non-owned Bot management is disabled')
    if any(row.get(k) for k in ('isRunning','isRunningTurn','isComposingMessage')):
        raise ControlError('Bot is busy; wait until idle')
    if delete:
        if confirm_name!=row['name'] or not confirm_delete:
            raise ControlError('Deletion requires exact --confirm-name and --confirm-delete')
        if any(b.get('isGroup') and bot_id in (b.get('memberIds') or []) for b in state['bots']):
            raise ControlError('Bot belongs to a group; deletion is disabled')
    return row


class ManagementJournal(Journal):
    def __init__(self, request_id, main_id, operation, args, root=STATE_DIR):
        payload=json.dumps({'op':operation,'args':args},ensure_ascii=False,sort_keys=True)
        super().__init__(request_id,main_id,payload,root)
        self.path=Path(root)/f'manage-{request_id}.json'


class BotControl:
    def __init__(self, port=9337, transport=None, root=STATE_DIR):
        self.cdp=transport or CDP(port)
        self.root=Path(root)

    def action(self, op, **args):
        return self.cdp.evaluate('(() => {'+BRIDGE+'\nreturn grokbotManage('+json.dumps(op)+','+
                                 json.dumps(args,ensure_ascii=False)+');})()', timeout=45)

    def list(self): return self.action('list')

    def info(self, selector):
        state=self.list()
        matches=[b for b in state['bots'] if b['id']==selector]
        if not matches: matches=[b for b in state['bots'] if b['name']==selector]
        if len(matches)!=1:raise ControlError('Expected one exact Bot name or ID; use bot list')
        return {'bot':matches[0],'mainId':state['mainId'],'ready':state['ready'],'scope':state['scope']}

    def verify(self, op, target_id, profile, main_id, timeout=12):
        # Refresh the app roster, not just the optimistic view. RPC completion is
        # separately required, because absence alone can be a client-side tombstone.
        self.action('refresh')
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            state=self.list()
            if state.get('mainId')!=main_id: raise ControlError('Account changed during verification')
            row=next((b for b in state['bots'] if b['id']==target_id),None)
            if state.get('ready'):
                if op=='delete' and row is None:return None
                if op!='delete' and row and all(row.get(k)==v for k,v in profile.items()):return row
            time.sleep(.2)
        raise ControlError('RPC returned but roster verification timed out')

    def mutate(self, op, profile=None, bot_id=None, apply=False, request_id=None,
               confirm_name=None, confirm_delete=False):
        if op not in ('create','update','delete'):raise ControlError('Unsupported operation')
        if op in ('create','update'):
            profile=profile_fields(**(profile or {}),create=op=='create')
        else: profile={}
        if op!='create' and (not isinstance(bot_id,str) or not ID_RE.fullmatch(bot_id)):
            raise ControlError('Management mutations require an exact UUID, not a name')
        if apply and not request_id: raise ControlError('Applying a mutation requires --request-id')
        state=self.list()
        if not state.get('ready') or not state.get('mainId'):raise ControlError('Roster/main Bot not ready')
        params={'id':bot_id,'profile':profile,'confirmName':confirm_name,'confirmDelete':confirm_delete}
        journal=None
        if apply:
            journal=ManagementJournal(request_id,state['mainId'],op,params,self.root)
            cached=journal.check()
            if cached:return {**cached,'reused':True}
        # Dry-run delete previews the target without demanding the execute confirmation.
        row=guard(state,bot_id,delete=op=='delete',
                  confirm_name=confirm_name if apply else next((b['name'] for b in state['bots'] if b['id']==bot_id),None),
                  confirm_delete=confirm_delete if apply else True)
        if op=='create' and any(b['name']==profile['name'] for b in state['bots']):
            raise ControlError('Bot name already exists; choose a unique name')
        plan={'operation':op,'dry_run':not apply,'target':row,'profile':profile,
              'warning':'Deletion may remove conversation history; not a recoverable backup.' if op=='delete'
                        else 'Name/description/title are profile fields, not model or system-prompt configuration.'}
        if not apply:return plan
        args={**params,'mainId':state['mainId'],'expected':profile_of(row) if row else None}
        if op=='create':
            args['nonce']=str(uuid.uuid5(uuid.NAMESPACE_URL,'grokbot:'+state['mainId']+':'+request_id))
        # Store the pre-change profile receipt before RPC, outside chat-send journals.
        journal.save('attempted', {'operation':op,'before':row,'requested_profile':profile})
        ack=None
        try:
            ack=self.action(op,**args)
            if not ack or ack.get('acknowledged') is not True:raise ControlError('No RPC acknowledgement')
            target_id=ack['bot']['id'] if op=='create' else bot_id
            desired={**(profile_of(row) if row else {}),**profile}
            after=self.verify(op,target_id,desired,state['mainId'])
            result={'operation':op,'verified':True,'verification':'app-rpc-ack-and-refreshed-roster',
                    'request_id':request_id,'id':target_id,'before':row,'after':after,
                    'receipt':str(journal.path)}
            journal.save('verified',result)
            return result
        except Exception as e:
            journal.save('uncertain',{'operation':op,'before':row,'rpc_ack':ack})
            raise ControlError(f'{e}; management request {request_id} is uncertain. Inspect bot list/info; do not repeat under a new ID.') from e

    def __enter__(self):return self
    def __exit__(self,*_):self.cdp.close()
