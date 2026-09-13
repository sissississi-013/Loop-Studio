'use strict';
const $ = id => document.getElementById(id);
let project = null, selected = null, proposal = null, playingShot = null, lastJobs = new Map(), config = {};
let editChain = Promise.resolve();
const dirty = new Set();
const fileURL = path => `/files/${project.id}/${path}`;
const time = seconds => `${Math.floor(seconds / 60)}:${(seconds % 60).toFixed(1).padStart(4, '0')}`;
function el(tag, text, cls) { const node = document.createElement(tag); if (text != null) node.textContent = text; if (cls) node.className = cls; return node; }
function button(text, action, cls) { const node = el('button', text, cls); node.addEventListener('click', () => safe(action)); return node; }
function message(text) { $('message').textContent = text; $('message').hidden = !text; }
async function safe(action) { try { await action(); } catch (error) { message(error.message || String(error)); } }
async function api(path, data) {
  const response = await fetch(`/api${path}`, data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}
async function refreshProjects() {
  const projects = await api('/projects');
  $('projects').replaceChildren(...projects.map(p => {const option=el('option',p.name); option.value=p.id; return option;}));
  if (project) $('projects').value=project.id;
  return projects;
}
async function openProject(id) {
  await editChain; if(dirty.size) throw new Error('Apply your pending changes before switching projects.'); dirty.clear(); project = await api(`/projects/${id}`); selected=null; proposal=null; playingShot=null;
  localStorage.setItem('loop-project',id); $('viewer').pause(); $('viewer').removeAttribute('src'); $('viewer').load();
  $('viewer').parentElement.classList.remove('has-video'); render(); await refreshProjects();
  const recent=project.exports.at(-1);
  if(recent) showVideo(fileURL(recent.path),project.name,`Version ${recent.version} · rendered ${recent.preview?'preview':'export'}`);
  else if(project.timeline.length) selectShot(project.timeline[0].id);
}
async function reload() { if (!project) return; project=await api(`/projects/${project.id}`); render(); }
function edit(operation) {
  const pending = editChain.then(async () => {
    $('save-state').textContent='Saving…';
    try {
      project=await api(`/projects/${project.id}/edit`,{version:project.version,operation});
      if(operation.op==='settings') {
        if(operation.brief!==undefined) dirty.delete('brief');
        if(operation.name!==undefined) dirty.delete('project-name');
        if(operation.style) for(const id of ['aspect','look','title','title-size','font','title-position','title-background','music','source-volume','music-volume']) dirty.delete(id);
      }
      if(operation.op==='shot') for(const id of ['trim-start','trim-end','shot-volume','shot-caption']) dirty.delete(id);
      render();
    } catch(error) { if(error.message.includes('changed')) await reload(); throw error; }
    finally { $('save-state').textContent=dirty.size?'Unapplied changes':'Saved locally'; }
  });
  editChain=pending.catch(()=>{});
  return pending;
}
function setField(id,value) { if(!dirty.has(id)) $(id).value=value; }

function render() {
  if (!project) return;
  setField('project-name',project.name);
  setField('brief',project.brief);
  for(const [key,id] of Object.entries({aspect:'aspect',look:'look',title:'title',title_size:'title-size',font:'font',title_position:'title-position',music:'music',source_volume:'source-volume',music_volume:'music-volume'})) setField(id,project.style[key]);
  if(!dirty.has('title-background')) $('title-background').checked=project.style.title_background;
  const clips=Object.values(project.assets).filter(a=>a.kind!=='reference');
  $('asset-count').textContent=`${clips.length} / 10`;
  $('assets').replaceChildren(...clips.map(assetCard));
  $('references').replaceChildren(...Object.values(project.assets).filter(a=>a.kind==='reference').map(assetCard));
  $('sample').hidden=Object.keys(project.assets).length>0;
  $('undo').disabled=!project.undo.length; $('redo').disabled=!project.redo.length;
  $('preview').disabled=$('export').disabled=!project.timeline.length;
  $('direct').disabled=$('analyze').disabled=!clips.length;
  $('revise').disabled=!selected;
  $('timeline-duration').textContent=time(project.timeline.reduce((sum,s)=>sum+s.end-s.start,0));
  $('shot-count').textContent=`${project.timeline.length} shots`;
  if(project.timeline.length) $('timeline').replaceChildren(...project.timeline.map((shot,index)=>{
    const asset=project.assets[shot.asset_id];
    const node=button('',()=>selectShot(shot.id),'timeline-shot'+(selected===shot.id?' selected':''));
    node.setAttribute('aria-label',`Shot ${index+1}: ${asset.name}${shot.locked?', locked':''}`);
    const image=el('img'); image.src=fileURL(asset.poster); image.alt='';
    const meta=el('span',null,'shot-meta'); meta.append(el('strong',`${shot.locked?'🔒 ':''}${index+1}. ${asset.name}`),el('span',`${time(shot.start)} → ${time(shot.end)}`));
    node.append(image,meta); return node;
  })); else $('timeline').replaceChildren(el('p','Your story starts here. Add a shot from the footage library.','timeline-empty'));
  renderInspector(); renderExports();
  $('proposal').hidden=!proposal;
}
function assetCard(asset) {
  const node=el('article',null,'asset'), top=el('div',null,'asset-top'), image=el('img');
  image.src=fileURL(asset.poster); image.alt='';
  const info=el('div'); info.append(el('strong',asset.name),el('small',`${time(asset.duration)} · ${asset.width} × ${asset.height}`));
  top.append(image,info); node.append(top);
  const actions=el('div',null,'asset-actions');
  actions.append(button('View',()=>showVideo(fileURL(asset.proxy),asset.name,'Full-duration source proxy')));
  if(asset.kind!=='reference') actions.append(button('+ Add shot',()=>edit({op:'add',asset_id:asset.id,start:0,end:Math.min(asset.duration,5)})));
  const analysis=project.analysis[asset.id];
  if(asset.kind==='reference'&&analysis) actions.append(button('Use color look',()=>edit({op:'settings',style:analysis.reference_style})));
  node.append(actions);
  if(analysis) {
    const details=el('details'), summary=el('summary',analysis.mode==='model'?'Visual notes & moments':'Sampled moments · offline');
    details.append(summary,el('p',analysis.description,'analysis-text'));
    if(analysis.selection_notice) details.append(el('p',analysis.selection_notice,'analysis-text'));
    const contact=el('a','View contact sheet'); contact.href=fileURL(analysis.contact); contact.target='_blank'; contact.rel='noreferrer';details.append(contact);
    if(asset.kind!=='reference') for(const candidate of [...analysis.candidates].sort((a,b)=>b.score-a.score).slice(0,4)) details.append(button(`${time(candidate.start)}–${time(candidate.end)} · ${candidate.description}`,()=>edit({op:'add',asset_id:asset.id,start:candidate.start,end:candidate.end}),'candidate'));
    node.append(details);
  }
  return node;
}
function showVideo(url,label,kind,start=0) {
  playingShot=null;
  $('viewer-label').textContent=label; $('viewer-kind').textContent=kind;
  $('viewer').src=url; $('viewer').parentElement.classList.add('has-video');
  $('viewer').onloadedmetadata=()=>{ $('viewer').currentTime=start; };
  $('viewer-info').textContent=kind.includes('render')?'Rendered from original footage with saved edits.':'Source monitor. Render preview to see your full cut, captions, color and sound.';
}
function selectShot(id) {
  if(['trim-start','trim-end','shot-volume','shot-caption'].some(field=>dirty.has(field))) throw new Error('Apply the selected shot changes before choosing another shot.');
  for(const field of ['trim-start','trim-end','shot-volume','shot-caption']) dirty.delete(field);
  selected=id;
  const shot=project.timeline.find(s=>s.id===id), asset=project.assets[shot.asset_id];
  showVideo(fileURL(asset.proxy),asset.name,'Selected source range',shot.start); playingShot=shot;
  render();
}
function renderInspector() {
  const shot=project.timeline.find(s=>s.id===selected); $('inspector').hidden=!shot; if(!shot) return;
  setField('trim-start',shot.start.toFixed(2)); setField('trim-end',shot.end.toFixed(2)); setField('shot-volume',shot.volume);
  setField('shot-caption',shot.caption); $('shot-lock').textContent=shot.locked?'Unlock shot':'Lock shot';
  for(const id of ['trim-start','trim-end','shot-volume','shot-caption','save-shot','split-shot','remove-shot','move-left','move-right']) $(id).disabled=shot.locked;
}
function renderExports() {
  $('exports').replaceChildren(...project.exports.slice(-4).reverse().map(item=>{
    const row=el('div',null,'export-item');
    row.append(el('span',`${item.preview?'Preview':'Export'} · v${item.version} · ${item.width}×${item.height}`),button('Play',()=>showVideo(fileURL(item.path),project.name,`Version ${item.version} · rendered ${item.preview?'preview':'export'}`)));
    const link=el('a','Download'); link.href=fileURL(item.path); link.download=`${project.name.replace(/[^a-z0-9 -]/gi,'')||'film'}.mp4`; row.append(link);
    return row;
  }));
}
async function uploadFiles(files, kind='clip') {
  for(const file of files) {
    message(`Uploading ${file.name}…`);
    const response=await fetch(`/api/projects/${project.id}/upload`,{method:'POST',headers:{'X-Filename':encodeURIComponent(file.name),'X-Asset-Kind':kind},body:file});
    const result=await response.json(); if(!response.ok) throw new Error(result.error);
  }
  message('Upload received. Full-duration proxies are being prepared.'); await pollJobs();
}
async function startJob(action, data={}) { if(action==='export'&&dirty.size) throw new Error('Apply your pending changes before rendering.'); await editChain; await api(`/projects/${project.id}/${action}`,data); message(''); await pollJobs(); }
async function pollJobs() {
  const jobs=await api('/jobs');
  for(const job of jobs) {
    const previous=lastJobs.get(job.id);
    if(project&&job.project_id===project.id&&previous!==job.status&&job.status==='completed') {
      await reload();
      if(job.name==='Draft edit') {
        proposal=job.result; $('rationale').textContent=proposal.rationale;
        $('proposal-shots').replaceChildren(...proposal.timeline.map(s=>el('p',`${project.assets[s.asset_id].name}: ${time(s.start)}–${time(s.end)}`)));
        $('proposal').hidden=false;
      } else if(job.name==='Preview'||job.name==='Export') showVideo(fileURL(job.result.path),project.name,`Version ${job.result.version} · rendered ${job.result.preview?'preview':'export'}`);
    }
    lastJobs.set(job.id,job.status);
  }
  $('jobs').replaceChildren(...jobs.filter(j=>project&&j.project_id===project.id).slice(-5).reverse().map(job=>{
    const node=el('div',null,`job ${job.status}`); node.append(el('span',`${job.name} · ${job.message}`));
    if(['queued','running'].includes(job.status)) node.append(button('Cancel',()=>api(`/jobs/${job.id}/cancel`,{})));
    return node;
  }));
}
function bind(id, event, action) { $(id).addEventListener(event,()=>safe(action)); }
bind('new-project','click',async()=>{const p=await api('/projects',{name:'Untitled film'});await openProject(p.id);});
bind('projects','change',()=>openProject($('projects').value));
bind('project-name','change',()=>edit({op:'settings',name:$('project-name').value}));
bind('brief','change',()=>edit({op:'settings',brief:$('brief').value}));
bind('undo','click',()=>edit({op:'undo'})); bind('redo','click',()=>edit({op:'redo'}));
bind('upload','change',async()=>{await uploadFiles($('upload').files);$('upload').value='';});
bind('reference','change',async()=>{await uploadFiles($('reference').files,'reference');$('reference').value='';});
bind('sample','click',()=>startJob('sample'));
bind('analyze','click',()=>startJob('analyze',{use_model:$('use-model').checked}));
bind('direct','click',async()=>{await edit({op:'settings',brief:$('brief').value});await startJob('direct',{version:project.version,brief:project.brief,duration:Number($('duration').value),use_model:$('use-model').checked});});
bind('revise','click',async()=>{await edit({op:'settings',brief:$('brief').value});await startJob('direct',{version:project.version,brief:project.brief,duration:Number($('duration').value),use_model:$('use-model').checked,target_shot_id:selected});});
bind('apply-proposal','click',async()=>{if(proposal.version!==project.version) throw new Error('This draft is based on an older edit. Request a fresh draft before applying it.'); await edit({op:'proposal',timeline:proposal.timeline});proposal=null;render();});
bind('dismiss-proposal','click',()=>{proposal=null;render();});
bind('preview','click',()=>startJob('export',{version:project.version,preview:true}));
bind('export','click',()=>startJob('export',{version:project.version}));
bind('save-style','click',()=>edit({op:'settings',style:{aspect:$('aspect').value,look:$('look').value,title:$('title').value,title_size:Number($('title-size').value),font:$('font').value,title_position:$('title-position').value,title_background:$('title-background').checked,music:$('music').value,source_volume:Number($('source-volume').value),music_volume:Number($('music-volume').value)}}));
bind('save-shot','click',()=>edit({op:'shot',shot_id:selected,changes:{start:Number($('trim-start').value),end:Number($('trim-end').value),volume:Number($('shot-volume').value),caption:$('shot-caption').value}}));
bind('shot-lock','click',()=>edit({op:'shot',shot_id:selected,changes:{locked:!project.timeline.find(s=>s.id===selected).locked}}));
bind('split-shot','click',()=>{if(!playingShot||playingShot.id!==selected) throw new Error('Select this shot in the source monitor before splitting.');return edit({op:'split',shot_id:selected,at:$('viewer').currentTime});});
bind('remove-shot','click',()=>edit({op:'remove',shot_id:selected}));
bind('move-left','click',()=>edit({op:'move',shot_id:selected,index:Math.max(0,project.timeline.findIndex(s=>s.id===selected)-1)}));
bind('move-right','click',()=>edit({op:'move',shot_id:selected,index:Math.min(project.timeline.length-1,project.timeline.findIndex(s=>s.id===selected)+1)}));
$('viewer').addEventListener('timeupdate',()=>{if(playingShot&&$('viewer').currentTime>=playingShot.end){$('viewer').pause();$('viewer').currentTime=playingShot.start;}});
const drop=document.querySelector('.upload');
drop.addEventListener('dragover',event=>{event.preventDefault();drop.classList.add('dragging');});
drop.addEventListener('dragleave',()=>drop.classList.remove('dragging'));
drop.addEventListener('drop',event=>{event.preventDefault();drop.classList.remove('dragging');safe(()=>uploadFiles(event.dataTransfer.files));});
document.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='z'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){event.preventDefault();safe(()=>edit({op:event.shiftKey?'redo':'undo'}));}});
for(const id of ['project-name','brief','aspect','look','title','title-size','font','title-position','title-background','music','source-volume','music-volume','trim-start','trim-end','shot-volume','shot-caption']) $(id).addEventListener('input',()=>{dirty.add(id);$('save-state').textContent='Unapplied changes';});
async function boot() {
  config=await api('/config');
  $('use-model').disabled=!config.configured;
  $('model-info').textContent=config.configured?`${config.model} · ${config.local?'Local endpoint':'Remote endpoint: sampled frames and brief will be sent when enabled'} · ${config.endpoint}`:'No model needed to edit. Offline drafts use image signals and a few pace keywords, not story understanding. Connect your model in the server environment for visual direction.';
  const projects=await refreshProjects(), remembered=localStorage.getItem('loop-project');
  let chosen=projects.find(p=>p.id===remembered)||projects[0];
  if(!chosen) chosen=await api('/projects',{name:'My first film'});
  await openProject(chosen.id);
  const initialJobs=await api('/jobs'); for(const job of initialJobs)lastJobs.set(job.id,job.status);
  const savedDraft=initialJobs.filter(job=>job.project_id===project.id&&job.name==='Draft edit'&&job.status==='completed'&&job.result.version===project.version).at(-1);
  if(savedDraft) {
    proposal=savedDraft.result; $('rationale').textContent=proposal.rationale;
    $('proposal-shots').replaceChildren(...proposal.timeline.map(s=>el('p',`${project.assets[s.asset_id].name}: ${time(s.start)}–${time(s.end)}`)));
    $('proposal').hidden=false;
  }
  await pollJobs();
  setInterval(()=>safe(pollJobs),2000);
}
safe(boot);
