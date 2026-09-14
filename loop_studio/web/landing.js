'use strict';
const hero=document.getElementById('hero-ascii'),lab=document.getElementById('lab-ascii');
let paused=matchMedia('(prefers-reduced-motion: reduce)').matches, shape='orbit',phase=0;
const chars=' .,:;+=*#%@';
function art(cols,rows,t,kind){let out='';for(let y=0;y<rows;y++){for(let x=0;x<cols;x++){const u=(x-cols/2)/(cols*.24),v=(y-rows/2)/(rows*.35);let light=0;if(kind==='wave'){const wave=Math.sin(u*3+t)*.45+Math.cos(u*1.3-t*.7)*.2;light=Math.exp(-Math.pow((v-wave)*6,2))*(.6+.4*Math.sin(u*5-t));}else{const angle=t*.24,xx=u*Math.cos(angle)+v*Math.sin(angle)*.4,yy=-u*Math.sin(angle)+v*Math.cos(angle)*.4;const r=Math.sqrt(xx*xx+yy*yy*7);light=Math.exp(-Math.pow((r-1)*11,2))*(.55+.45*Math.sin(Math.atan2(yy,xx)*3+t));light+=Math.exp(-Math.pow((Math.sqrt(u*u+v*v)-.55)*17,2))*.4;}out+=chars[Math.min(chars.length-1,Math.floor(Math.max(0,light)*chars.length))];}out+='\n';}return out;}
function draw(){hero.textContent=art(120,34,phase,'orbit');lab.textContent=art(Number(document.getElementById('density').value),34,phase,shape);}
document.querySelectorAll('[data-shape]').forEach(b=>b.onclick=()=>{shape=b.dataset.shape;document.querySelectorAll('[data-shape]').forEach(n=>n.classList.toggle('active',n===b));draw();});
const pause=document.getElementById('pause-art');function label(){pause.textContent=paused?'Resume motion':'Pause motion';pause.setAttribute('aria-pressed',String(paused));}pause.onclick=()=>{paused=!paused;label();};label();document.getElementById('density').oninput=draw;
document.getElementById('download-ascii').onclick=()=>{const url=URL.createObjectURL(new Blob([lab.textContent],{type:'text/plain'})),a=document.createElement('a');a.href=url;a.download='loop-ascii-frame.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
draw();setInterval(()=>{if(!paused&&!document.hidden){phase+=.08;draw();}},80);
