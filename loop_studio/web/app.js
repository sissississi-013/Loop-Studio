'use strict';
const $ = id => document.getElementById(id);
let project = null, selected = null, proposal = null, playingShot = null, lastJobs = new Map(), config = {};
let editChain = Promise.resolve();
let jobRenderKey = null;
let workflowBusy = false;
let selectedMood = null;
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
  await editChain; if(dirty.size) throw new Error('Apply your pending changes before switching projects.'); dirty.clear(); project = await api(`/projects/${id}`); selected=null; proposal=null; playingShot=null; selectedMood=null;
  for(const node of document.querySelectorAll('[data-mood]')) node.classList.remove('active');
  localStorage.setItem('loop-project',id); $('viewer').pause(); $('viewer').removeAttribute('src'); $('viewer').load();
  $('viewer').parentElement.classList.remove('has-video'); render(); await refreshProjects();
  const recent=project.accepted_preview?.version===project.version?project.accepted_preview:project.exports.filter(e=>e.version===project.version).at(-1);
  if(recent) showVideo(fileURL(recent.path),project.name,`Version ${recent.version} · rendered ${recent.preview?'preview':'export'}`);
  else if(project.timeline.length) selectShot(project.timeline[0].id);
  const jobs=await api('/jobs');
  const savedDraft=jobs.filter(job=>job.project_id===project.id&&['Make my film','Draft edit'].includes(job.name)&&job.status==='completed'&&job.result.version===project.version).at(-1);
  if(savedDraft) showProposal({...savedDraft.result,job_id:savedDraft.id},false);
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
        if(operation.style) for(const id of ['ascii-mode','ascii-columns','aspect','look','title','title-size','font','shot-seconds','title-position','title-background','music','source-volume','music-volume']) dirty.delete(id);
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
  for(const [key,id] of Object.entries({ascii_mode:'ascii-mode',ascii_columns:'ascii-columns',aspect:'aspect',look:'look',title:'title',title_size:'title-size',font:'font',shot_seconds:'shot-seconds',title_position:'title-position',music:'music',source_volume:'source-volume',music_volume:'music-volume'})) setField(id,project.style[key]);
  if(!dirty.has('title-background')) $('title-background').checked=project.style.title_background;
  const clips=Object.values(project.assets).filter(a=>a.kind!=='reference');
  document.body.classList.toggle('has-footage',clips.length>0);
  $('step-footage').classList.toggle('active',!clips.length);
  $('step-draft').classList.toggle('active',!!clips.length&&!project.timeline.length);
  $('step-finish').classList.toggle('active',!!project.timeline.length);
  $('asset-count').textContent=`${clips.length} / 10`;
  $('assets').replaceChildren(...clips.map(assetCard));
  $('references').replaceChildren(...Object.values(project.assets).filter(a=>a.kind==='reference').map(assetCard));
  $('sample').hidden=Object.keys(project.assets).length>0;
  $('discard').hidden=!dirty.size;
  $('undo').disabled=!project.undo.length; $('redo').disabled=!project.redo.length;
  $('preview').disabled=$('export').disabled=!project.timeline.length;
  $('direct').disabled=!clips.length||workflowBusy; $('analyze').disabled=!clips.length||workflowBusy;
  $('revise').disabled=!selected||workflowBusy;
  $('timeline-duration').textContent=time(project.timeline.reduce((sum,s)=>sum+s.end-s.start,0));
  $('shot-count').textContent=`${project.timeline.length} shots`;
  if(project.timeline.length) $('timeline').replaceChildren(...project.timeline.map((shot,index)=>{
    const asset=project.assets[shot.asset_id];
    const node=button('',()=>selectShot(shot.id),'timeline-shot'+(selected===shot.id?' selected':''));
    node.setAttribute('aria-label',`Shot ${index+1}: ${asset.name}${shot.locked?', locked':''}`);
    node.style.width=`${Math.max(8,(shot.end-shot.start)*Number($('timeline-zoom').value))}px`;
    node.draggable=true;node.addEventListener('dragstart',event=>event.dataTransfer.setData('text/plain',shot.id));node.addEventListener('dragover',event=>event.preventDefault());node.addEventListener('drop',event=>{event.preventDefault();const sid=event.dataTransfer.getData('text/plain');if(project.timeline.some(s=>s.id===sid))safe(()=>edit({op:'move',shot_id:sid,index}));});
    const image=el('img'); image.src=fileURL(asset.poster); image.alt='';
    const meta=el('span',null,'shot-meta'); meta.append(el('strong',`${shot.locked?'🔒 ':''}${index+1}. ${asset.name}`),el('span',`${time(shot.start)} → ${time(shot.end)}`));
    node.append(image,meta); return node;
  })); else $('timeline').replaceChildren(el('p','Your story starts here. Add a shot from the footage library.','timeline-empty'));
  renderInspector(); renderExports();
  const duration=project.timeline.reduce((n,s)=>n+s.end-s.start,0);
  $('timeline-ruler').replaceChildren(...Array.from({length:Math.ceil(duration/5)+1},(_,i)=>{const tick=el('span',time(i*5));tick.style.width=`${5*Number($('timeline-zoom').value)}px`;return tick;}));
  $('audio-strip').textContent=project.style.music==='none'?'SOURCE AUDIO':`SOURCE + ${project.style.music.toUpperCase()} / PROCEDURAL MUSIC`;
  $('proposal').hidden=!proposal;
  $('apply-proposal').disabled=!proposal||proposal.version!==project.version||workflowBusy;
  $('apply-proposal').title=proposal&&proposal.version!==project.version?'This draft predates your latest edits. Make a fresh draft.':'';
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
  if(asset.kind==='reference'&&analysis) actions.append(button('Use look & pace',()=>edit({op:'settings',style:analysis.reference_style,explicit_style_keys:Object.keys(analysis.reference_style)})));
  node.append(actions);
  if(analysis) {
    const details=el('details'), summary=el('summary',analysis.mode==='model'?'AI notes · review for accuracy':'Sampled moments · offline');
    details.append(summary,el('p',analysis.description,'analysis-text'));
    const notes=el('textarea'); notes.rows=3; notes.value=project.notes?.[asset.id]??analysis.description;
    notes.setAttribute('aria-label',`Correct footage notes for ${asset.name}`);
    details.append(notes,button('Save corrected notes',()=>edit({op:'notes',asset_id:asset.id,text:notes.value})));
    if(asset.kind==='reference') details.append(el('p',`Suggested look: ${analysis.reference_style.look}${analysis.reference_style.shot_seconds?` · estimated cut length ${analysis.reference_style.shot_seconds}s`:''}. Scene-change estimates are editable, not a guarantee of matching the reference.`,'analysis-text'));
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
  setInspectorTab('inspector');
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
      if(job.name==='Make my film'||job.name==='Draft edit') {
        showProposal({...job.result,job_id:job.id});
      } else if(job.name==='Preview'||job.name==='Export') showVideo(fileURL(job.result.path),project.name,`Version ${job.result.version} · rendered ${job.result.preview?'preview':'export'}`);
    }
    lastJobs.set(job.id,job.status);
  }
  const active=jobs.find(j=>j.project_id===project?.id&&['queued','running'].includes(j.status)&&['Make my film','Import'].includes(j.name));
  workflowBusy=!!active;
  $('workflow-progress').hidden=!active;
  if(active) {
    const copy=el('div');copy.append(el('strong',active.message),el('small','You can cancel. Your saved cut stays intact.'));
    $('workflow-progress').replaceChildren(copy,button('Cancel',()=>api(`/jobs/${active.id}/cancel`,{})));
  }
  $('direct').disabled=workflowBusy||!Object.values(project?.assets||{}).some(a=>a.kind!=='reference');
  $('revise-draft').disabled=workflowBusy;
  $('apply-proposal').disabled=workflowBusy||!proposal||proposal.version!==project?.version;
  const shown=jobs.filter(j=>project&&j.project_id===project.id).slice(-5).reverse();
  const key=JSON.stringify(shown);
  if(key===jobRenderKey) return;
  jobRenderKey=key;
  $('jobs').replaceChildren(...shown.map(job=>{
    const node=el('div',null,`job ${job.status}`); node.append(el('span',`${job.name} · ${job.message}`));
    if(['failed','cancelled'].includes(job.status)&&job.name==='Make my film') node.append(button('Retry draft',()=>makeFilm()));
    if(['queued','running'].includes(job.status)) node.append(button('Cancel',()=>api(`/jobs/${job.id}/cancel`,{})));
    return node;
  }));
}
function bind(id, event, action) { $(id).addEventListener(event,()=>safe(action)); }
bind('new-project','click',async()=>{const p=await api('/projects',{name:'Untitled film'});await openProject(p.id);});
bind('projects','change',()=>openProject($('projects').value));
bind('project-name','change',()=>edit({op:'settings',name:$('project-name').value}));
bind('brief','change',()=>edit({op:'settings',brief:$('brief').value}));
bind('discard','click',()=>{dirty.clear();render();$('save-state').textContent='Saved locally';});
bind('undo','click',()=>edit({op:'undo'})); bind('redo','click',()=>edit({op:'redo'}));
bind('upload','change',async()=>{await uploadFiles($('upload').files);$('upload').value='';});
bind('reference','change',async()=>{await uploadFiles($('reference').files,'reference');$('reference').value='';});
bind('sample','click',()=>startJob('sample'));
bind('analyze','click',()=>startJob('analyze',{use_model:$('use-model').checked}));
bind('direct','click',()=>makeFilm());
bind('revise','click',()=>makeFilm({target_shot_id:selected}));
bind('revise-draft','click',()=>{
  const feedback=$('draft-feedback').value.trim();
  if(!feedback) throw new Error('Describe what you want to change first.');
  return makeFilm({draft_timeline:proposal.timeline,draft_style:proposal.style,feedback,brief:`Original direction: ${project.brief}\nRequested revision: ${feedback}`});
});
bind('watch-proposal','click',()=>watchProposal());
bind('watch-current','click',async()=>{
  if(!project.timeline.length) return;
  const current=project.accepted_preview?.version===project.version?project.accepted_preview:project.exports.filter(e=>e.version===project.version).at(-1);
  if(current) showVideo(fileURL(current.path),'Your current cut','Current cut · rendered preview');
  else await startJob('export',{version:project.version,preview:true});
});
bind('apply-proposal','click',async()=>{
  if(dirty.size) throw new Error('Save or discard changes made after this draft before keeping it.');
  if(proposal.version!==project.version) throw new Error('Your edit has changed since this draft. Make a fresh draft to keep your latest changes.');
  const kept=proposal;
  if(proposal.preview&&proposal.job_id) project=await api(`/projects/${project.id}/keep-film`,{version:project.version,job_id:proposal.job_id});
  else await edit({op:'proposal',timeline:proposal.timeline});
  proposal=null;render();
  if(kept.preview) showVideo(fileURL(kept.preview.path),'Your film','Kept cut · rendered preview');
  message('Cut kept. Make small adjustments below, or export the finished film.');
});
bind('dismiss-proposal','click',()=>{proposal=null;render();});
bind('preview','click',async()=>{await savePending();await startJob('export',{version:project.version,preview:true});});
bind('export','click',async()=>{await savePending();await startJob('export',{version:project.version});});
bind('save-style','click',()=>edit({op:'settings',style:readStyle()}));
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
for(const id of ['project-name','brief','ascii-mode','ascii-columns','aspect','look','title','title-size','font','shot-seconds','title-position','title-background','music','source-volume','music-volume','trim-start','trim-end','shot-volume','shot-caption']) $(id).addEventListener('input',()=>{dirty.add(id);$('discard').hidden=false;$('save-state').textContent='Unapplied changes';});

