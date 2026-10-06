// Executed in the real Grok Bot renderer. Never claims the coordinator port.
// No React-private fields, credentials, gateway emulation or fixed coordinates.
function grokbotAction(action, args) {
  const q = (s, root=document) => root.querySelector(s);
  const qa = (s, root=document) => [...root.querySelectorAll(s)];
  const chatName = e => (e.querySelector('.sand-agent-item__name')?.textContent || e.getAttribute('aria-label') || '').replace(/, (主 Bot|Main Bot)(?:,.*)?$/,'').replace(/, (未读动态|Unread activity)$/,'');
  const editor = () => q('main .sand-prompt-field[contenteditable="true"]');
  const heading = () => q('#sand-conversation-heading')?.getAttribute('aria-label') || null;
  const active = () => {
    const els = qa('button[data-agent-id][data-active="true"]');
    const ids = [...new Set(els.map(e=>e.dataset.agentId))];
    return ids.length===1 ? ids[0] : null;
  };
  const draft = () => editor()?.innerText.replace(/\r\n/g,'\n').trim() || '';
  const assertTarget = () => {
    if(active()!==args.id || heading()!==args.name) throw Error('Target changed or not ready; refusing action');
    if(!editor()) throw Error('Composer unavailable');
  };
  const messages = () => qa('[role="log"] [data-row-key]').flatMap(row => {
    const msg = row.matches('[data-role]') ? row : q('[data-role]',row);
    if(!msg) return [];
    const text = qa('.sand-message-prose',row).map(e=>e.innerText).join('\n').trim();
    if(!text) return [];
    const labelled = row.getAttribute('aria-labelledby') || '';
    const seq = labelled.match(/(?:%40|@)(\d+)(?:-author|-timestamp)/);
    const authorId = labelled.split(' ').find(x=>x.endsWith('-author'));
    return [{key:row.dataset.rowKey, role:msg.dataset.role,
      author:authorId?document.getElementById(authorId)?.textContent:null,
      text, sequence:seq?Number(seq[1]):null,
      timestamp:q('time',row)?.getAttribute('datetime')||q('time',row)?.getAttribute('aria-label')||null}];
  });
  const state = () => ({id:active(),name:heading(),draft:draft(),composer:!!editor()});
  switch(action) {
    case 'list': {
      const seen = new Set();
      const chats = qa('button[data-agent-id]').filter(e=>!seen.has(e.dataset.agentId)&&seen.add(e.dataset.agentId)).map(e=>({
        id:e.dataset.agentId,name:chatName(e),
        kind:q('.sand-group-avatar',e)?'group':'bot',active:e.dataset.active==='true'
      }));
      return {chats, current:state(), scope:'rendered-sidebar', total:chats.length};
    }
    case 'state': return state();
    case 'open': {
      const target=qa('button[data-agent-id]').find(e=>e.dataset.agentId===args.id);
      if(!target || chatName(target)!==args.name) throw Error('Target disappeared; list again');
      target.click(); return {clicked:args.id};
    }
    case 'read': {
      if(args.id) assertTarget();
      return {...state(),scope:'rendered-transcript',messages:messages()};
    }
    case 'latest': {
      assertTarget();
      const log=q('[role="log"]'); if(!log) throw Error('Transcript missing');
      log.scrollTop=log.scrollHeight; return true;
    }
    case 'prepare': {
      assertTarget();
      if(draft()) throw Error('Existing draft; refusing to overwrite it');
      const form=editor().closest('form');
      if(!form || q('[data-kind="attachment"],.sand-prompt-attachment',form)) throw Error('Unrecognized composer or attachments present');
      editor().focus();
      if(document.activeElement!==editor()) throw Error('Composer did not focus');
      return state();
    }
    case 'draft': assertTarget(); return state();
    case 'submit': {
      assertTarget();
      if(draft()!==args.text.trim()) throw Error('Draft does not match intended message; refusing Send');
      const button=q('.sand-prompt-send',editor().closest('form'));
      // This same button is a voice-call control when the composer is empty.
      const label=button?.getAttribute('aria-label')||'';
      if(!button || button.disabled || !/^(发送|发送消息|Send|Send message)$/i.test(label))
        throw Error('Send control not ready (not a text-send button)');
      const before=messages().filter(m=>m.role==='user').map(m=>m.key);
      button.click();
      return {submitted:true,before};
    }
    default: throw Error('Unknown operation');
  }
}
