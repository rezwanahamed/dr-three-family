/* Framework-free dashboard preview. Local drafts never publish to the website. */
(() => {
  const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
  const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)');
  const ease='cubic-bezier(.22,1,.36,1)';
  const motions=new WeakMap();
  function motion(element,frames,options={}) {
    if(!element)return null;
    motions.get(element)?.cancel();
    if(reducedMotion.matches)return null;
    const animation=element.animate(frames,{duration:240,easing:ease,fill:'backwards',...options});
    motions.set(element,animation);
    animation.finished.then(()=>{if(motions.get(element)===animation)motions.delete(element);},()=>{});
    return animation;
  }
  function reveal(elements,stagger=24) {
    elements.forEach((element,index)=>motion(element,[{opacity:0,transform:'translateY(7px)'},{opacity:1,transform:'translateY(0)'}],{duration:240,delay:Math.min(index*stagger,140)}));
  }
  function openDialog(dialog) {
    dialog.classList.remove('closing');
    if(!dialog.open)dialog.showModal();
    const slide=dialog.id==='editor';
    motion(dialog,[{opacity:slide?1:0,transform:slide?'translateX(35px)':'translateY(-8px) scale(.985)'},{opacity:1,transform:'none'}],{duration:slide?300:220});
  }
  async function closeDialog(dialog) {
    if(!dialog.open||dialog.classList.contains('closing'))return;
    dialog.classList.add('closing');
    const animation=motion(dialog,[{opacity:1,transform:'none'},{opacity:0,transform:dialog.id==='editor'?'translateX(24px)':'translateY(-5px) scale(.99)'}],{duration:160,easing:'cubic-bezier(.4,0,1,1)'});
    if(animation){try{await animation.finished;}catch{return;}}
    if(dialog.classList.contains('closing')){dialog.close();dialog.classList.remove('closing');}
  }
  function setNavigation(open) {
    $('#sidebar').classList.toggle('open',open);
    $('#menu').setAttribute('aria-expanded',String(open));
    const backdrop=$('#nav-backdrop');
    if(open){backdrop.hidden=false;motion(backdrop,[{opacity:0},{opacity:1}],{duration:200});}
    else if(!backdrop.hidden){const animation=motion(backdrop,[{opacity:1},{opacity:0}],{duration:180});if(animation)animation.finished.then(()=>{if(!$('#sidebar').classList.contains('open'))backdrop.hidden=true;},()=>{});else backdrop.hidden=true;}
  }
  reducedMotion.addEventListener('change',()=>{if(reducedMotion.matches)document.getAnimations().forEach(animation=>animation.finish());});
  const iconNames={overview:'squares-four',pages:'file-text',treatments:'first-aid',doctors:'users',gallery:'images',clinic:'buildings',articles:'article',activity:'pulse',settings:'gear-six',download:'download-simple',plus:'plus',info:'info',search:'magnifying-glass',caretDown:'caret-down',caretRight:'caret-right',arrowUpRight:'arrow-up-right',arrowRight:'arrow-right',close:'x',menu:'list',enter:'arrow-elbow-down-left',up:'arrow-up',down:'arrow-down'};
  const icon=name=>`<svg class="phosphor-icon" data-phosphor="${iconNames[name]||iconNames.pages}" aria-hidden="true" focusable="false" viewBox="0 0 256 256" fill="currentColor">${window.DashboardPhosphor[iconNames[name]||iconNames.pages]}</svg>`;
  $$('[data-icon]').forEach(el=>el.innerHTML=icon(el.dataset.icon));
  const labels={overview:'Overview',pages:'Pages',treatments:'Treatments',doctors:'Doctors',gallery:'Gallery',clinic:'Our clinic',articles:'Articles & resources',activity:'Activity',settings:'Settings',drafts:'Local drafts'};
  const descriptions={clinic:'Manage the clinic story and photo collection on your Our clinic page.',drafts:'Review your saved changes before exporting them for your CMS.',pages:'Manage the pages that help patients get to know your clinic.',treatments:'Keep your treatment information clear, helpful, and up to date.',doctors:'Introduce the people behind your patients’ smiles.',gallery:'A closer look at your clinic, your team, and your care.',articles:'Helpful answers and stories for healthier smiles.',activity:'A record of your draft changes in this browser.',settings:'Manage your local website workspace preferences.'};
  const key='drteeth-dashboard-v1'; let store={drafts:[],activity:[],settings:{name:'Dr. Teeth Family Dental',email:'info@drteethfamilydental.com'}};
  try {const saved=JSON.parse(localStorage.getItem(key));if(saved&&Array.isArray(saved.drafts)&&Array.isArray(saved.activity))store={...store,...saved};}catch{}
  let records=[],section='overview',editing=null,search='',filter='all',sort='default',editorInitial='',queryIndex=0;
  const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safeURL=value=>/^(\/(?!\/)|https?:\/\/)/.test(value||'')?escape(value):'';
  const doctorFields=['specialty','qualifications','training','position','registration','appointment_url'];
  function withDoctorDetails(record){
    if(record.section!=='doctors')return record;
    const source=records.find(r=>r.id===record.id&&r.section==='doctors');
    return {...Object.fromEntries(doctorFields.map(name=>[name,source?.[name]||''])),...record};
  }
  const all=()=>[...records.filter(r=>!store.drafts.some(d=>d.id===r.id)),...store.drafts.map(withDoctorDetails)];
  const searchable=r=>[r.title,r.description,...doctorFields.map(name=>r[name])].join(' ').toLowerCase();
  const detailLines=value=>String(value||'').split('\n').filter(Boolean).map(line=>`<li>${escape(line)}</li>`).join('');
  function doctorCards(items){return `<div class="doctor-grid">${items.map(r=>`<article class="doctor-card"><div class="doctor-card-heading">${safeURL(r.image)?`<img class="doctor-card-portrait" src="${safeURL(r.image)}" alt="${escape(r.title)}" loading="lazy">`:`<div class="doctor-card-portrait doctor-no-portrait">${icon('doctors')}<small>Portrait unavailable</small></div>`}<div><p class="doctor-specialty">${escape(r.specialty||'Specialty not provided')}</p><h3><button class="title-button" data-edit="${escape(r.id)}">${escape(r.title)}</button></h3>${badge(r)}</div></div><div class="doctor-card-details"><h4>Qualifications</h4>${r.qualifications?`<ul>${detailLines(r.qualifications)}</ul>`:'<p>Not provided</p>'}${r.position?`<h4>Professional role</h4><p>${escape(r.position)}</p>`:''}${r.training?`<h4>Advanced training</h4><ul>${detailLines(r.training)}</ul>`:''}<p class="doctor-registration"><strong>BM&amp;DC</strong> ${escape(r.registration||'Not provided')}</p></div><div class="doctor-card-actions"><button data-edit="${escape(r.id)}" aria-label="Edit ${escape(r.title)}">Edit profile</button><a class="text-link" href="${safeURL(r.url)}" target="_blank" rel="noopener">View page ${icon('arrowUpRight')}</a>${safeURL(r.appointment_url)?`<a class="text-link" href="${safeURL(r.appointment_url)}" target="_blank" rel="noopener">Appointment ${icon('arrowUpRight')}</a>`:''}</div></article>`).join('')}</div>`;}

  const count=s=>all().filter(r=>r.section===s).length;
  const badge=r=>`<span class="badge ${r.status==='Draft'?'draft':'snapshot'}"><span class="badge-dot" aria-hidden="true"></span>${r.status==='Draft'?'Local draft':'Website snapshot'}</span>`;
  function toast(message){$('#toast').textContent=message;$('#toast').classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').classList.remove('show'),3000);}
  function save(){try{localStorage.setItem(key,JSON.stringify(store));return true;}catch{toast('Could not save locally. Check browser storage permissions.');return false;}}
  function activity(){return store.activity.length?`<ul class="activity-list">${store.activity.slice(0,12).map(a=>`<li>${escape(a.title)}<small>${escape(new Date(a.time).toLocaleString())}</small></li>`).join('')}</ul>`:`<div class="empty">${icon('activity')}<h3>A fresh start for your website</h3><p>Your saved drafts will appear here. Open any content item to make your first edit.</p></div>`;}
  function draftQueue(){return `<section class="panel draft-queue"><div class="panel-header"><div><h2>Ready for your next edit</h2><p>${store.drafts.length?'Pick up where you left off.':'Start with the content your patients see first.'}</p></div><a href="#drafts" class="text-link">View drafts ${icon('arrowRight')}</a></div><div class="quick-edits">${(store.drafts.length?store.drafts.slice(-3).reverse():records.filter(r=>['/','/services/','/our-doctors/'].includes(r.id))).map(r=>`<button data-edit="${escape(r.id)}"><span class="content-icon">${icon(r.section)}</span><span><strong>${escape(r.title)}</strong><small>${r.status==='Draft'?'Continue draft':'Edit '+labels[r.section].toLowerCase()}</small></span><span class="quick-arrow">${icon('arrowUpRight')}</span></button>`).join('')}</div></section>`;}
  function overview(){const categories=['pages','treatments','doctors','clinic','gallery','articles'];return `
    ${draftQueue()}<section class="stats" aria-label="Website content summary">${[['pages','Core pages',count('pages'),'Clinic information & key pages'],['treatments','Treatments',count('treatments'),'Treatment pages in your website'],['doctors','Doctors',count('doctors'),'Profiles in your team section'],['gallery','Gallery photos',count('gallery'),'Images in your clinic gallery']].map(([s,label,n,note])=>`<a href="#${s}" class="stat"><div class="stat-top">${label}${icon(s)}</div><span class="stat-value">${n}</span><small>${note} <span aria-hidden="true">${icon('arrowUpRight')}</span></small></a>`).join('')}</section>
    <section class="panel website-card"><div class="site-info"><span class="workspace-icon">${icon('pages')}</span><div><strong>${escape(store.settings.name)}</strong><p>Your clinic website · ${records.filter(r=>['pages','treatments','articles'].includes(r.section)).length} exported routes</p></div></div><div class="heading-actions"><a href="#drafts" class="badge draft">${store.drafts.length} local drafts ${icon('arrowRight')}</a><a class="text-link" href="/" target="_blank" rel="noopener">Open website ${icon('arrowUpRight')}</a></div></section>
    <div class="overview-grid"><section class="panel"><div class="panel-header"><div><h2>Manage your website</h2><p>Everything your patients see, in one place.</p></div><span class="badge snapshot">6 sections</span></div><div class="content-list">${categories.map(s=>`<a class="content-row" href="#${s}"><span class="content-icon">${icon(s)}</span><div><strong>${labels[s]}</strong><small>${({pages:'Core pages and clinic information',treatments:'Services, care, and treatment details',doctors:'Your team and professional profiles',gallery:'Clinic spaces and team photography',clinic:'Your clinic story and featured photo collection',articles:'Journal, resources, and patient guidance'})[s]}</small></div><span class="count">${count(s)}</span><span class="arrow">${icon('caretRight')}</span></a>`).join('')}</div></section><section class="panel"><div class="panel-header"><div><h2>Content overview</h2><p>Your website’s content library.</p></div>${icon('overview')}</div><div class="distribution">${categories.map(s=>`<div class="bar-row"><div class="bar-label"><span>${labels[s]}</span><strong>${count(s)}</strong></div><div class="bar-track"><div class="bar-fill" style="width:${count(s)/Math.max(...categories.map(count),1)*100}%"></div></div></div>`).join('')}<p class="panel-note">Counts reflect the website snapshot and your local drafts.</p></div></section></div>
    <section class="panel"><div class="panel-header"><div><h2>Recent activity</h2><p>Keep track of the changes you make.</p></div><a href="#activity" class="text-link">View activity ${icon('arrowRight')}</a></div>${activity()}</section>`;}
  function clinicCards(items){return `<div class="clinic-grid">${items.map(r=>`<article class="clinic-card"><div class="clinic-photo">${safeURL(r.image)?`<img src="${safeURL(r.image)}" alt="${escape(r.alt||r.title)}" loading="lazy">`:`<span>${icon('clinic')}</span>`}<span class="clinic-number">${String(r.order||1).padStart(2,'0')}</span></div><div class="clinic-details"><h3>${escape(r.title)}</h3><p>${escape(r.description)}</p><div class="clinic-actions">${badge(r)}<button data-edit="${escape(r.id)}" aria-label="Edit ${escape(r.title)}">Edit photo</button></div></div></article>`).join('')}</div>`;}
  function clinicIntro(){const page=all().find(r=>r.id==='/about-us/');return `<section class="panel clinic-intro"><span class="content-icon">${icon('clinic')}</span><div><span class="eyebrow">OUR CLINIC PAGE</span><h2>${escape(page?.title||'Our clinic')}</h2><p>Update the page introduction, then shape the photo collection below.</p></div><div class="heading-actions"><button data-edit="/about-us/">Edit introduction</button><a class="text-link" href="/about-us/" target="_blank" rel="noopener">View page ${icon('arrowUpRight')}</a></div></section>`;}
  function collection(){return `${section==='clinic'?clinicIntro():''}<section class="panel collection-panel"><div class="collection-heading"><div><h2>${section==='drafts'?'Your draft library':labels[section]+' library'}</h2><p>Find an item, review its details, and make your next update.</p></div><span class="library-icon">${icon(section)}</span></div><div class="toolbar"><label class="search" style="margin:0">${icon('search')}<input id="content-search" aria-label="Search content" placeholder="Search ${labels[section].toLowerCase()}…" value="${escape(search)}"></label><select id="status-filter" aria-label="Filter by status"><option value="all">All content</option><option value="Draft" ${filter==='Draft'?'selected':''}>Local drafts</option><option value="Website snapshot" ${filter==='Website snapshot'?'selected':''}>Website snapshot</option></select><select id="sort-content" aria-label="Sort content"><option value="default">Default order</option><option value="az">Title: A–Z</option><option value="za">Title: Z–A</option></select><span id="result-count" class="result-count"></span></div><div id="results"></div></section>`;}
  function results(animateResults=true){const items=all().filter(r=>(section==='drafts'?r.status==='Draft':r.section===section)&&(filter==='all'||r.status===filter)&&searchable(r).includes(search.toLowerCase()));if(section==='clinic'&&sort==='default')items.sort((a,b)=>(Number(a.order)||1)-(Number(b.order)||1));if(sort!=='default')items.sort((a,b)=>a.title.localeCompare(b.title)*(sort==='za'?-1:1));$('#result-count').textContent=`${items.length} ${items.length===1?'item':'items'}`;
    $('#results').innerHTML=!items.length?`<div class="empty">${icon('search')}<h3>${section==='drafts'&&!search?'No drafts yet':'No matching content'}</h3><p>${section==='drafts'&&!search?'Open any website item to save your first draft.':'Try another search or clear your filters.'}</p><button id="clear-search">${section==='drafts'&&!search?'Browse pages':'Clear filters'}</button></div>`:section==='clinic'?clinicCards(items):section==='doctors'?doctorCards(items):section==='gallery'?`<div class="media-grid">${items.map(r=>`<article class="media-card">${safeURL(r.image)?`<img src="${safeURL(r.image)}" alt="${escape(r.title)}" loading="lazy">`:''}<div><strong>${escape(r.title)}</strong><button data-edit="${escape(r.id)}">Edit details</button> ${badge(r)}</div></article>`).join('')}</div>`:`<div class="table-wrap"><table><thead><tr><th>Content</th><th>Status</th><th>Actions</th></tr></thead><tbody>${items.map(r=>`<tr><td><div class="table-content">${['doctors','gallery'].includes(r.section)&&safeURL(r.image)?`<img class="row-thumbnail" src="${safeURL(r.image)}" alt="" loading="lazy">`:`<span class="row-thumbnail placeholder">${icon(r.section)}</span>`}<div><button class="title-button" data-edit="${escape(r.id)}">${escape(r.title)}</button><small>${escape(r.url)}</small></div></div></td><td>${badge(r)}</td><td><button class="edit" data-edit="${escape(r.id)}" aria-label="Edit ${escape(r.title)}">Edit</button> <a class="text-link" href="${safeURL(r.url)}" target="_blank" rel="noopener" aria-label="Preview ${escape(r.title)}"><span class="preview-text">Preview</span> ${icon('arrowUpRight')}</a></td></tr>`).join('')}</tbody></table></div>`;
    if(animateResults)reveal($$('#results tbody tr, #results .media-card, #results .doctor-card, #results .empty'),16);
    bindEditors();if($('#clear-search'))$('#clear-search').onclick=()=>{if(section==='drafts'&&!search){location.hash='pages';return;}search='';filter='all';$('#content-search').value='';$('#status-filter').value='all';results();};
  }
  function bindEditors(){$$('[data-edit]').forEach(b=>b.onclick=()=>openEditor(all().find(r=>r.id===b.dataset.edit)));}
  function settings(){return `<section class="panel"><div class="panel-header"><div><h2>Workspace details</h2><p>These preferences apply to your local dashboard.</p></div></div><form id="settings-form" class="settings-form"><label>Workspace name<input name="name" required maxlength="100" value="${escape(store.settings.name)}"></label><label>Contact email<input name="email" required type="email" value="${escape(store.settings.email)}"></label><button class="primary">Save preferences</button></form></section>`;}
  function render(preserve=false){section=location.hash.slice(1)||'overview';if(!labels[section])section='overview';if(!preserve){search='';filter='all';sort='default';}$('#page-title').textContent=labels[section];$('#breadcrumb').textContent=labels[section];$('#page-description').textContent=descriptions[section]||'Your content, your team, and every first impression — all in one place.';document.title=`${labels[section]} · Dr. Teeth Website Console`;$$('[data-nav]').forEach(a=>{a.classList.toggle('active',a.dataset.nav===section);if(a.dataset.nav===section)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});$('[data-count="pages"]').textContent=count('pages');$('[data-count="drafts"]').textContent=store.drafts.length;setNavigation(false);$('#view').innerHTML=section==='overview'?overview():section==='activity'?`<section class="panel"><div class="panel-header"><h2>Draft activity</h2><span class="badge snapshot">${store.activity.length} changes</span></div>${activity()}</section>`:section==='settings'?settings():collection();
    $('#add').innerHTML=icon('plus')+' '+(({pages:'Add page',treatments:'Add treatment',doctors:'Add doctor',gallery:'Add photo',clinic:'Add clinic photo',articles:'Add article'})[section]||'Add content');bindEditors();if($('#content-search')){$('#sort-content').value=sort;$('#content-search').oninput=e=>{search=e.target.value;results(false);};$('#status-filter').onchange=e=>{filter=e.target.value;results();};$('#sort-content').onchange=e=>{sort=e.target.value;results();};results();}
    motion($('#view'),[{opacity:0,transform:'translateY(6px)'},{opacity:1,transform:'none'}],{duration:260});
    motion($('.page-heading'),[{opacity:.45,transform:'translateY(3px)'},{opacity:1,transform:'none'}],{duration:220});
    if(section==='overview')reveal($$('.stats .stat, .quick-edits > button'),30);
    if($('#settings-form'))$('#settings-form').onsubmit=e=>{e.preventDefault();const data=new FormData(e.target);store.settings={name:data.get('name').trim(),email:data.get('email').trim()};if(save()){updateWorkspace();toast('Workspace preferences saved');}};
  }
  function updateWorkspace(){$('.workspace strong').textContent=store.settings.name;}
  function updateEditorFields(){
    const form=$('#editor-form'),isDoctor=form.elements.section.value==='doctors',isClinic=form.elements.section.value==='clinic';
    $('#clinic-fields').hidden=!isClinic;$('#clinic-fields').disabled=!isClinic;
    form.elements.image.required=isClinic;form.elements.url.closest('label').hidden=isClinic;form.elements.url.disabled=isClinic;
    $('#doctor-fields').hidden=!isDoctor;
    $('#doctor-fields').disabled=!isDoctor;
    form.elements.description.required=!isDoctor;
    $('#editor-name-label').textContent=isDoctor?'Doctor name':'Title';
    for(const name of ['description','url','image']){
      const field=form.elements.namedItem(name);
      field.closest('label').hidden=isDoctor||(isClinic&&name==='url');
      field.disabled=isDoctor||(isClinic&&name==='url');
    }
    $('#editor-title').textContent=isDoctor?(editing?'Edit doctor':'Add doctor'):(isClinic?(editing?'Edit clinic photo':'Add clinic photo'):(editing?'Edit content':'Add content'));
    if(isClinic)form.elements.url.value='/about-us/';
    if(isDoctor){
      if(!form.elements.url.value)form.elements.url.value='/our-doctors/';
    }
  }
  function openEditor(record){
    editing=record?.id||null;
    const form=$('#editor-form');form.reset();
    for(const name of ['title','section','description','url','image','alt','order',...doctorFields.filter(name=>name!=='appointment_url')])form.elements.namedItem(name).value=record?.[name]||(name==='section'?(Object.keys(descriptions).includes(section)&&!['activity','settings','drafts'].includes(section)?section:'pages'):'');
    if(form.elements.section.value==='clinic'&&!record)form.elements.order.value=Math.max(0,...all().filter(r=>r.section==='clinic').map(r=>Number(r.order)||0))+1;
    updateEditorFields();$('#discard-notice').hidden=true;
    editorInitial=JSON.stringify(Object.fromEntries(new FormData(form)));
    openDialog($('#editor'));$('.editor-body').scrollTop=0;
  }
  $('#add').onclick=()=>openEditor();function closeEditor(){if(JSON.stringify(Object.fromEntries(new FormData($('#editor-form'))))!==editorInitial){$('#discard-notice').hidden=false;motion($('#discard-notice'),[{opacity:0,transform:'translateY(-4px)'},{opacity:1,transform:'none'}]);$('#keep-editing').focus();}else closeDialog($('#editor'));}
  $('#close-editor').onclick=$('#cancel-editor').onclick=closeEditor;$('#editor').addEventListener('cancel',e=>{e.preventDefault();closeEditor();});$('#keep-editing').onclick=()=>{$('#discard-notice').hidden=true;$('#editor-form input[name="title"]').focus();};$('#discard-editing').onclick=()=>closeDialog($('#editor'));
  $('#editor-form').onsubmit=e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target));Object.keys(data).forEach(k=>data[k]=data[k].trim());if(data.section==='clinic'){data.url='/about-us/';data.order=Number(data.order);if(!data.alt||!data.image||!Number.isInteger(data.order)||data.order<1){toast('Enter an image, alt text, and a display order of 1 or more.');return;}}if(data.section==='doctors'){const previous=all().find(r=>r.id===editing);Object.assign(data,{description:previous?.description||'',url:previous?.url||'/our-doctors/',image:previous?.image||'',appointment_url:previous?.appointment_url||'/appointment/'});}if(!data.title||(!data.description&&data.section!=='doctors')||!/^\/(?!\/)/.test(data.url)){toast('Enter a title, required details, and website path beginning with /.');return;}if(data.section==='doctors'&&(!data.specialty||!data.qualifications)){toast('Enter a specialty and qualifications.');return;}if(data.image&&!/^(\/(?!\/)|https?:\/\/)/.test(data.image)){toast('Use a local image path or an HTTPS image URL.');return;}const entry={...data,id:editing||`draft-${crypto.randomUUID()}`,status:'Draft'};store.drafts=store.drafts.filter(r=>r.id!==entry.id);store.drafts.push(entry);store.activity.unshift({title:`Saved draft: ${entry.title}`,time:new Date().toISOString()});store.activity=store.activity.slice(0,100);if(save()){closeDialog($('#editor'));render(true);toast('Draft saved in this browser');}};
  $('#export').onclick=()=>{const blob=new Blob([JSON.stringify({drafts:store.drafts.map(withDoctorDetails),settings:store.settings},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='dr-teeth-website-drafts.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Drafts exported');};
  $('#menu').onclick=()=>setNavigation(!$('#sidebar').classList.contains('open'));$('#nav-backdrop').onclick=()=>setNavigation(false);
  $('#account').onclick=()=>openDialog($('#account-dialog'));$('#close-account').onclick=()=>closeDialog($('#account-dialog'));
  function globalResults(){const query=$('#global-query').value.toLowerCase().trim();const items=all().filter(r=>!query||`${searchable(r)} ${labels[r.section]}`.toLowerCase().includes(query)).slice(0,8);queryIndex=0;$('#global-results').innerHTML=items.length?items.map((r,i)=>`<button class="command-result ${i===0?'selected':''}" data-record="${escape(r.id)}"><span class="content-icon">${icon(r.section)}</span><span><strong>${escape(r.title)}</strong><small>${labels[r.section]} · ${r.status}</small></span><span>${icon('enter')}</span></button>`).join(''):'<div class="empty"><h3>No results found</h3><p>Try a different title or content type.</p></div>';$$('.command-result').forEach(b=>b.onclick=async()=>{await closeDialog($('#search-dialog'));openEditor(all().find(r=>r.id===b.dataset.record));});}
  function openSearch(){$('#global-query').value='';globalResults();openDialog($('#search-dialog'));$('#global-query').focus();}
  ['search-dialog','account-dialog'].forEach(id=>$('#'+id).addEventListener('cancel',e=>{e.preventDefault();closeDialog($('#'+id));}));
  $('#open-search').onclick=openSearch;$('#close-search').onclick=()=>closeDialog($('#search-dialog'));$('#global-query').oninput=globalResults;
  $('#global-query').onkeydown=e=>{const items=$$('.command-result');if(!items.length)return;if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();queryIndex=(queryIndex+(e.key==='ArrowDown'?1:-1)+items.length)%items.length;items.forEach((b,i)=>b.classList.toggle('selected',i===queryIndex));items[queryIndex].scrollIntoView({block:'nearest'});}if(e.key==='Enter'){e.preventDefault();items[queryIndex].click();}};
  document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();if(!$('#editor').open)openSearch();}});
  window.addEventListener('hashchange',()=>{render();window.scrollTo({top:0});});document.addEventListener('keydown',e=>{if(e.key==='Escape'){setNavigation(false);}});
  fetch(document.body.dataset.contentUrl).then(r=>{if(!r.ok)throw Error('Content unavailable');return r.json();}).then(data=>{records=data;updateWorkspace();render();}).catch(()=>{$('#view').innerHTML='<div class="panel empty"><h3>Could not load website content</h3><p>Reload the page to try again.</p></div>';});
})();