function readStyle() {
  return {ascii_mode:$('ascii-mode').value,ascii_columns:Number($('ascii-columns').value),aspect:$('aspect').value,look:$('look').value,title:$('title').value,title_size:Number($('title-size').value),font:$('font').value,shot_seconds:Number($('shot-seconds').value),title_position:$('title-position').value,title_background:$('title-background').checked,music:$('music').value,source_volume:Number($('source-volume').value),music_volume:Number($('music-volume').value)};
}
async function savePending() {
  const fields={name:$('project-name').value,brief:$('brief').value,style:readStyle()};
  const shotFields=selected&&['trim-start','trim-end','shot-volume','shot-caption'].some(id=>dirty.has(id))?{start:Number($('trim-start').value),end:Number($('trim-end').value),volume:Number($('shot-volume').value),caption:$('shot-caption').value}:null;
  const styleKeys={'ascii-mode':'ascii_mode','ascii-columns':'ascii_columns','aspect':'aspect','look':'look','title':'title','title-size':'title_size','font':'font','shot-seconds':'shot_seconds','title-position':'title_position','title-background':'title_background','music':'music','source-volume':'source_volume','music-volume':'music_volume'};
  const explicit_style_keys=[...dirty].filter(k=>styleKeys[k]).map(k=>styleKeys[k]);
  await editChain;
  if(shotFields) await edit({op:'shot',shot_id:selected,changes:shotFields});
  if(explicit_style_keys.length||fields.name!==project.name||fields.brief!==project.brief||JSON.stringify(fields.style)!==JSON.stringify(Object.fromEntries(Object.keys(fields.style).map(k=>[k,project.style[k]])))) await edit({op:'settings',...fields,explicit_style_keys});
}
async function makeFilm(extra={}) {
  if(workflowBusy) return;
  workflowBusy=true;$('direct').disabled=true;
  try {
    await savePending();
    await startJob('make-film',{version:project.version,brief:project.brief,duration:$('duration').value==='auto'?Math.max(5,Math.min(30,Math.floor(Object.values(project.assets).filter(a=>a.kind!=='reference').reduce((n,a)=>n+a.duration,0)*.85))):Number($('duration').value),use_model:$('use-model').checked,mood:selectedMood,...extra});
  } catch(error) { workflowBusy=false;$('direct').disabled=false;throw error; }
}
function watchProposal(start=0) {
  if(!proposal?.preview) return;
  showVideo(fileURL(proposal.preview.path),'Your proposed film','Draft · rendered preview',start);
}
function showProposal(result,focus=true) {
  proposal=result;
  $('draft-duration').textContent=`${time(result.duration)} · ${result.timeline.length} shots`;
  $('rationale').textContent=`${result.mode==='model'?'Model explanation — review for accuracy: ':''}${result.rationale}`;
  const metrics=el('div',null,'review-metrics');
  if(result.review) metrics.append(el('span',`${result.review.changed} shots changed`),el('span',`${result.review.removed} removed`),el('span',`${result.review.locked} locked`));
  if(result.direction) metrics.append(el('span',result.direction));
  if(result.elapsed_seconds) metrics.append(el('span',`Ready in ${result.elapsed_seconds}s`));
  $('review-summary').replaceChildren(metrics,...(result.review?.notes||[]).map(note=>el('p',note,'review-warning')));
  let offset=0;
  $('proposal-shots').replaceChildren(...result.timeline.map((shot,index)=>{
    const start=offset;offset+=shot.end-shot.start;
    const asset=project.assets[shot.asset_id], card=button('',()=>watchProposal(start));
    card.setAttribute('aria-label',`Preview draft shot ${index+1}: ${asset.name}`);
    const img=el('img');img.src=fileURL(result.preview?.thumbnails?.[index]||asset.poster);img.alt='';
    card.append(img,el('span',`${index+1}. ${asset.name} · ${(shot.end-shot.start).toFixed(1)}s${shot.locked?' · locked':''}`));return card;
  }));
  $('apply-proposal').disabled=workflowBusy||result.version!==project.version;
  $('watch-proposal').disabled=!result.preview;
  $('watch-current').disabled=!project.timeline.length;
  $('draft-feedback').value='';$('proposal').hidden=false;
  if(result.preview&&(focus||!$('viewer').getAttribute('src'))) watchProposal();
  if(focus) $('proposal').scrollIntoView({behavior:'smooth',block:'nearest'});
}
const moods={quiet:{look:'warm',font:'serif',shot_seconds:4,music:'ambient',title_position:'bottom-left'},bright:{look:'natural',font:'sans',shot_seconds:1.25,music:'pulse',title_position:'top-left'},editorial:{look:'mono',font:'sans',shot_seconds:3,music:'none',title_position:'bottom-left'}};
for(const node of document.querySelectorAll('[data-mood]')) node.addEventListener('click',()=>{
  selectedMood=node.dataset.mood;
  const mood=moods[selectedMood];
  const ids={look:'look',font:'font',shot_seconds:'shot-seconds',music:'music',title_position:'title-position'};
  for(const [key,value] of Object.entries(mood)){ $(ids[key]).value=value;dirty.add(ids[key]); }
  for(const sibling of document.querySelectorAll('[data-mood]')) sibling.classList.toggle('active',sibling===node);
  $('save-state').textContent='Direction selected';$('discard').hidden=false;
});

