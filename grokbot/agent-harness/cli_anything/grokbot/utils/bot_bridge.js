// Grok Bot 0.66.x private SandClient bridge. Read only the known provider's roster.
// No credentials, token files, generic eval RPC, or stealing coordinatorPort.
function grokbotClient() {
  const anchor=document.querySelector('main');
  const key=anchor && Object.keys(anchor).find(k=>k.startsWith('__reactFiber$'));
  let fiber=key?anchor[key]:null;
  const found=new Set();
  for(let i=0;fiber && i<120;i++,fiber=fiber.return) {
    const v=fiber.memoizedProps?.value;
    if(v?.roster?.snapshots?.get && v?.roster?.createAgent && v?.roster?.updateAgent &&
       v?.roster?.deleteAgents && v?.mainAgent?.snapshots?.get) found.add(v);
  }
  if(found.size!==1) throw Error('Unsupported Grok Bot client shape; management disabled');
  return [...found][0];
}
function botView(row) {
  const fields=['id','name','description','title','isGroup','isRunning','isRunningTurn',
    'isComposingMessage','isHiddenFromSidebar','harness','origin','purpose','visibility',
    'published','viewerIsOwner','viewerCanManage','isTeamDefault','memberIds','serverId'];
  return Object.fromEntries(fields.map(k=>[k,row[k]??null]));
}
function botState(client) {
  const s=client.roster.snapshots.get();
  const main=client.mainAgent.snapshots.get();
  if(!Array.isArray(s.agents?.rows)) throw Error('Unrecognized roster data');
  return {bots:s.agents.rows.map(botView),mainId:main?.status==='ready'?main.value?.agentId:null,
    ready:s.hasCompleteRoster===true && s.hasCompleteTemporalRoster===true &&
      s.isShowingRestoredRoster===false && s.loadState==='ready' && !s.isResyncing,
    scope:'app-client-roster'};
}
function validateProfile(profile, create=false) {
  if(!profile || typeof profile!=='object' || Array.isArray(profile)) throw Error('Invalid profile');
  const limits={name:120,description:20000,title:120};
  for(const [k,v] of Object.entries(profile)) {
    if(!Object.hasOwn(limits,k)||typeof v!=='string'||v.length>limits[k]||v.includes('\0'))
      throw Error('Unsupported profile field/value');
    if(k==='name'&&!v.trim()) throw Error('Name cannot be blank');
  }
  if(create && !profile.name) throw Error('Name required');
}
function managementGuard(state, args, op) {
  if(!state.ready || !state.mainId) throw Error('Roster/main Bot not ready; mutations disabled');
  if(args.mainId!==state.mainId) throw Error('Account/main Bot changed; refusing mutation');
  if(op==='create') {
    validateProfile(args.profile,true);
    if(state.bots.some(b=>b.name===args.profile.name)) throw Error('Bot name already exists');
    return null;
  }
  const row=state.bots.find(b=>b.id===args.id);
  if(!row) throw Error('Bot no longer exists');
  if(row.id===state.mainId||row.isTeamDefault||row.purpose) throw Error('Protected/system Bot');
  if(row.isGroup) throw Error('This command does not manage groups');
  if(row.viewerIsOwner===false||row.viewerCanManage===false||row.visibility==='team'||row.published)
    throw Error('Shared/non-owned Bot management is disabled');
  if(row.isRunning||row.isRunningTurn||row.isComposingMessage) throw Error('Bot is busy; wait until idle');
  const current={name:row.name,description:row.description,title:row.title};
  if(JSON.stringify(current)!==JSON.stringify(args.expected)) throw Error('Profile changed; inspect and retry');
  if(op==='update') validateProfile(args.profile);
  if(op==='delete') {
    if(args.confirmName!==row.name||args.confirmDelete!==true) throw Error('Delete confirmation mismatch');
    if(state.bots.some(b=>b.isGroup&&(b.memberIds||[]).includes(row.id)))
      throw Error('Bot belongs to a group; deletion is disabled');
  }
  return row;
}
async function grokbotManage(op,args) {
  const client=grokbotClient();
  const state=botState(client);
  if(op==='list') return state;
  if(op==='refresh') { client.roster.retry(); return {requested:true}; }
  if(!['create','update','delete'].includes(op)) throw Error('Unsupported management operation');
  managementGuard(state,args,op);
  if(op!=='create') {
    const active=document.querySelector('button[data-agent-id][data-active="true"]');
    if(active?.dataset?.agentId===args.id) {
      const draft=document.querySelector('main .sand-prompt-field[contenteditable="true"]')?.innerText?.trim();
      const editing=document.querySelector('#sand-conversation-details input:not([type="file"]),#sand-conversation-details textarea');
      if(draft || editing) throw Error('Target has a draft or open profile editor; refusing mutation');
    }
  }
  if(op==='create') {
    const result=await client.roster.createAgent({...args.profile,origin:'user',
      clientNonce:args.nonce,isIntroductionSuppressed:true,isKickstartRequested:false});
    if(!result?.agent?.id) throw Error('Create response missing agent ID');
    return {acknowledged:true,bot:botView(result.agent)};
  }
  if(op==='update') {
    await client.roster.updateAgent(args.id,{...args.expected,...args.profile});
    return {acknowledged:true,id:args.id};
  }
  const result=await client.roster.deleteAgents([args.id]);
  if(!result || typeof result!=='object' || Array.isArray(result) ||
     (result.refusedAgentIds!==undefined && !Array.isArray(result.refusedAgentIds)) ||
     (result.failedAgentIds!==undefined && !Array.isArray(result.failedAgentIds)))
    throw Error('Unrecognized delete response; inspect before retrying');
  // The app treats absent lists as empty (its own roster uses ?? []).
  const refused=result.refusedAgentIds??[], failed=result.failedAgentIds??[];
  if(refused.length||failed.length)
    throw Error('Application refused/failed deletion; inspect before retrying');
  return {acknowledged:true,id:args.id,refusedAgentIds:refused,failedAgentIds:failed};
}
