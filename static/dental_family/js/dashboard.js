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
  const iconNames={overview:'squares-four',pages:'file-text',treatments:'first-aid',doctors:'users',gallery:'images',clinic:'buildings',locations:'buildings',articles:'article',activity:'pulse',settings:'gear-six',download:'download-simple',upload:'arrow-up',plus:'plus',info:'info',search:'magnifying-glass',caretDown:'caret-down',caretRight:'caret-right',arrowUpRight:'arrow-up-right',arrowRight:'arrow-right',close:'x',menu:'list',enter:'arrow-elbow-down-left',up:'arrow-up',down:'arrow-down',drag:'dots-six-vertical'};
  const icon=name=>`<svg class="phosphor-icon" data-phosphor="${iconNames[name]||iconNames.pages}" aria-hidden="true" focusable="false" viewBox="0 0 256 256" fill="currentColor">${window.DashboardPhosphor[iconNames[name]||iconNames.pages]}</svg>`;
  $$('[data-icon]').forEach(el=>el.innerHTML=icon(el.dataset.icon));
  const labels={overview:'Overview',pages:'Pages',treatments:'Treatments',doctors:'Doctors',gallery:'Gallery',clinic:'Our clinic',locations:'Locations',articles:'Articles & resources',activity:'Activity',settings:'Settings',drafts:'Local drafts'};
  const descriptions={locations:'Manage your clinic branches, contact details, and Google Maps locations.',clinic:'Manage the clinic story and photo collection on your Our clinic page.',drafts:'Review your saved changes before exporting them for your CMS.',pages:'Manage the pages that help patients get to know your clinic.',treatments:'Keep your treatment information clear, helpful, and up to date.',doctors:'Introduce the people behind your patients’ smiles.',gallery:'A closer look at your clinic, your team, and your care.',articles:'Helpful answers and stories for healthier smiles.',activity:'A record of your draft changes in this browser.',settings:'Manage your local website workspace preferences.'};
  const key='drteeth-dashboard-v1'; let store={drafts:[],deletions:[],activity:[],settings:{name:'Dr. Teeth Family Dental',email:'info@drteethfamilydental.com'}};
  try {const saved=JSON.parse(localStorage.getItem(key));if(saved&&Array.isArray(saved.drafts)&&Array.isArray(saved.activity))store={...store,...saved};}catch{}
  let records=[],section='overview',editing=null,search='',filter='all',sort='default',editorInitial='',queryIndex=0;
  const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safeURL=value=>/^(\/(?!\/)|https?:\/\/)/.test(value||'')?escape(value):'';
  const doctorFields=['specialty','qualifications','training','position','registration','appointment_url'];
  function withRecordDetails(record){
    if(['gallery','doctors'].includes(record.section)){
      const source=records.find(r=>r.id===record.id);
      const fallback=records.filter(r=>r.section===record.section).length+store.drafts.filter(r=>r.section===record.section).findIndex(r=>r.id===record.id)+1;
      record={...record,alt:record.alt||source?.alt||record.title,order:Number(record.order)||source?.order||fallback};
    }
    if(record.section!=='doctors')return record;
    const source=records.find(r=>r.id===record.id&&r.section==='doctors');
    return {...Object.fromEntries(doctorFields.map(name=>[name,source?.[name]||''])),...record};
  }
  function capitalizeText(value){return String(value||'').replace(/(^|[\s-])(\p{L})/gu,(_,separator,letter)=>separator+letter.toLocaleUpperCase());}
  const all=()=>[...records.filter(r=>!store.drafts.some(d=>d.id===r.id)),...store.drafts.map(withRecordDetails)].filter(record=>!(store.deletions||[]).some(deleted=>deleted.id===record.id)).map(record=>record.section==='treatments'?{...record,title:capitalizeText(record.title)}:record);
  const searchable=r=>[r.title,r.description,r.short_details,r.keywords,r.seo_title,r.service,r.treatment,r.area,r.address,r.phone,r.hours,...doctorFields.map(name=>r[name])].join(' ').toLowerCase();


  const count=s=>all().filter(r=>r.section===s).length;
  const badge=r=>`<span class="badge ${r.status==='Draft'?'draft':'snapshot'}"><span class="badge-dot" aria-hidden="true"></span>${r.status==='Draft'?'Local draft':'Website snapshot'}</span>`;
  function toast(message){$('#toast').textContent=message;$('#toast').classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').classList.remove('show'),3000);}
  function save(){try{localStorage.setItem(key,JSON.stringify(store));return true;}catch{toast('Could not save locally. Check browser storage permissions.');return false;}}
  function activity(){return store.activity.length?`<ul class="activity-list">${store.activity.slice(0,12).map(a=>`<li>${escape(a.title)}<small>${escape(new Date(a.time).toLocaleString())}</small></li>`).join('')}</ul>`:`<div class="empty">${icon('activity')}<h3>A fresh start for your website</h3><p>Your saved drafts will appear here. Open any content item to make your first edit.</p></div>`;}
  function draftQueue(){return `<section class="panel draft-queue"><div class="panel-header"><div><h2>Ready for your next edit</h2><p>${store.drafts.length?'Pick up where you left off.':'Start with the content your patients see first.'}</p></div><a href="#drafts" class="text-link">View drafts ${icon('arrowRight')}</a></div><div class="quick-edits">${(store.drafts.length?store.drafts.slice(-3).reverse():records.filter(r=>['/','/services/','/our-doctors/'].includes(r.id))).map(r=>`<button data-edit="${escape(r.id)}"><span class="content-icon">${icon(r.section)}</span><span><strong>${escape(r.title)}</strong><small>${r.status==='Draft'?'Continue draft':'Edit '+labels[r.section].toLowerCase()}</small></span><span class="quick-arrow">${icon('arrowUpRight')}</span></button>`).join('')}</div></section>`;}
  function overview(){const categories=['pages','treatments','doctors','clinic','locations','gallery','articles'];return `
    ${draftQueue()}<section class="stats" aria-label="Website content summary">${[['pages','Core pages',count('pages'),'Clinic information & key pages'],['treatments','Treatments',count('treatments'),'Treatment pages in your website'],['doctors','Doctors',count('doctors'),'Profiles in your team section'],['gallery','Gallery photos',count('gallery'),'Images in your clinic gallery']].map(([s,label,n,note])=>`<a href="#${s}" class="stat"><div class="stat-top">${label}${icon(s)}</div><span class="stat-value">${n}</span><small>${note} <span aria-hidden="true">${icon('arrowUpRight')}</span></small></a>`).join('')}</section>
    <section class="panel website-card"><div class="site-info"><span class="workspace-icon">${icon('pages')}</span><div><strong>${escape(store.settings.name)}</strong><p>Your clinic website · ${records.filter(r=>['pages','treatments','articles'].includes(r.section)).length} exported routes</p></div></div><div class="heading-actions"><a href="#drafts" class="badge draft">${store.drafts.length} local drafts ${icon('arrowRight')}</a><a class="text-link" href="/" target="_blank" rel="noopener">Open website ${icon('arrowUpRight')}</a></div></section>
    <div class="overview-grid"><section class="panel"><div class="panel-header"><div><h2>Manage your website</h2><p>Everything your patients see, in one place.</p></div><span class="badge snapshot">6 sections</span></div><div class="content-list">${categories.map(s=>`<a class="content-row" href="#${s}"><span class="content-icon">${icon(s)}</span><div><strong>${labels[s]}</strong><small>${({pages:'Core pages and clinic information',treatments:'Services, care, and treatment details',doctors:'Your team and professional profiles',gallery:'Clinic spaces and team photography',clinic:'Your clinic story and featured photo collection',articles:'Journal, resources, and patient guidance'})[s]}</small></div><span class="count">${count(s)}</span><span class="arrow">${icon('caretRight')}</span></a>`).join('')}</div></section><section class="panel"><div class="panel-header"><div><h2>Content overview</h2><p>Your website’s content library.</p></div>${icon('overview')}</div><div class="distribution">${categories.map(s=>`<div class="bar-row"><div class="bar-label"><span>${labels[s]}</span><strong>${count(s)}</strong></div><div class="bar-track"><div class="bar-fill" style="width:${count(s)/Math.max(...categories.map(count),1)*100}%"></div></div></div>`).join('')}<p class="panel-note">Counts reflect the website snapshot and your local drafts.</p></div></section></div>
    <section class="panel"><div class="panel-header"><div><h2>Recent activity</h2><p>Keep track of the changes you make.</p></div><a href="#activity" class="text-link">View activity ${icon('arrowRight')}</a></div>${activity()}</section>`;}
  function photoTable(items){const isDoctor=section==='doctors',noun=isDoctor?'doctors':'photos';const reorder=!search.trim()&&filter==='all'&&sort==='default';return `<div class="clinic-order-help">${icon('info')}<span>${reorder?`Drag the handle to reorder ${noun}. You can also focus a handle and use ↑ / ↓.`:`Clear search and filters, and select Default order to reorder ${noun}.`}</span></div><div class="table-wrap clinic-table-wrap"><table class="clinic-table ${isDoctor?'doctor-table':''}"><thead><tr><th><span class="sr-only">Reorder</span></th><th>Order</th><th>${isDoctor?'Doctor':section==='gallery'?'Gallery photo':'Clinic photo'}</th>${isDoctor?'<th>Qualifications</th>':''}<th>Status</th><th>Actions</th></tr></thead><tbody>${items.map(r=>`<tr data-clinic-id="${escape(r.id)}"><td><button class="drag-handle" data-drag="${escape(r.id)}" ${reorder?'':'disabled'} aria-label="Reorder ${escape(r.title)}" aria-describedby="reorder-instructions">${icon('drag')}</button></td><td><span class="photo-order">${String(r.order||1).padStart(2,'0')}</span></td><td><div class="table-content">${safeURL(r.image)?`<img class="clinic-thumbnail" src="${safeURL(r.image)}" alt="${escape(r.alt||r.title)}" loading="lazy" draggable="false">`:`<span class="clinic-thumbnail placeholder">${icon(isDoctor?'doctors':'clinic')}</span>`}<div class="clinic-row-copy"><button class="title-button" data-edit="${escape(r.id)}">${escape(r.title)}</button><small title="${escape(isDoctor?r.specialty:r.description)}">${escape(isDoctor?r.specialty:r.description)}</small>${isDoctor?`<small>BM&amp;DC ${escape(r.registration||'Not provided')}</small>`:''}</div></div></td>${isDoctor?`<td><p class="doctor-qualification-summary" title="${escape(r.qualifications)}">${escape(r.qualifications||'Not provided')}</p></td>`:''}<td>${badge(r)}</td><td><button class="edit" data-edit="${escape(r.id)}" aria-label="Edit ${escape(r.title)}">${isDoctor?'Edit profile':'Edit photo'}</button></td></tr>`).join('')}</tbody></table></div><span id="reorder-instructions" class="sr-only">Use the up and down arrow keys to move this item one position. Order is saved as local drafts.</span>`;}
  function savePhotoOrder(ids,focusId=null){
    const previousDrafts=store.drafts,previousActivity=store.activity;
    const current=all().filter(r=>r.section===section);
    const changed=current.filter(r=>ids.indexOf(r.id)+1!==Number(r.order));
    if(!changed.length)return;
    const updates=changed.map(r=>({...r,order:ids.indexOf(r.id)+1,status:'Draft'}));
    store.drafts=[...store.drafts.filter(r=>!updates.some(update=>update.id===r.id)),...updates];
    store.activity=[{title:`Reordered ${labels[section]}${section==='doctors'?'':' photos'}`,time:new Date().toISOString()},...store.activity].slice(0,100);
    if(!save()){store.drafts=previousDrafts;store.activity=previousActivity;results(false);return;}
    results(false);$('[data-count="drafts"]').textContent=store.drafts.length;
    if(focusId)$$('[data-drag]').find(button=>button.dataset.drag===focusId)?.focus();
    toast(section==='doctors'?'Doctor order saved in this browser':'Photo order saved in this browser');
  }
  function bindPhotoReordering(){
    const body=$('.clinic-table tbody');if(!body)return;
    const handles=$$('.drag-handle:not(:disabled)');
    handles.forEach(handle=>{
      handle.onkeydown=e=>{if(!['ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();const ids=[...body.rows].map(row=>row.dataset.clinicId),from=ids.indexOf(handle.dataset.drag),to=from+(e.key==='ArrowUp'?-1:1);if(to<0||to>=ids.length)return;[ids[from],ids[to]]=[ids[to],ids[from]];savePhotoOrder(ids,handle.dataset.drag);};
      handle.onpointerdown=e=>{
        if(e.button!==0)return;e.preventDefault();handle.focus();
        const row=handle.closest('tr'),original=[...body.rows].map(r=>r.dataset.clinicId);let moved=false;
        handle.setPointerCapture(e.pointerId);row.classList.add('dragging');document.body.classList.add('clinic-reordering');
        function cleanup(){row.classList.remove('dragging');document.body.classList.remove('clinic-reordering');window.removeEventListener('pointermove',move);window.removeEventListener('pointerup',finish);window.removeEventListener('pointercancel',cancel);if(handle.hasPointerCapture(e.pointerId))handle.releasePointerCapture(e.pointerId);}
        function move(event){
          if(event.pointerId!==e.pointerId)return;
          const rows=[...body.rows],targetIndex=rows.findIndex(r=>{const rect=r.getBoundingClientRect();return event.clientY>=rect.top&&event.clientY<rect.bottom;});
          if(targetIndex>=0&&targetIndex!==rows.indexOf(row)){const remaining=rows.filter(r=>r!==row);body.insertBefore(row,remaining[targetIndex]||null);moved=true;}
          if(event.clientY>innerHeight-60)window.scrollBy(0,14);else if(event.clientY<100)window.scrollBy(0,-14);
        }
        function finish(){cleanup();if(moved)savePhotoOrder([...body.rows].map(r=>r.dataset.clinicId),handle.dataset.drag);}
        function cancel(){cleanup();original.forEach(id=>body.append([...body.rows].find(r=>r.dataset.clinicId===id)));}
        window.addEventListener('pointermove',move);window.addEventListener('pointerup',finish);window.addEventListener('pointercancel',cancel);
      };
    });
  }
  function locationQuery(record){return record.map_pin?.trim()||`${record.title}, ${record.address}`;}
  function locationMap(record){return `https://www.google.com/maps?q=${encodeURIComponent(locationQuery(record))}&z=17&t=m&iwloc=A&output=embed`;}
  function locationDirections(record){return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(locationQuery(record))}`;}
  function locationCards(items){return `<div class="location-grid">${items.map((record,index)=>`<article class="location-card"><header><span class="location-number">${String(index+1).padStart(2,'0')}</span>${badge(record)}</header><span class="eyebrow">${escape(record.area)}</span><h2>${escape(record.title)}</h2><p class="location-address">${escape(record.address)}</p><div class="location-contact"><span>Clinic phone</span><a href="tel:${escape(record.phone.replace(/[^+0-9]/g,''))}">${escape(record.phone)}</a>${record.hours?`<span>Opening hours</span><strong>${escape(record.hours)}</strong>`:''}</div><iframe src="${escape(locationMap(record))}" title="Google Maps — ${escape(record.title)}" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe><footer><a class="text-link" href="${escape(locationDirections(record))}" target="_blank" rel="noopener">Get directions ${icon('arrowUpRight')}</a><button data-edit="${escape(record.id)}">Edit location</button></footer></article>`).join('')}</div>`;}
  $('#preview-location-map').onclick=()=>{
    const form=$('#editor-form'),record={title:form.elements.title.value,address:form.elements.address.value,map_pin:form.elements.map_pin.value};
    if(!record.map_pin.trim()&&!record.address.trim()){toast('Enter an address or Google Maps pin to preview.');return;}
    $('#location-map-preview').hidden=false;$('#location-map-preview').innerHTML=`<iframe src="${escape(locationMap(record))}" title="Location map preview" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe><a class="text-link" href="${escape(locationDirections(record))}" target="_blank" rel="noopener">Open in Google Maps ${icon('arrowUpRight')}</a>`;
  };
  ['title','address','map_pin'].forEach(name=>$('#editor-form').elements[name].addEventListener('input',()=>{$('#location-map-preview').hidden=true;$('#location-map-preview').innerHTML='';}));
  function clinicIntro(){const page=all().find(r=>r.id==='/about-us/');return `<section class="panel clinic-intro"><span class="content-icon">${icon('clinic')}</span><div><span class="eyebrow">OUR CLINIC PAGE</span><h2>${escape(page?.title||'Our clinic')}</h2><p>Update the page introduction, then shape the photo collection below.</p></div><div class="heading-actions"><button data-edit="/about-us/">Edit introduction</button><a class="text-link" href="/about-us/" target="_blank" rel="noopener">View page ${icon('arrowUpRight')}</a></div></section>`;}
  function collection(){return `${section==='clinic'?clinicIntro():''}<section class="panel collection-panel"><div class="collection-heading"><div><h2>${section==='drafts'?'Your draft library':labels[section]+' library'}</h2><p>Find an item, review its details, and make your next update.</p></div><span class="library-icon">${icon(section)}</span></div><div class="toolbar"><label class="search" style="margin:0">${icon('search')}<input id="content-search" aria-label="Search content" placeholder="Search ${labels[section].toLowerCase()}…" value="${escape(search)}"></label><select id="status-filter" aria-label="Filter by status"><option value="all">All content</option><option value="Draft" ${filter==='Draft'?'selected':''}>Local drafts</option><option value="Website snapshot" ${filter==='Website snapshot'?'selected':''}>Website snapshot</option></select><select id="sort-content" aria-label="Sort content"><option value="default">Default order</option><option value="az">Title: A–Z</option><option value="za">Title: Z–A</option></select><span id="result-count" class="result-count"></span></div><div id="results"></div></section>`;}
  function results(animateResults=true){const items=all().filter(r=>(section==='drafts'?r.status==='Draft':r.section===section)&&(filter==='all'||r.status===filter)&&searchable(r).includes(search.toLowerCase()));if(['clinic','gallery','doctors','locations'].includes(section)&&sort==='default')items.sort((a,b)=>(Number(a.order)||1)-(Number(b.order)||1));if(sort!=='default')items.sort((a,b)=>a.title.localeCompare(b.title)*(sort==='za'?-1:1));$('#result-count').textContent=`${items.length} ${items.length===1?'item':'items'}`;
    $('#results').innerHTML=!items.length?`<div class="empty">${icon('search')}<h3>${section==='drafts'&&!search?'No drafts yet':'No matching content'}</h3><p>${section==='drafts'&&!search?'Open any website item to save your first draft.':'Try another search or clear your filters.'}</p><button id="clear-search">${section==='drafts'&&!search?'Browse pages':'Clear filters'}</button></div>`:section==='locations'?locationCards(items):['clinic','gallery','doctors'].includes(section)?photoTable(items):`<div class="table-wrap"><table><thead><tr><th>Content</th><th>Status</th><th>Actions</th></tr></thead><tbody>${items.map(r=>`<tr><td><div class="table-content">${['doctors','gallery','treatments','articles'].includes(r.section)&&safeURL(r.image)?`<img class="row-thumbnail" src="${safeURL(r.image)}" alt="" loading="lazy">`:`<span class="row-thumbnail placeholder">${icon(r.section)}</span>`}<div><button class="title-button" data-edit="${escape(r.id)}">${escape(r.title)}</button><small>${escape(r.section==='treatments'?(serviceCatalog().find(service=>service.id===r.service)?.name||'Service not selected')+(r.treatment?' · '+capitalizeText(r.treatment):''):r.url)}</small>${['treatments','articles'].includes(r.section)&&r.short_details?`<small>${escape(r.short_details.slice(0,100))}</small>`:''}</div></div></td><td>${badge(r)}</td><td><button class="edit" data-edit="${escape(r.id)}" aria-label="Edit ${escape(r.title)}">Edit</button>${r.section==='treatments'?` <button class="delete-treatment" data-delete-treatment="${escape(r.id)}" aria-label="Delete ${escape(r.title)}">Delete</button>`:''} <a class="text-link" href="${safeURL(r.url)}" target="_blank" rel="noopener" aria-label="Preview ${escape(r.title)}"><span class="preview-text">Preview</span> ${icon('arrowUpRight')}</a></td></tr>`).join('')}</tbody></table></div>`;
    if(animateResults)reveal($$('#results tbody tr, #results .media-card, #results .doctor-card, #results .empty'),16);
    bindEditors();bindPhotoReordering();if($('#clear-search'))$('#clear-search').onclick=()=>{if(section==='drafts'&&!search){location.hash='pages';return;}search='';filter='all';$('#content-search').value='';$('#status-filter').value='all';results();};
  }
  function bindEditors(){$$('[data-edit]').forEach(b=>b.onclick=()=>openEditor(all().find(r=>r.id===b.dataset.edit)));$$('[data-delete-treatment]').forEach(button=>button.onclick=()=>confirmTreatmentDeletion(button.dataset.deleteTreatment));}
  let treatmentToDelete=null;
  function confirmTreatmentDeletion(id){
    const record=all().find(record=>record.id===id&&record.section==='treatments');if(!record)return;
    treatmentToDelete=id;$('#delete-treatment-message').textContent=`Remove “${record.title}” from your treatments?`;
    openDialog($('#delete-treatment-dialog'));$('#cancel-delete-treatment').focus();
  }
  $('#cancel-delete-treatment').onclick=()=>closeDialog($('#delete-treatment-dialog'));
  $('#delete-treatment-dialog').addEventListener('close',()=>{treatmentToDelete=null;});
  $('#confirm-delete-treatment').onclick=async()=>{
    const record=all().find(record=>record.id===treatmentToDelete&&record.section==='treatments');if(!record)return;
    const previous={drafts:store.drafts,deletions:store.deletions,activity:store.activity};
    store.drafts=store.drafts.filter(draft=>draft.id!==record.id);
    store.deletions=[...(store.deletions||[]).filter(item=>item.id!==record.id),{id:record.id,section:'treatments',title:record.title,slug:record.slug||record.url.replace(/^\/+|\/+$/g,''),url:record.url,deleted_at:new Date().toISOString()}];
    store.activity=[{title:`Deleted treatment: ${record.title}`,time:new Date().toISOString()},...store.activity].slice(0,100);
    if(!save()){Object.assign(store,previous);return;}
    await closeDialog($('#delete-treatment-dialog'));render(true);$('#add').focus();toast('Treatment removed from this workspace');
  };
  function settings(){return `<section class="panel"><div class="panel-header"><div><h2>Workspace details</h2><p>These preferences apply to your local dashboard.</p></div></div><form id="settings-form" class="settings-form"><label>Workspace name<input name="name" required maxlength="100" value="${escape(store.settings.name)}"></label><label>Contact email<input name="email" required type="email" value="${escape(store.settings.email)}"></label><button class="primary">Save preferences</button></form></section>`;}
  function render(preserve=false){section=location.hash.slice(1)||'overview';if(!labels[section])section='overview';if(!preserve){search='';filter='all';sort='default';}$('#page-title').textContent=labels[section];$('#breadcrumb').textContent=labels[section];$('#page-description').textContent=descriptions[section]||'Your content, your team, and every first impression — all in one place.';document.title=`${labels[section]} · Dr. Teeth Website Console`;$$('[data-nav]').forEach(a=>{a.classList.toggle('active',a.dataset.nav===section);if(a.dataset.nav===section)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});$('[data-count="pages"]').textContent=count('pages');$('[data-count="drafts"]').textContent=store.drafts.length;setNavigation(false);$('#view').innerHTML=section==='overview'?overview():section==='activity'?`<section class="panel"><div class="panel-header"><h2>Draft activity</h2><span class="badge snapshot">${store.activity.length} changes</span></div>${activity()}</section>`:section==='settings'?settings():collection();
    $('#add').innerHTML=icon('plus')+' '+(({pages:'Add page',treatments:'Add treatment',doctors:'Add doctor',gallery:'Add photo',clinic:'Add clinic photo',locations:'Add location',articles:'Add article'})[section]||'Add content');bindEditors();if($('#content-search')){$('#sort-content').value=sort;$('#content-search').oninput=e=>{search=e.target.value;results(false);};$('#status-filter').onchange=e=>{filter=e.target.value;results();};$('#sort-content').onchange=e=>{sort=e.target.value;results();};results();}
    motion($('#view'),[{opacity:0,transform:'translateY(6px)'},{opacity:1,transform:'none'}],{duration:260});
    motion($('.page-heading'),[{opacity:.45,transform:'translateY(3px)'},{opacity:1,transform:'none'}],{duration:220});
    if(section==='overview')reveal($$('.stats .stat, .quick-edits > button'),30);
    if($('#settings-form'))$('#settings-form').onsubmit=e=>{e.preventDefault();const data=new FormData(e.target);store.settings={name:data.get('name').trim(),email:data.get('email').trim()};if(save()){updateWorkspace();toast('Workspace preferences saved');}};
  }
  function updateWorkspace(){$('.workspace strong').textContent=store.settings.name;}
  const serviceCatalog=()=>[...(window.DashboardServices||[]),...(store.services||[])].map(service=>({...service,name:capitalizeText(service.name),treatments:[...new Set([...service.treatments,...(store.treatmentOptions?.[service.id]||[])])]}));
  function fillServices(selected=''){
    $('#treatment-service').innerHTML='<option value="">Select a service</option>'+serviceCatalog().map(service=>`<option value="${escape(service.id)}">${escape(service.name)}</option>`).join('');
    $('#treatment-service').value=selected;fillTreatments();
  }
  function fillTreatments(selected=''){
    const service=serviceCatalog().find(item=>item.id===$('#treatment-service').value);
    $('#treatment-option').innerHTML='<option value="">No specific treatment</option>'+(service?.treatments||[]).map(name=>`<option value="${escape(name)}">${escape(capitalizeText(name))}</option>`).join('');
    $('#treatment-option').value=selected;$('#treatment-option').disabled=!service;$('#add-treatment-option').disabled=!service;
    $('#new-treatment').hidden=true;
  }
  $('#treatment-service').onchange=()=>{fillTreatments();$('#catalog-status').textContent='';};
  $('#add-service').onclick=()=>{$('#new-service').hidden=false;$('#new-service-name').focus();};
  $('#add-treatment-option').onclick=()=>{$('#new-treatment').hidden=false;$('#new-treatment-name').focus();};
  $$('[data-cancel-catalog]').forEach(button=>button.onclick=()=>{$('#'+button.dataset.cancelCatalog).hidden=true;});
  $('#create-service').onclick=()=>{
    const name=capitalizeText($('#new-service-name').value.trim());if(!name){$('#catalog-status').textContent='Enter a service name.';return;}
    const existing=serviceCatalog().find(service=>service.name.toLowerCase()===name.toLowerCase());
    const id=existing?.id||'service-'+crypto.randomUUID();
    if(!existing){store.services=store.services||[];store.services.push({id,name,treatments:[]});if(!save()){store.services.pop();return;}}
    fillServices(id);$('#new-service').hidden=true;$('#new-service-name').value='';$('#catalog-status').textContent=existing?'Existing service selected.':'Service added to this workspace.';
  };
  $('#create-treatment-option').onclick=()=>{
    const id=$('#treatment-service').value,name=capitalizeText($('#new-treatment-name').value.trim());if(!id||!name){$('#catalog-status').textContent='Select a service and enter a treatment name.';return;}
    const service=serviceCatalog().find(service=>service.id===id),existing=service.treatments.find(value=>value.toLowerCase()===name.toLowerCase());
    if(!existing){store.treatmentOptions=store.treatmentOptions||{};store.treatmentOptions[id]=store.treatmentOptions[id]||[];store.treatmentOptions[id].push(name);if(!save()){store.treatmentOptions[id].pop();return;}}
    fillTreatments(existing||name);$('#new-treatment-name').value='';$('#catalog-status').textContent=existing?'Existing treatment selected.':'Treatment added to this service.';
  };
  const validRichLink=value=>/^(https?:\/\/|mailto:|tel:|\/(?!\/)|#)/i.test(value)&&!/[\u0000-\u0020]/.test(value);
  function cleanDetails(html){
    const template=document.createElement('template');template.innerHTML=html;
    const allowed=new Set(['P','BR','B','STRONG','I','EM','U','S','STRIKE','H1','H2','H3','H4','H5','H6','UL','OL','LI','BLOCKQUOTE','DIV','PRE','CODE','HR','A']);
    function clean(node){for(const child of [...node.childNodes]){if(child.nodeType===1){
      if(['SCRIPT','STYLE','IFRAME','OBJECT'].includes(child.tagName)){child.remove();continue;}
      clean(child);
      if(!allowed.has(child.tagName)){child.replaceWith(...child.childNodes);continue;}
      const href=child.tagName==='A'?child.getAttribute('href'):null;
      const align=child.style.textAlign||child.getAttribute('align');
      for(const attr of [...child.attributes])child.removeAttribute(attr.name);
      if(href&&validRichLink(href))child.setAttribute('href',href);
      if(['P','DIV','H1','H2','H3','H4','H5','H6','BLOCKQUOTE','PRE','LI'].includes(child.tagName)&&['left','center','right','justify'].includes(align))child.style.textAlign=align;
    }else if(child.nodeType!==3)child.remove();}}
    clean(template.content);return template.innerHTML;
  }
  function syncDetails(){if(['treatments','articles'].includes($('#editor-form').elements.section.value))$('#editor-form').elements.details.value=cleanDetails($('#treatment-details').innerHTML);}
  $('#treatment-details').addEventListener('input',syncDetails);
  $('#treatment-details').addEventListener('paste',event=>{event.preventDefault();document.execCommand('insertText',false,event.clipboardData.getData('text/plain'));syncDetails();});
  $$('[data-rich]').forEach(button=>{button.onmousedown=event=>event.preventDefault();button.onclick=()=>{$('#treatment-details').focus();document.execCommand(button.dataset.rich,false,button.dataset.richValue||null);syncDetails();};});
  let richLinkRange=null;
  $('#rich-link').onmousedown=event=>event.preventDefault();
  $('#rich-link').onclick=()=>{
    const selection=window.getSelection();
    richLinkRange=selection.rangeCount&&$('#treatment-details').contains(selection.anchorNode)?selection.getRangeAt(0).cloneRange():null;
    $('#rich-link-panel').hidden=false;$('#rich-link-url').value='';$('#rich-link-error').textContent='';$('#rich-link-url').focus();
  };
  $('#rich-link-apply').onclick=()=>{
    const url=$('#rich-link-url').value.trim();
    if(!validRichLink(url)){$('#rich-link-error').textContent='Enter an HTTPS, email, phone, or local page address.';return;}
    const editor=$('#treatment-details');editor.focus();
    if(richLinkRange){const selection=window.getSelection();selection.removeAllRanges();selection.addRange(richLinkRange);}
    else{const range=document.createRange();range.selectNodeContents(editor);range.collapse(false);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);}
    if(window.getSelection().isCollapsed){const link=document.createElement('a');link.href=url;link.textContent=url;document.execCommand('insertHTML',false,link.outerHTML);}
    else document.execCommand('createLink',false,url);
    syncDetails();$('#rich-link-panel').hidden=true;richLinkRange=null;
  };
  $('#rich-link-cancel').onclick=()=>{$('#rich-link-panel').hidden=true;richLinkRange=null;$('#treatment-details').focus();};
  let uploadController=null,uploading=false;
  function showImagePreview(){
    const url=$('#editor-form').elements.image.value;
    $('#upload-preview').hidden=!url;
    if(url)$('#image-preview').src=safeURL(url);else $('#image-preview').removeAttribute('src');
  }
  function setUploading(value){
    uploading=value;
    $('#image-file').disabled=value;
    $('#editor-form button[type="submit"]').disabled=value;
    $('.image-upload').setAttribute('aria-busy',String(value));
  }
  function resetUpload(){uploadController?.abort();uploadController=null;setUploading(false);}
  $('#editor').addEventListener('close',resetUpload);
  $('#image-file').addEventListener('change',async event=>{
    const status=$('#upload-status');
    if(event.target.files.length>1){status.textContent='Choose only one image.';event.target.value='';return;}
    const file=event.target.files[0];if(!file)return;
    if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>10*1024*1024){status.textContent='Choose a JPEG, PNG, or WebP image up to 10 MB.';event.target.value='';return;}
    const controller=new AbortController();uploadController=controller;setUploading(true);
    status.textContent='Uploading and optimizing image…';
    try{
      const payload=new FormData();payload.append('image',file);
      const token=document.cookie.split('; ').find(part=>part.startsWith('csrftoken='))?.slice(10)||'';
      const response=await fetch(document.body.dataset.uploadUrl,{method:'POST',body:payload,credentials:'same-origin',headers:{'X-CSRFToken':decodeURIComponent(token)},signal:controller.signal});
      const result=await response.json().catch(()=>({error:'Image uploads require the Django server. Please open the dashboard through Django.'}));
      if(!response.ok)throw Error(result.error||'Upload failed. Please try again.');
      if(uploadController!==controller)return;
      $('#editor-form').elements.image.value=result.url;showImagePreview();
      status.textContent=`Uploaded · ${result.width} × ${result.height} · Save draft to use this image.`;
    }catch(error){if(error.name!=='AbortError'&&uploadController===controller)status.textContent=error.message;}
    finally{if(uploadController===controller){uploadController=null;setUploading(false);event.target.value='';}}
  });
  function titleSlug(title,fallback='treatment'){
    return title.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/['’]/g,'').replace(/&/g,' and ').replace(/[^\p{L}\p{N}\p{M}]+/gu,'-').replace(/^-+|-+$/g,'').slice(0,100).replace(/-+$/g,'')||fallback;
  }
  function uniqueContentSlug(title){
    const base=titleSlug(title,$('#editor-form').elements.section.value==='articles'?'article':'treatment'),used=new Set(['dashboard','static','media']);
    let latest=[];try{latest=JSON.parse(localStorage.getItem(key))?.drafts||[];}catch{}
    for(const record of [...records,...store.drafts,...latest,...(store.deletions||[])]){
      if(record.id===editing)continue;
      if(record.slug)used.add(record.slug.toLowerCase());
      if(record.url)used.add(record.url.split(/[?#]/)[0].replace(/^\/+|\/+$/g,'').toLowerCase());
    }
    let slug=base,suffix=2;while(used.has(slug))slug=`${base}-${suffix++}`;return slug;
  }
  function contentSlug(){
    const previous=all().find(record=>record.id===editing);
    return previous?.slug||(previous?.url&&!['/services/','/blog/'].includes(previous.url)?previous.url.replace(/^\/+|\/+$/g,''):uniqueContentSlug($('#editor-form').elements.title.value));
  }
  function updateSlugPreview(){
    const preview=$('#treatment-slug-preview'),form=$('#editor-form');preview.hidden=!['treatments','articles'].includes(form.elements.section.value);
    preview.textContent=form.elements.title.value.trim()?`Slug: ${contentSlug()}`:'The slug is generated automatically from the title.';
  }
  $('#editor-form').elements.title.addEventListener('input',updateSlugPreview);
  function updateEditorFields(){
    const form=$('#editor-form'),isDoctor=form.elements.section.value==='doctors',isClinic=['clinic','gallery'].includes(form.elements.section.value),isTreatment=form.elements.section.value==='treatments',isLocation=form.elements.section.value==='locations',isArticle=form.elements.section.value==='articles';
    $('#editor-form').dataset.section=form.elements.section.value;
    $('#location-fields').hidden=!isLocation;$('#location-fields').disabled=!isLocation;$('.image-upload').hidden=isLocation;
    $('#article-fields').hidden=!isArticle;$('#article-fields').disabled=!isArticle;
    $('#content-fields').hidden=!(isTreatment||isArticle);$('#content-fields').disabled=!(isTreatment||isArticle);
    $('#treatment-fields').hidden=!isTreatment;$('#treatment-fields').disabled=!isTreatment;
    $('#treatment-details').contentEditable=String(isTreatment||isArticle);
    $('#treatment-details').dataset.placeholder=isArticle?'Write the article details…':'Write the treatment details…';
    $('#short-details-help').textContent=isArticle?'A brief summary for article cards and previews.':'A brief summary for treatment cards.';
    $('#image-file').multiple=false;
    $('#image-field-label').textContent=isTreatment?'Treatment thumbnail':isArticle?'Article thumbnail':'Image';
    $('#image-field-help').textContent=(isTreatment||isArticle)?'Upload one thumbnail (JPEG, PNG, or WebP, up to 10 MB). A new upload replaces the current thumbnail.':'Choose a JPEG, PNG, or WebP up to 10 MB. Uploads are stored in the gallery.';
    $('#image-picker-label').textContent=(isTreatment||isArticle)?'Choose thumbnail':'Choose an image';
    $('#clinic-fields legend').textContent=form.elements.section.value==='gallery'?'Gallery photo details':'Clinic photo details';
    $('#clinic-fields').hidden=!isClinic;$('#clinic-fields').disabled=!isClinic;
    form.elements.url.closest('label').hidden=isClinic;form.elements.url.disabled=isClinic;
    $('#doctor-fields').hidden=!isDoctor;
    $('#doctor-fields').disabled=!isDoctor;
    form.elements.description.required=!isDoctor&&!isTreatment&&!isLocation&&!isArticle;
    $('#editor-name-label').textContent=isDoctor?'Doctor name':isLocation?'Branch name':'Title';
    for(const name of ['description','url']){
      const field=form.elements.namedItem(name);
      field.closest('label').hidden=isDoctor||isLocation||((isTreatment||isArticle)&&name==='description')||((isClinic||isTreatment||isArticle)&&name==='url');
      field.disabled=isDoctor||isLocation||((isTreatment||isArticle)&&name==='description')||((isClinic||isTreatment||isArticle)&&name==='url');
    }
    updateSlugPreview();
    $('#editor-title').textContent=isArticle?(editing?'Edit article':'Add article'):isLocation?(editing?'Edit location':'Add location'):isDoctor?(editing?'Edit doctor':'Add doctor'):(isClinic?(editing?'Edit photo':'Add photo'):(editing?'Edit content':'Add content'));
    if(isClinic)form.elements.url.value=form.elements.section.value==='gallery'?'/gallery/':'/about-us/';
    if(isDoctor){
      if(!form.elements.url.value)form.elements.url.value='/our-doctors/';
    }
  }
  function openEditor(record){
    editing=record?.id||null;
    resetUpload();const form=$('#editor-form');form.reset();
    for(const name of ['title','section','description','url','image','alt','order',...doctorFields.filter(name=>name!=='appointment_url')])form.elements.namedItem(name).value=record?.[name]||(name==='section'?(Object.keys(descriptions).includes(section)&&!['activity','settings','drafts'].includes(section)?section:'pages'):'');
    if(['clinic','gallery'].includes(form.elements.section.value)&&!record)form.elements.order.value=Math.max(0,...all().filter(r=>r.section===form.elements.section.value).map(r=>Number(r.order)||0))+1;
    updateEditorFields();
    if(['treatments','articles'].includes(form.elements.section.value)){
      form.elements.short_details.value=record?.short_details??record?.description??'';
      $('#treatment-details').innerHTML=cleanDetails(record?.details||`<p>${escape(record?.description||'')}</p>`);
      if(form.elements.section.value==='treatments'){const service=record?.service||serviceCatalog().find(item=>record?.url===`/${item.id}/`)?.id||'';
      fillServices(service);fillTreatments(record?.treatment||'');}syncDetails();
    }
    if(form.elements.section.value==='articles'){for(const name of ['seo_title','meta_description','keywords','canonical_url','og_title','og_description','image_alt'])form.elements[name].value=record?.[name]||'';form.elements.robots.value=record?.robots||'index,follow';}
    if(form.elements.section.value==='locations'){for(const name of ['area','address','phone','hours','map_pin'])form.elements[name].value=record?.[name]||'';form.elements.location_order.value=record?.order||Math.max(0,...all().filter(item=>item.section==='locations').map(item=>Number(item.order)||0))+1;}
    $('#location-map-preview').hidden=true;$('#location-map-preview').innerHTML='';
    $('#rich-link-panel').hidden=true;richLinkRange=null;$('#new-service').hidden=true;$('#new-treatment').hidden=true;$('#catalog-status').textContent='';
    showImagePreview();$('#upload-status').textContent=form.elements.image.value?'Current image · Choose a file to replace it.':'No image selected.';$('#discard-notice').hidden=true;
    editorInitial=JSON.stringify(Object.fromEntries(new FormData(form)));
    openDialog($('#editor'));$('.editor-body').scrollTop=0;
  }
  $('#add').onclick=()=>openEditor();function closeEditor(){syncDetails();if(JSON.stringify(Object.fromEntries(new FormData($('#editor-form'))))!==editorInitial){$('#discard-notice').hidden=false;motion($('#discard-notice'),[{opacity:0,transform:'translateY(-4px)'},{opacity:1,transform:'none'}]);$('#keep-editing').focus();}else closeDialog($('#editor'));}
  $('#close-editor').onclick=$('#cancel-editor').onclick=closeEditor;$('#editor').addEventListener('cancel',e=>{e.preventDefault();closeEditor();});$('#keep-editing').onclick=()=>{$('#discard-notice').hidden=true;$('#editor-form input[name="title"]').focus();};$('#discard-editing').onclick=()=>closeDialog($('#editor'));
  $('#editor-form').onsubmit=e=>{e.preventDefault();if(uploading){toast('Wait for the image upload to finish.');return;}syncDetails();const data=Object.fromEntries(new FormData(e.target));Object.keys(data).forEach(k=>data[k]=data[k].trim());if(['clinic','gallery'].includes(data.section)){data.url=data.section==='gallery'?'/gallery/':'/about-us/';data.order=Number(data.order);if(!data.alt||!data.image||!Number.isInteger(data.order)||data.order<1){toast('Enter an image, alt text, and a display order of 1 or more.');return;}}if(data.section==='locations'){data.url='/contact/';data.description=data.address;data.order=Number(data.location_order);delete data.location_order;if(!data.area||!data.address||!/^\+?[0-9 ()-]{6,40}$/.test(data.phone)||!Number.isInteger(data.order)||data.order<1){toast('Enter an area, address, valid phone number, and display order.');return;}}if(data.section==='articles'){
      data.slug=contentSlug();const previous=all().find(record=>record.id===editing);data.url=previous?.url&&!['/blog/','/services/'].includes(previous.url)?previous.url:`/${data.slug}/`;
      data.details=cleanDetails(data.details);const text=document.createElement('div');text.innerHTML=data.details;data.description=text.textContent.trim();
      if(!data.short_details||!data.description){toast('Enter short details and article details.');return;}
      if(data.canonical_url&&!/^https?:\/\//i.test(data.canonical_url)){toast('Canonical URLs must begin with https:// or http://.');return;}
      if(!['index,follow','noindex,follow','noindex,nofollow'].includes(data.robots)){toast('Select a valid search engine visibility option.');return;}
      const keywords=new Map(data.keywords.split(',').map(word=>word.trim()).filter(Boolean).map(word=>[word.toLowerCase(),word]));data.keywords=[...keywords.values()].join(', ');
    }if(data.section==='treatments'){data.title=capitalizeText(data.title);data.slug=contentSlug();const previous=all().find(r=>r.id===editing);data.url=previous?.url&&!['/services/','/blog/'].includes(previous.url)?previous.url:`/${data.slug}/`;data.details=cleanDetails(data.details);const text=document.createElement('div');text.innerHTML=data.details;data.description=text.textContent.trim();if(!serviceCatalog().some(service=>service.id===data.service)||!data.short_details||!data.description){toast('Select a service and enter short details and details.');return;}if(data.treatment&&!serviceCatalog().find(service=>service.id===data.service).treatments.includes(data.treatment)){toast('Choose a treatment belonging to the selected service.');return;}}if(data.section==='doctors'){const previous=all().find(r=>r.id===editing);Object.assign(data,{description:previous?.description||'',url:previous?.url||'/our-doctors/',image:data.image||previous?.image||'',appointment_url:previous?.appointment_url||'/appointment/',order:Number(previous?.order)||Math.max(0,...all().filter(r=>r.section==='doctors').map(r=>Number(r.order)||0))+1});}if(!data.title||(!data.description&&data.section!=='doctors')||!/^\/(?!\/)/.test(data.url)){toast('Enter a title, required details, and website path beginning with /.');return;}if(data.section==='doctors'&&(!data.specialty||!data.qualifications)){toast('Enter a specialty and qualifications.');return;}if(data.image&&!/^(\/(?!\/)|https?:\/\/)/.test(data.image)){toast('Use a local image path or an HTTPS image URL.');return;}const entry={...data,id:editing||`draft-${crypto.randomUUID()}`,status:'Draft'};store.drafts=store.drafts.filter(r=>r.id!==entry.id);store.drafts.push(entry);store.activity.unshift({title:`Saved draft: ${entry.title}`,time:new Date().toISOString()});store.activity=store.activity.slice(0,100);if(save()){closeDialog($('#editor'));render(true);toast('Draft saved in this browser');}};
  $('#export').onclick=()=>{const blob=new Blob([JSON.stringify({drafts:store.drafts.map(withRecordDetails),deletions:store.deletions||[],services:serviceCatalog(),settings:store.settings},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='dr-teeth-website-drafts.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Drafts exported');};
  $('#menu').onclick=()=>setNavigation(!$('#sidebar').classList.contains('open'));$('#nav-backdrop').onclick=()=>setNavigation(false);
  $('#account').onclick=()=>openDialog($('#account-dialog'));$('#close-account').onclick=()=>closeDialog($('#account-dialog'));
  function globalResults(){const query=$('#global-query').value.toLowerCase().trim();const items=all().filter(r=>!query||`${searchable(r)} ${labels[r.section]}`.toLowerCase().includes(query)).slice(0,8);queryIndex=0;$('#global-results').innerHTML=items.length?items.map((r,i)=>`<button class="command-result ${i===0?'selected':''}" data-record="${escape(r.id)}"><span class="content-icon">${icon(r.section)}</span><span><strong>${escape(r.title)}</strong><small>${labels[r.section]} · ${r.status}</small></span><span>${icon('enter')}</span></button>`).join(''):'<div class="empty"><h3>No results found</h3><p>Try a different title or content type.</p></div>';$$('.command-result').forEach(b=>b.onclick=async()=>{await closeDialog($('#search-dialog'));openEditor(all().find(r=>r.id===b.dataset.record));});}
  function openSearch(){$('#global-query').value='';globalResults();openDialog($('#search-dialog'));$('#global-query').focus();}
  ['search-dialog','account-dialog'].forEach(id=>$('#'+id).addEventListener('cancel',e=>{e.preventDefault();closeDialog($('#'+id));}));
  $('#open-search').onclick=openSearch;$('#close-search').onclick=()=>closeDialog($('#search-dialog'));$('#global-query').oninput=globalResults;
  $('#global-query').onkeydown=e=>{const items=$$('.command-result');if(!items.length)return;if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();queryIndex=(queryIndex+(e.key==='ArrowDown'?1:-1)+items.length)%items.length;items.forEach((b,i)=>b.classList.toggle('selected',i===queryIndex));items[queryIndex].scrollIntoView({block:'nearest'});}if(e.key==='Enter'){e.preventDefault();items[queryIndex].click();}};
  document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();if(!$('#editor').open)openSearch();}});
  window.addEventListener('hashchange',()=>{render();window.scrollTo({top:0});});document.addEventListener('keydown',e=>{if(e.key==='Escape'){setNavigation(false);}});
  fetch(document.body.dataset.contentUrl).then(r=>{if(!r.ok)throw Error('Content unavailable');return r.json();}).then(data=>{records=[...data,...(window.DashboardLocations||[])];updateWorkspace();render();}).catch(()=>{$('#view').innerHTML='<div class="panel empty"><h3>Could not load website content</h3><p>Reload the page to try again.</p></div>';});
})();