async function boot() {
  config=await api('/config');
  $('use-model').disabled=!config.configured;
  const choice=localStorage.getItem('loop-director:'+config.endpoint);
  $('use-model').checked=config.configured&&(choice===null?config.local:choice==='true');
  $('use-model').addEventListener('change',()=>localStorage.setItem('loop-director:'+config.endpoint,String($('use-model').checked)));
  $('model-info').textContent=config.configured?`${config.model}${config.planner_model!==config.model?` + ${config.planner_model} planner`:''} · ${config.local?'Runs on your computer; footage stays local':'Remote endpoint: sampled frames and brief will be sent when enabled'} · ${config.endpoint}`:'No model needed to edit. Offline drafts use image signals and a few pace keywords, not story understanding. Connect your model in the server environment for visual direction.';
  const projects=await refreshProjects(), remembered=localStorage.getItem('loop-project');
  let chosen=projects.find(p=>p.id===remembered)||projects[0];
  if(!chosen) chosen=await api('/projects',{name:'My first film'});
  await openProject(chosen.id);
  const initialJobs=await api('/jobs'); for(const job of initialJobs)lastJobs.set(job.id,job.status);
  await pollJobs();
  setInterval(()=>safe(pollJobs),2000);
}
safe(boot);

function setInspectorTab(name){for(const tab of ['director','inspector','effects']){$(tab+'-pane').hidden=tab!==name;$('tab-'+tab).classList.toggle('active',tab===name);}}
bind('tab-director','click',()=>setInspectorTab('director'));
bind('tab-inspector','click',()=>setInspectorTab('inspector'));
bind('timeline-zoom','input',()=>{render();updatePlayhead();});
bind('transport','click',()=>{const video=$('viewer');if(!video.getAttribute('src'))return;if(video.paused)return video.play();video.pause();});
$('viewer').addEventListener('timeupdate',()=>{const t=$('viewer').currentTime||0;$('timecode').textContent=`${String(Math.floor(t/60)).padStart(2,'0')}:${String(Math.floor(t%60)).padStart(2,'0')}:${String(Math.floor(t%1*30)).padStart(2,'0')}`;});

