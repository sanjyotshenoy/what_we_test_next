/* Browser-local split sizes. Focusing never reparents or rebuilds panel contents. */
function initializeDashboardLayout() {
  const main=document.querySelector('main'), panels=[...main.querySelectorAll('.panel')];
  const key='wwtn-dashboard-layout-v1', defaults={columns:[27,41,32],rows:[34,33,33]};
  let sizes=structuredClone(defaults), focused=null, previousFocus=null, resizeFrame=0;
  try {
    const saved=JSON.parse(localStorage.getItem(key));
    if(saved&&['columns','rows'].every(k=>Array.isArray(saved[k])&&saved[k].length===3&&saved[k].every(n=>Number.isFinite(n)&&n>=10&&n<=80)&&Math.abs(saved[k].reduce((a,b)=>a+b,0)-100)<.01)) sizes=saved;
  } catch {}
  const names={agent:'Agent workflow',kg:'Knowledge graph',plate:'96-well plate',structure:'Molecule',video:'Protocol visualization',robot:'Simulator'};
  const handles=[];
  const save=()=>{try{localStorage.setItem(key,JSON.stringify(sizes));}catch{}};
  function updateGeometry() {
    cancelAnimationFrame(resizeFrame);
    resizeFrame=requestAnimationFrame(()=>{
      main.style.setProperty('--dashboard-header-height',`${document.querySelector('header').getBoundingClientRect().height}px`);
      if(graph&&!graph.destroyed()&&!$('kg').hidden) graph.resize();
      if(focused||matchMedia('(max-width:1100px)').matches) return;
      const bounds=main.getBoundingClientRect(),agent=$('agent').getBoundingClientRect(),kg=$('kg').getBoundingClientRect(),video=$('video').getBoundingClientRect(),structure=$('structure').getBoundingClientRect();
      const positions=[{left:agent.right-bounds.left-1,top:8,height:bounds.height-16},
        {left:kg.right-bounds.left-1,top:8,height:bounds.height-16},
        {left:video.left-bounds.left,top:video.top-bounds.top-9,width:video.width},
        {left:kg.left-bounds.left,top:structure.top-bounds.top-9,width:bounds.right-kg.left-8}];
      handles.forEach((h,i)=>{for(const [k,v] of Object.entries(positions[i])) h.style[k]=`${v}px`;});
    });
  }
  function apply() {
    main.style.setProperty('--dashboard-columns',sizes.columns.map(v=>`minmax(0,${v}fr)`).join(' '));
    main.style.setProperty('--dashboard-rows',sizes.rows.map(v=>`minmax(0,${v}fr)`).join(' '));
    handles.forEach(h=>h.setAttribute('aria-valuenow',Math.round(sizes[h.dataset.axis][Number(h.dataset.index)])));
    updateGeometry();
  }
  function focusPanel(panel) {
    const restore=focused===panel;
    if(!focused) previousFocus=document.activeElement;
    focused=restore?null:panel;
    main.classList.toggle('panel-focused',!!focused);
    panels.forEach(p=>{
      p.hidden=!!focused&&p!==focused;
      const button=p.querySelector('.panel-focus');button.textContent=p===focused?'Restore':'Focus';
      button.setAttribute('aria-label',`${p===focused?'Restore dashboard from':'Focus'} ${names[p.id]}`);
      button.setAttribute('aria-pressed',String(p===focused));
    });
    hideGraphTooltip();updateGeometry();
    requestAnimationFrame(()=>{if(graph&&!graph.destroyed()&&!$('kg').hidden) graph.fit(undefined,45);});
    if(focused) focused.querySelector('.panel-focus').focus();
    else if(previousFocus?.isConnected) previousFocus.focus({preventScroll:true});
  }
  for(const panel of panels) {
    const button=document.createElement('button');button.type='button';button.className='small panel-focus';button.textContent='Focus';button.setAttribute('aria-label',`Focus ${names[panel.id]}`);button.setAttribute('aria-pressed','false');
    button.onclick=()=>focusPanel(panel);panel.querySelector('h2').append(button);
  }
  for(const [axis,index,label] of [['columns',0,'Agent column width'],['columns',1,'Graph column width'],['rows',0,'Plate panel height'],['rows',1,'Bottom panels height']]) {
    const handle=document.createElement('div');handle.className=`pane-divider ${axis}`;handle.dataset.axis=axis;handle.dataset.index=index;handle.tabIndex=0;handle.setAttribute('role','separator');handle.setAttribute('aria-orientation',axis==='columns'?'vertical':'horizontal');handle.setAttribute('aria-label',label);handle.setAttribute('aria-valuemin','10');handle.setAttribute('aria-valuemax','80');handle.title='Drag to resize; arrow keys adjust; double-click resets layout';
    function adjust(delta,start=sizes[axis]) {
      const total=start[index]+start[index+1],rect=main.getBoundingClientRect();
      const extent=axis==='columns'?rect.width-32:rect.height-32;
      const minimum=Math.min(total/2,Math.max(10,(axis==='columns'?220:150)/extent*100));
      sizes[axis]=[...start];sizes[axis][index]=Math.max(minimum,Math.min(total-minimum,start[index]+delta));sizes[axis][index+1]=total-sizes[axis][index];apply();
    }
    handle.onpointerdown=e=>{
      if(e.button!==0) return;
      e.preventDefault();hideGraphTooltip();handle.setPointerCapture(e.pointerId);
      const start=[...sizes[axis]],coordinate=axis==='columns'?e.clientX:e.clientY,rect=main.getBoundingClientRect(),extent=(axis==='columns'?rect.width:rect.height)-32;
      document.body.classList.add('resizing-panes');
      handle.onpointermove=event=>adjust(((axis==='columns'?event.clientX:event.clientY)-coordinate)/extent*100,start);
      const finish=()=>{handle.onpointermove=null;document.body.classList.remove('resizing-panes');save();};
      handle.onpointerup=finish;handle.onpointercancel=finish;handle.onlostpointercapture=finish;
    };
    handle.onkeydown=e=>{
      const negative=axis==='columns'?'ArrowLeft':'ArrowUp',positive=axis==='columns'?'ArrowRight':'ArrowDown';
      if(e.key===negative||e.key===positive){e.preventDefault();adjust((e.key===negative?-1:1)*(e.shiftKey?5:2));save();}
    };
    handle.ondblclick=reset;main.append(handle);handles.push(handle);
  }
  function reset() {sizes=structuredClone(defaults);save();apply();}
  $('reset-layout').onclick=reset;
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&focused&&!document.querySelector('dialog[open]')){e.preventDefault();focusPanel(focused);}});
  new ResizeObserver(updateGeometry).observe(main);
  new ResizeObserver(updateGeometry).observe(document.querySelector('header'));
  new ResizeObserver(updateGeometry).observe($('cy'));
  apply();
}


function initializeDashboardHeader() {
  const more=document.getElementById('header-more'),menu=document.getElementById('header-menu');
  const compact=matchMedia('(max-width:1100px)');
  const controls=['model','trace-switch','theme-toggle'].map(id=>{
    const element=document.getElementById(id),anchor=document.createComment(`header ${id}`);
    element.before(anchor);return {element,anchor};
  });
  function arrange() {
    for(const {element,anchor} of controls) {
      if(compact.matches) menu.append(element);else anchor.after(element);
    }
    more.open=false;
  }
  arrange();compact.addEventListener('change',arrange);
  document.addEventListener('click',event=>{if(!more.contains(event.target)) more.open=false;});
  more.addEventListener('keydown',event=>{if(event.key==='Escape') {more.open=false;more.querySelector('summary').focus();event.stopPropagation();}});
}
