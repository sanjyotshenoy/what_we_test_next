'use strict';
const el = id => document.getElementById(id);
let session=null, timer=null, lastMessage='';
async function request(url, body) {
  const response=await fetch(url, body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Demo-Run':'1'},body:JSON.stringify(body)});
  if(!response.ok) throw new Error((await response.text()).slice(0,220));
  return response.json();
}
function show(job) {
  el('live-status').textContent=`${job.state}: ${job.message}`;
  if(job.message!==lastMessage) {const li=document.createElement('li');li.textContent=job.message;el('live-events').append(li);lastMessage=job.message;}
  const active=['starting','running'].includes(job.state);
  el('start').disabled=active;el('stop').disabled=!active;
  el('live-results').href=`/?run=${encodeURIComponent(job.session)}`;el('live-results').hidden=false;
  if(!active) {clearTimeout(timer);timer=null;}
  return active;
}
async function poll() {
  try {if(show(await request(`/api/runs/${session}`))) timer=setTimeout(poll,3000);}
  catch(e) {el('live-status').textContent=`Unable to retrieve run: ${e.message}`;el('start').disabled=false;el('stop').disabled=true;}
}
el('live-form').onsubmit=async event=>{
  event.preventDefault();el('start').disabled=true;el('live-status').textContent='Starting…';
  const body={model:el('live-model').value,question:el('live-question').value,key:el('live-key').value};
  el('live-key').value='';
  try {
    const job=await request('/api/runs',body);session=job.session;body.key='';
    history.replaceState(null,'',`/planner?run=${encodeURIComponent(session)}`);
    el('live-events').replaceChildren();lastMessage='';show(job);timer=setTimeout(poll,1000);
  } catch(e) {el('live-status').textContent=e.message;el('start').disabled=false;}
  finally {body.key='';}
};
el('stop').onclick=async()=>{el('stop').disabled=true;try{clearTimeout(timer);show(await request(`/api/runs/${session}/stop`,{}));}catch(e){el('live-status').textContent=e.message;el('stop').disabled=false;}};
(async()=>{try {
  const catalog=await request('/api/precomputed');
  for(const m of catalog.models) {const option=document.createElement('option');option.value=m.id;option.textContent=m.label;el('live-model').append(option);}
  session=new URLSearchParams(location.search).get('run');if(session) await poll();
}catch(e){el('live-status').textContent=e.message;el('start').disabled=true;}})();