function updatePlayhead(){let t=$('viewer').currentTime||0;if(playingShot){let before=0;for(const s of project.timeline){if(s.id===playingShot.id)break;before+=s.end-s.start;}t=before+Math.max(0,t-playingShot.start);}$('timecode').textContent=`${String(Math.floor(t/60)).padStart(2,'0')}:${String(Math.floor(t%60)).padStart(2,'0')}:${String(Math.floor(t%1*30)).padStart(2,'0')}`;const x=71+t*Number($('timeline-zoom').value)-$('timeline').scrollLeft;$('timeline-playhead').style.left=`${x}px`;$('timeline-playhead').hidden=x<66;}
$('viewer').addEventListener('timeupdate',updatePlayhead);
$('timeline').addEventListener('scroll',()=>{$('timeline-ruler').scrollLeft=$('timeline').scrollLeft;updatePlayhead();});
$('timeline-ruler').addEventListener('click',event=>safe(()=>{const seconds=Math.max(0,(event.clientX-$('timeline-ruler').getBoundingClientRect().left-66+$('timeline').scrollLeft)/Number($('timeline-zoom').value));if(!project.timeline.length)return;if(!playingShot&&$('viewer').getAttribute('src')?.includes('/exports/')){$('viewer').currentTime=Math.min(seconds,$('viewer').duration||seconds);return;}let offset=0;for(const shot of project.timeline){if(seconds<offset+shot.end-shot.start){selectShot(shot.id);$('viewer').onloadedmetadata=()=>{$('viewer').currentTime=shot.start+seconds-offset;};break;}offset+=shot.end-shot.start;}}));
document.addEventListener('keydown',event=>{if(event.code==='Space'&&!['INPUT','TEXTAREA','SELECT','BUTTON','SUMMARY'].includes(document.activeElement.tagName)){event.preventDefault();$('transport').click();}});

bind('tab-effects','click',()=>setInspectorTab('effects'));
bind('ascii-preview','click',async()=>{await savePending();await startJob('export',{version:project.version,preview:true});});
