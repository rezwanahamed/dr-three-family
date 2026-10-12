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
  const iconNames={faqs:'info',overview:'squares-four',pages:'file-text',treatments:'first-aid',doctors:'users',gallery:'images',clinic:'buildings',locations:'buildings',articles:'article',activity:'pulse',settings:'gear-six',download:'download-simple',upload:'arrow-up',plus:'plus',info:'info',search:'magnifying-glass',caretDown:'caret-down',caretRight:'caret-right',arrowUpRight:'arrow-up-right',arrowRight:'arrow-right',close:'x',menu:'list',enter:'arrow-elbow-down-left',up:'arrow-up',down:'arrow-down',drag:'dots-six-vertical'};
  const icon=name=>`<svg class="phosphor-icon" data-phosphor="${iconNames[name]||iconNames.pages}" aria-hidden="true" focusable="false" viewBox="0 0 256 256" fill="currentColor">${window.DashboardPhosphor[iconNames[name]||iconNames.pages]}</svg>`;
  $$('[data-icon]').forEach(el=>el.innerHTML=icon(el.dataset.icon));
  const labels={faqs:'FAQs',overview:'Overview',pages:'Pages',treatments:'Treatments',doctors:'Doctors',gallery:'Gallery',clinic:'Our clinic',locations:'Locations',articles:'Articles & resources',activity:'Activity',settings:'Settings',drafts:'Local drafts'};
  const descriptions={faqs:'Manage clear, helpful answers to your patients’ questions, organized by treatment topic.',locations:'Manage your clinic branches, contact details, and Google Maps locations.',clinic:'Manage the clinic story and photo collection on your Our clinic page.',drafts:'Review and manage your saved website changes.',pages:'Manage the pages that help patients get to know your clinic.',treatments:'Keep your treatment information clear, helpful, and up to date.',doctors:'Introduce the people behind your patients’ smiles.',gallery:'A closer look at your clinic, your team, and your care.',articles:'Helpful answers and stories for healthier smiles.',activity:'A record of your draft changes in this browser.',settings:'Manage your local website workspace preferences.'};
  const key='drteeth-dashboard-v1'; let store={drafts:[],deletions:[],activity:[],settings:{name:'Dr. Teeth Family Dental',email:'info@drteethfamilydental.com'}};
  try {const saved=JSON.parse(localStorage.getItem(key));if(saved&&Array.isArray(saved.drafts)&&Array.isArray(saved.activity))store={...store,...saved};}catch{}
  let publishedSettings={};
  let records=[],section='overview',editing=null,search='',filter='all',sort='default',editorInitial='',queryIndex=0;
  let tablePage=1,tablePageSize=10;
  try{const size=Number(localStorage.getItem(key+'-page-size'));if([10,25,50,100].includes(size))tablePageSize=size;}catch{}
  const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safeURL=value=>/^(\/(?!\/)|https?:\/\/)/.test(value||'')?escape(value):'';
  const doctorFields=['specialty','qualifications','training','position','registration','appointment_url'];
  function withRecordDetails(record){
    if(record.section==='treatments'){const source=records.find(r=>r.id===record.id);record={show_on_homepage:source?.show_on_homepage??false,homepage_order:source?.homepage_order??0,...record};}
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
  const searchable=r=>[r.title,r.description,r.short_details,r.keywords,r.seo_title,r.service,r.treatment,r.topic,faqTopics().find(t=>t.id===r.topic)?.title,r.gallery_category,r.area,r.address,r.phone,r.hours,...doctorFields.map(name=>r[name])].join(' ').toLowerCase();


  const count=s=>all().filter(r=>r.section===s).length;
  const badge=r=>`<span class="badge ${r.status==='Draft'?'draft':'snapshot'}"><span class="badge-dot" aria-hidden="true"></span>${r.status==='Draft'?'Local draft':'Website snapshot'}</span>`;
  function toast(message){$('#toast').textContent=message;$('#toast').classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').classList.remove('show'),3000);}
  function updatePublishIndicator(){
    const button=$('#publish-changes');if(!button)return;
    if(!button.querySelector('.publish-draft-point'))button.insertAdjacentHTML('beforeend','<span class="publish-draft-point" aria-hidden="true"></span>');
    const contentChanges=Object.entries(store).some(([name,value])=>!['activity','settings','homepageTreatmentOrder'].includes(name)&&(Array.isArray(value)?value.length>0:value&&typeof value==='object'?Object.keys(value).length>0:false));
    const homepageChanges=Object.hasOwn(store,'homepageTreatmentOrder')&&JSON.stringify(homepageTreatmentIds())!==JSON.stringify(records.filter(r=>r.section==='treatments'&&r.show_on_homepage).sort((a,b)=>a.homepage_order-b.homepage_order).map(r=>r.id));
    const settingsChanges=['name','email'].some(name=>(store.settings?.[name]??({name:'Dr. Teeth Family Dental',email:'info@drteethfamilydental.com'})[name])!==(publishedSettings[name]??({name:'Dr. Teeth Family Dental',email:'info@drteethfamilydental.com'})[name]));
    const pending=contentChanges||homepageChanges||settingsChanges;
    button.classList.toggle('has-drafts',pending);
    button.setAttribute('aria-label',pending?'Publish changes · Unpublished changes pending':'Publish changes');
    button.title=pending?'You have unpublished changes. Publish to update your website.':'Publish changes to your website';
  }
  function save(){try{localStorage.setItem(key,JSON.stringify(store));scheduleServerSave();updatePublishIndicator();return true;}catch{toast('Could not save locally. Check browser storage permissions.');return false;}}
  function activity(){return store.activity.length?`<ul class="activity-list">${store.activity.slice(0,12).map(a=>`<li>${escape(a.title)}<small>${escape(new Date(a.time).toLocaleString())}</small></li>`).join('')}</ul>`:`<div class="empty">${icon('activity')}<h3>A fresh start for your website</h3><p>Your saved drafts will appear here. Open any content item to make your first edit.</p></div>`;}
  function draftQueue(){return `<section class="panel draft-queue"><div class="panel-header"><div><h2>Ready for your next edit</h2><p>${store.drafts.length?'Pick up where you left off.':'Start with the content your patients see first.'}</p></div><a href="#drafts" class="text-link">View drafts ${icon('arrowRight')}</a></div><div class="quick-edits">${(store.drafts.length?store.drafts.slice(-3).reverse():records.filter(r=>['/','/services/','/our-doctors/'].includes(r.id))).map(r=>`<button data-edit="${escape(r.id)}"><span class="content-icon">${icon(r.section)}</span><span><strong>${escape(r.title)}</strong><small>${r.status==='Draft'?'Continue draft':'Edit '+labels[r.section].toLowerCase()}</small></span><span class="quick-arrow">${icon('arrowUpRight')}</span></button>`).join('')}</div></section>`;}
  function overview(){const categories=['pages','treatments','doctors','clinic','locations','gallery','articles','faqs'];return `
    ${draftQueue()}<section class="stats" aria-label="Website content summary">${[['pages','Core pages',count('pages'),'Clinic information & key pages'],['treatments','Treatments',count('treatments'),'Treatment pages in your website'],['doctors','Doctors',count('doctors'),'Profiles in your team section'],['gallery','Gallery photos',count('gallery'),'Images in your clinic gallery']].map(([s,label,n,note])=>`<a href="#${s}" class="stat"><div class="stat-top">${label}${icon(s)}</div><span class="stat-value">${n}</span><small>${note} <span aria-hidden="true">${icon('arrowUpRight')}</span></small></a>`).join('')}</section>
    <section class="panel website-card"><div class="site-info"><span class="workspace-icon">${icon('pages')}</span><div><strong>${escape(store.settings.name)}</strong><p>Your clinic website · ${records.filter(r=>['pages','treatments','articles'].includes(r.section)).length} exported routes</p></div></div><div class="heading-actions"><a href="#drafts" class="badge draft">${store.drafts.length} local drafts ${icon('arrowRight')}</a><a class="text-link" href="/" target="_blank" rel="noopener">Open website ${icon('arrowUpRight')}</a></div></section>
    <div class="overview-grid"><section class="panel"><div class="panel-header"><div><h2>Manage your website</h2><p>Everything your patients see, in one place.</p></div><span class="badge snapshot">6 sections</span></div><div class="content-list">${categories.map(s=>`<a class="content-row" href="#${s}"><span class="content-icon">${icon(s)}</span><div><strong>${labels[s]}</strong><small>${({pages:'Core pages and clinic information',treatments:'Services, care, and treatment details',doctors:'Your team and professional profiles',gallery:'Clinic spaces and team photography',clinic:'Your clinic story and featured photo collection',articles:'Journal, resources, and patient guidance'})[s]}</small></div><span class="count">${count(s)}</span><span class="arrow">${icon('caretRight')}</span></a>`).join('')}</div></section><section class="panel"><div class="panel-header"><div><h2>Content overview</h2><p>Your website’s content library.</p></div>${icon('overview')}</div><div class="distribution">${categories.map(s=>`<div class="bar-row"><div class="bar-label"><span>${labels[s]}</span><strong>${count(s)}</strong></div><div class="bar-track"><div class="bar-fill" style="width:${count(s)/Math.max(...categories.map(count),1)*100}%"></div></div></div>`).join('')}<p class="panel-note">Counts reflect the website snapshot and your local drafts.</p></div></section></div>
    <section class="panel"><div class="panel-header"><div><h2>Recent activity</h2><p>Keep track of the changes you make.</p></div><a href="#activity" class="text-link">View activity ${icon('arrowRight')}</a></div>${activity()}</section>`;}
  function photoTable(items){const isDoctor=section==='doctors',noun=isDoctor?'doctors':'photos';const reorder=!search.trim()&&filter==='all'&&sort==='default';return `<div class="clinic-order-help">${icon('info')}<span>${reorder?`Drag the handle to reorder ${noun}. You can also focus a handle and use ↑ / ↓.`:`Clear search and filters, and select Default order to reorder ${noun}.`}</span></div><div class="table-wrap clinic-table-wrap"><table class="clinic-table ${isDoctor?'doctor-table':section==='gallery'?'gallery-table':''}"><thead><tr><th><span class="sr-only">Reorder</span></th><th>Order</th><th>${isDoctor?'Doctor':section==='gallery'?'Gallery photo':'Clinic photo'}</th>${isDoctor?'<th>Qualifications</th>':''}<th>Status</th><th>Actions</th></tr></thead><tbody>${items.map(r=>`<tr data-clinic-id="${escape(r.id)}"><td><button class="drag-handle" data-drag="${escape(r.id)}" ${reorder?'':'disabled'} aria-label="Reorder ${escape(r.title)}" aria-describedby="reorder-instructions">${icon('drag')}</button></td><td><span class="photo-order">${String(r.order||1).padStart(2,'0')}</span></td><td><div class="table-content">${safeURL(r.image)?`<img class="clinic-thumbnail" src="${safeURL(r.image)}" alt="${escape(r.alt||r.title)}" loading="lazy" draggable="false">`:`<span class="clinic-thumbnail placeholder">${icon(isDoctor?'doctors':'clinic')}</span>`}<div class="clinic-row-copy"><button class="title-button" data-edit="${escape(r.id)}">${escape(r.title)}</button><small title="${escape(isDoctor?r.specialty:r.description)}">${escape(isDoctor?r.specialty:r.description)}</small>${section==='gallery'&&r.gallery_category?`<small>${escape(r.gallery_category)}</small>`:''}${isDoctor?`<small>BM&amp;DC ${escape(r.registration||'Not provided')}</small>`:''}</div></div></td>${isDoctor?`<td><p class="doctor-qualification-summary" title="${escape(r.qualifications)}">${escape(r.qualifications||'Not provided')}</p></td>`:''}<td>${badge(r)}</td><td><div class="photo-row-actions"><button class="edit" data-edit="${escape(r.id)}" aria-label="Edit ${escape(r.title)}">${isDoctor?'Edit profile':'Edit photo'}</button>${section==='gallery'?` <button class="delete-content" data-delete-content="${escape(r.id)}" aria-label="Delete ${escape(r.title)}">Delete</button>`:''}</div></td></tr>`).join('')}</tbody></table></div><span id="reorder-instructions" class="sr-only">Use the up and down arrow keys to move this item one position. Order is saved as local drafts.</span>`;}
  function savePhotoOrder(ids,focusId=null){
    const previousDrafts=store.drafts,previousActivity=store.activity;
    const current=all().filter(r=>r.section===section).sort((a,b)=>(Number(a.order)||1)-(Number(b.order)||1));
    if(ids.length<current.length){const visible=new Set(ids);let index=0;ids=current.map(r=>visible.has(r.id)?ids[index++]:r.id);}
    const changed=current.filter(r=>ids.indexOf(r.id)+1!==Number(r.order));
    if(!changed.length)return;
    const updates=changed.map(r=>({...r,order:ids.indexOf(r.id)+1,status:'Draft'}));
    store.drafts=[...store.drafts.filter(r=>!updates.some(update=>update.id===r.id)),...updates];
    store.activity=[{title:`Reordered ${labels[section]}${section==='doctors'?'':' photos'}`,time:new Date().toISOString()},...store.activity].slice(0,100);
    if(!save()){store.drafts=previousDrafts;store.activity=previousActivity;results(false);return;}
    if(focusId)tablePage=Math.floor(ids.indexOf(focusId)/tablePageSize)+1;
    results(false);$('[data-count="drafts"]').textContent=store.drafts.length;
    if(focusId)$$('[data-drag]').find(button=>button.dataset.drag===focusId)?.focus();
    toast(section==='doctors'?'Doctor order saved in this browser':'Photo order saved in this browser');
  }
  function bindPhotoReordering(){
    const body=$('.clinic-table tbody');if(!body)return;
    const handles=$$('.drag-handle:not(:disabled)');
    handles.forEach(handle=>{
      handle.onkeydown=e=>{if(!['ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();const ids=all().filter(r=>r.section===section).sort((a,b)=>(Number(a.order)||1)-(Number(b.order)||1)).map(r=>r.id),from=ids.indexOf(handle.dataset.drag),to=from+(e.key==='ArrowUp'?-1:1);if(to<0||to>=ids.length)return;[ids[from],ids[to]]=[ids[to],ids[from]];savePhotoOrder(ids,handle.dataset.drag);};
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
  const faqTopics=()=>{
    const seeded=window.DashboardFAQTopics||[],custom=store.faqTopics||[];
    const topics=[...seeded.map(topic=>custom.find(item=>item.id===topic.id)||topic),...custom.filter(topic=>!seeded.some(item=>item.id===topic.id))].filter(topic=>!(store.deletedFAQTopics||[]).some(item=>item.id===topic.id));
    const order=store.faqTopicOrder||[],fallback=new Map(topics.map((topic,index)=>[topic.id,index]));const rank=id=>order.includes(id)?order.indexOf(id):order.length+fallback.get(id);
    return topics.sort((a,b)=>rank(a.id)-rank(b.id));
  };
  let faqTopicFilter='';

  let editingTopic=null,removingTopic=null;
  const topicQuestions=id=>all().filter(r=>r.section==='faqs'&&r.topic===id);
  function topicList(){
    $('#faq-topic-list').innerHTML=faqTopics().map((topic,index)=>`<div class="faq-topic-row" data-topic-id="${escape(topic.id)}"><div class="faq-topic-info"><button type="button" class="drag-handle" data-topic-drag="${escape(topic.id)}" aria-label="Reorder ${escape(topic.title)}" title="Drag to reorder, or use up/down arrow keys">${icon('drag')}</button><span class="faq-topic-number" aria-label="Order ${index+1}">${String(index+1).padStart(2,'0')}</span><div><strong>${escape(topic.title)}</strong><small>${topicQuestions(topic.id).length} questions</small></div></div><div><button type="button" data-edit-topic="${escape(topic.id)}" aria-label="Edit topic ${escape(topic.title)}">Edit</button><button type="button" class="delete-content" data-remove-topic="${escape(topic.id)}" aria-label="Remove topic ${escape(topic.title)}">Remove</button></div></div>`).join('')||'<p class="field-help">No topics yet. Use Add topic to create your first topic.</p>';
    bindTopicReordering();
    $$('[data-edit-topic]').forEach(button=>button.onclick=()=>editTopic(button.dataset.editTopic));
    $$('[data-remove-topic]').forEach(button=>button.onclick=()=>removeTopic(button.dataset.removeTopic));
  }
  function saveTopicOrder(ids,focusId){
    if(ids.join('|')===faqTopics().map(topic=>topic.id).join('|'))return;
    const previous={faqTopicOrder:store.faqTopicOrder,activity:store.activity};
    store.faqTopicOrder=ids;store.activity=[{title:'Reordered FAQ topics',time:new Date().toISOString()},...store.activity].slice(0,100);
    if(!save()){Object.assign(store,previous);topicList();return;}
    render(true);$$('[data-topic-drag]').find(handle=>handle.dataset.topicDrag===focusId)?.focus();toast('Topic order saved in this browser');
  }
  function bindTopicReordering(){
    const list=$('#faq-topic-list');const ids=()=>[...list.children].map(row=>row.dataset.topicId);
    $$('[data-topic-drag]').forEach(handle=>{
      handle.onkeydown=event=>{if(!['ArrowUp','ArrowDown'].includes(event.key))return;event.preventDefault();const order=ids(),from=order.indexOf(handle.dataset.topicDrag),to=from+(event.key==='ArrowUp'?-1:1);if(to<0||to>=order.length)return;[order[from],order[to]]=[order[to],order[from]];saveTopicOrder(order,handle.dataset.topicDrag);};
      handle.onpointerdown=event=>{
        if(event.button!==0)return;event.preventDefault();handle.focus();const row=handle.closest('.faq-topic-row'),original=ids();handle.setPointerCapture(event.pointerId);row.classList.add('dragging');
        function cleanup(){row.classList.remove('dragging');window.removeEventListener('pointermove',move);window.removeEventListener('pointerup',finish);window.removeEventListener('pointercancel',cancel);if(handle.hasPointerCapture(event.pointerId))handle.releasePointerCapture(event.pointerId);}
        function move(next){if(next.pointerId!==event.pointerId)return;const rows=[...list.children],index=rows.findIndex(item=>{const rect=item.getBoundingClientRect();return next.clientY>=rect.top&&next.clientY<rect.bottom;});if(index>=0&&index!==rows.indexOf(row)){const remaining=rows.filter(item=>item!==row);list.insertBefore(row,remaining[index]||null);[...list.children].forEach((item,position)=>{const number=item.querySelector('.faq-topic-number');number.textContent=String(position+1).padStart(2,'0');number.setAttribute('aria-label',`Order ${position+1}`);});}if(next.clientY>innerHeight-60)window.scrollBy(0,14);else if(next.clientY<100)window.scrollBy(0,-14);}
        function finish(next){if(next.pointerId!==event.pointerId)return;cleanup();saveTopicOrder(ids(),handle.dataset.topicDrag);}
        function cancel(){cleanup();original.forEach((id,index)=>{const item=[...list.children].find(item=>item.dataset.topicId===id);list.append(item);const number=item.querySelector('.faq-topic-number');number.textContent=String(index+1).padStart(2,'0');number.setAttribute('aria-label',`Order ${index+1}`);});}
        window.addEventListener('pointermove',move);window.addEventListener('pointerup',finish);window.addEventListener('pointercancel',cancel);
      };
    });
  }
  function editTopic(id=null){
    editingTopic=id;const topic=faqTopics().find(t=>t.id===id);$('#faq-topic-name').value=topic?.title||'';$('#faq-topic-form-title').textContent=topic?'Edit topic':'Add topic';$('#save-faq-topic').textContent=topic?'Save topic':'Add topic';$('#faq-topic-error').textContent='';openDialog($('#faq-topic-editor'));$('#faq-topic-name').focus();
  }
  $('#faq-topic-editor').addEventListener('cancel',event=>{event.preventDefault();closeDialog($('#faq-topic-editor'));});
  function bindTopicManager(){
    topicList();editingTopic=null;removingTopic=null;bindTopicRemoval();$('#add-faq-topic').onclick=()=>editTopic();
  $('#reset-faq-topic').onclick=$('#close-topic-editor').onclick=()=>closeDialog($('#faq-topic-editor')); 
  $('#faq-topic-form').onsubmit=async event=>{
    event.preventDefault();const title=$('#faq-topic-name').value.trim().replace(/\s+/g,' '),topics=faqTopics();
    if(!title){$('#faq-topic-error').textContent='Enter a topic name.';return;}
    if(topics.some(topic=>topic.id!==editingTopic&&topic.title.toLocaleLowerCase()===title.toLocaleLowerCase())){$('#faq-topic-error').textContent='A topic with this name already exists.';return;}
    const previousTopic=topics.find(topic=>topic.id===editingTopic);
    const base='faq-'+titleSlug(title),used=new Set([...topics,...(store.deletedFAQTopics||[])].map(topic=>topic.id));let id=previousTopic?.id||base,index=2;while(!previousTopic&&used.has(id))id=base+'-'+index++;
    const topic={id,title,url:previousTopic?.url||`/${id}/`};
    const previous={faqTopics:store.faqTopics,activity:store.activity};
    store.faqTopics=[...(store.faqTopics||[]).filter(item=>item.id!==id),topic];store.activity=[{title:`${previousTopic?'Edited':'Added'} FAQ topic: ${title}`,time:new Date().toISOString()},...store.activity].slice(0,100);
    if(!save()){Object.assign(store,previous);return;}
    await closeDialog($('#faq-topic-editor'));render(true);$('#add-faq-topic').focus();toast('FAQ topic saved in this browser');
  };
  }
  function removeTopic(id){
    const topic=faqTopics().find(t=>t.id===id);if(!topic)return;removingTopic=id;const questions=topicQuestions(id);
    $('#faq-topic-remove-message').textContent=questions.length?`“${topic.title}” has ${questions.length} questions. Choose another topic to move them to before removing it.`:`Remove “${topic.title}”? This topic has no questions.`;
    $('#faq-topic-move-label').hidden=!questions.length;$('#faq-topic-move').disabled=!questions.length;$('#faq-topic-move').innerHTML='<option value="">Select destination topic</option>'+faqTopics().filter(t=>t.id!==id).map(t=>`<option value="${escape(t.id)}">${escape(t.title)}</option>`).join('');
    $('#faq-topic-remove-error').textContent=questions.length&&faqTopics().length===1?'Add another topic before removing this topic, or remove its questions first.':'';
    $('#confirm-remove-faq-topic').disabled=questions.length>0&&faqTopics().length===1;openDialog($('#faq-topic-removal'));$('#cancel-remove-faq-topic').focus();
  }
  $('#faq-topic-removal').addEventListener('cancel',event=>{event.preventDefault();closeDialog($('#faq-topic-removal'));});
  $('#faq-topic-removal').addEventListener('close',()=>{removingTopic=null;});
  function bindTopicRemoval(){
  $('#cancel-remove-faq-topic').onclick=()=>closeDialog($('#faq-topic-removal'));
  $('#confirm-remove-faq-topic').onclick=async()=>{
    const topic=faqTopics().find(t=>t.id===removingTopic);if(!topic)return;const questions=topicQuestions(topic.id),destination=faqTopics().find(t=>t.id===$('#faq-topic-move').value&&t.id!==topic.id);
    if(questions.length&&!destination){$('#faq-topic-remove-error').textContent='Select a destination topic for these questions.';return;}
    const previous={drafts:store.drafts,faqTopics:store.faqTopics,deletedFAQTopics:store.deletedFAQTopics,activity:store.activity};
    let order=destination?Math.max(0,...topicQuestions(destination.id).map(r=>Number(r.order)||0)):0;
    const moved=questions.sort((a,b)=>(Number(a.order)||1)-(Number(b.order)||1)).map(r=>({...r,topic:destination.id,url:destination.url,order:++order,status:'Draft'}));
    store.drafts=[...store.drafts.filter(draft=>!moved.some(r=>r.id===draft.id)),...moved];store.faqTopics=(store.faqTopics||[]).filter(t=>t.id!==topic.id);store.deletedFAQTopics=[...(store.deletedFAQTopics||[]),{...topic,deleted_at:new Date().toISOString(),moved_to:destination?.id||null}];store.activity=[{title:`Removed FAQ topic: ${topic.title}${moved.length?`; moved ${moved.length} questions to ${destination.title}`:''}`,time:new Date().toISOString()},...store.activity].slice(0,100);
    if(!save()){Object.assign(store,previous);return;}
    if(faqTopicFilter===topic.id)faqTopicFilter=destination?.id||'';await closeDialog($('#faq-topic-removal'));removingTopic=null;render(true);$('#add-faq-topic').focus();toast('FAQ topic removed from this workspace');
  };
  }

  function faqIntro(){return `<div class="faq-summary"><div><span class="eyebrow">PATIENT QUESTIONS</span><h2>Good questions. Clear answers.</h2><p>${all().filter(r=>r.section==='faqs').length} questions across ${faqTopics().length} treatment topics. Review the answer, choose its topic, and set its display order.</p></div><div class="faq-summary-actions"><a class="text-link" href="/faq/" target="_blank" rel="noopener">View website FAQs ${icon('arrowUpRight')}</a></div></div>`;}
  function collection(){return `${section==='clinic'?clinicIntro():section==='faqs'?faqIntro()+$('#faq-topics-template').innerHTML:section==='treatments'?catalogManager():section==='gallery'?gallerySectionManager():''}<section class="panel collection-panel"><div class="collection-heading"><div><h2>${section==='drafts'?'Your draft library':labels[section]+' library'}</h2><p>Find an item, review its details, and make your next update.</p></div><span class="library-icon">${icon(section)}</span></div><div class="toolbar"><label class="search" style="margin:0">${icon('search')}<input id="content-search" aria-label="Search content" placeholder="Search ${labels[section].toLowerCase()}…" value="${escape(search)}"></label><select id="status-filter" aria-label="Filter by status"><option value="all">All content</option><option value="Draft" ${filter==='Draft'?'selected':''}>Local drafts</option><option value="Website snapshot" ${filter==='Website snapshot'?'selected':''}>Website snapshot</option></select><select id="sort-content" aria-label="Sort content"><option value="default">Default order</option><option value="az">Title: A–Z</option><option value="za">Title: Z–A</option></select>${section==='faqs'?`<select id="faq-topic-filter" aria-label="Filter FAQs by topic"><option value="">All topics</option>${faqTopics().map(t=>`<option value="${escape(t.id)}" ${faqTopicFilter===t.id?'selected':''}>${escape(t.title)}</option>`).join('')}</select>`:''}<span id="result-count" class="result-count"></span></div><div id="results"></div></section>`;}
  function homepageTreatmentIds(){const available=all().filter(r=>r.section==='treatments');return (store.homepageTreatmentOrder??available.filter(r=>r.show_on_homepage).sort((a,b)=>a.homepage_order-b.homepage_order).map(r=>r.id)).filter(id=>available.some(r=>r.id===id));}
  function treatmentTable(items){const selected=homepageTreatmentIds();return `<p class="homepage-treatment-note"><strong>${selected.length} / 6 on homepage</strong><span>Choose up to six treatments. Position sets their display order on the homepage.</span></p><div class="table-wrap"><table class="homepage-treatment-table"><thead><tr><th>Content</th><th>Homepage</th><th>Position</th><th>Status</th><th>Actions</th></tr></thead><tbody>${items.map(r=>{const position=selected.indexOf(r.id);return `<tr><td><div class="table-content">${safeURL(r.image)?`<img class="row-thumbnail" src="${safeURL(r.image)}" alt="" loading="lazy">`:''}<div><button class="title-button" data-edit="${escape(r.id)}">${escape(r.title)}</button><small>${escape(r.short_details||r.description||'')}</small></div></div></td><td><label class="homepage-treatment-toggle"><input type="checkbox" data-homepage-toggle="${escape(r.id)}" aria-label="Show ${escape(r.title)} on homepage" ${position>=0?'checked':''} ${position<0&&selected.length>=6?'disabled':''}><span>Show</span></label></td><td>${position>=0?`<select data-homepage-position="${escape(r.id)}" aria-label="Homepage position for ${escape(r.title)}">${selected.map((id,i)=>`<option value="${i+1}" ${i===position?'selected':''}>${i+1}</option>`).join('')}</select>`:'<span class="muted">—</span>'}</td><td>${badge(r)}</td><td><div class="gallery-row-actions"><button class="edit" data-edit="${escape(r.id)}">Edit</button><button class="delete-content" data-delete-content="${escape(r.id)}">Delete</button><a class="text-link" href="${safeURL(r.url)}" target="_blank" rel="noopener" aria-label="Preview ${escape(r.title)}">${icon('arrowUpRight')}</a></div></td></tr>`;}).join('')}</tbody></table></div>`;}
  function bindHomepageTreatments(){
    const commit=ids=>{const active=document.activeElement,selector=active?.dataset.homepageToggle?`[data-homepage-toggle="${CSS.escape(active.dataset.homepageToggle)}"]`:active?.dataset.homepagePosition?`[data-homepage-position="${CSS.escape(active.dataset.homepagePosition)}"]`:null;const previous=store.homepageTreatmentOrder;store.homepageTreatmentOrder=ids;if(!save())store.homepageTreatmentOrder=previous;results(false);if(selector)$(selector)?.focus({preventScroll:true});};
    $$('[data-homepage-toggle]').forEach(input=>input.onchange=()=>{const ids=homepageTreatmentIds(),id=input.dataset.homepageToggle;if(input.checked&&ids.length>=6){input.checked=false;toast('Only six treatments can appear on the homepage.');return;}commit(input.checked?[...ids,id]:ids.filter(value=>value!==id));});
    $$('[data-homepage-position]').forEach(input=>input.onchange=()=>{const ids=homepageTreatmentIds(),from=ids.indexOf(input.dataset.homepagePosition);const target=Number(input.value)-1,[moved]=ids.splice(from,1);ids.splice(target,0,moved);commit(ids);});
  }
  function tablePagination(total,pages){
    const start=total?(tablePage-1)*tablePageSize+1:0,end=Math.min(tablePage*tablePageSize,total);
    const numbers=[...new Set([1,pages,tablePage-1,tablePage,tablePage+1].filter(n=>n>=1&&n<=pages))].sort((a,b)=>a-b);
    const buttons=numbers.map((n,i)=>`${i&&n>numbers[i-1]+1?'<span class="pagination-gap" aria-hidden="true">…</span>':''}<button type="button" data-table-page="${n}" aria-label="Go to page ${n}" ${n===tablePage?'aria-current="page"':''}>${n}</button>`).join('');
    return `<footer class="table-pagination"><p id="table-page-summary" role="status" aria-live="polite">Showing <strong>${start}–${end}</strong> of <strong>${total}</strong> ${total===1?'item':'items'}</p><label class="table-page-size">Rows per page<select id="table-page-size" aria-label="Rows per page">${[10,25,50,100].map(n=>`<option value="${n}" ${n===tablePageSize?'selected':''}>${n}</option>`).join('')}</select></label><nav aria-label="${escape(labels[section])} pagination"><button type="button" data-table-page="${tablePage-1}" data-page-control="previous" aria-label="Previous page" ${tablePage===1?'disabled':''}>${icon('caretRight')}<span>Previous</span></button>${buttons}<button type="button" data-table-page="${tablePage+1}" data-page-control="next" aria-label="Next page" ${tablePage===pages?'disabled':''}><span>Next</span>${icon('caretRight')}</button></nav></footer>`;
  }
  function bindTablePagination(){
    $$('[data-table-page]').forEach(button=>button.onclick=()=>{const control=button.dataset.pageControl;tablePage=Number(button.dataset.tablePage);results();const target=control?`[data-page-control="${control}"]`:`[data-table-page="${tablePage}"]`;$(`${target}:not(:disabled)`)?.focus({preventScroll:true});});
    $('#table-page-size').onchange=event=>{tablePageSize=Number(event.target.value);tablePage=1;try{localStorage.setItem(key+'-page-size',String(tablePageSize));}catch{}results();$('#table-page-size').focus({preventScroll:true});};
  }
  function results(animateResults=true){let items=all().filter(r=>(section==='drafts'?r.status==='Draft':r.section===section)&&(filter==='all'||r.status===filter)&&(section!=='faqs'||!faqTopicFilter||r.topic===faqTopicFilter)&&searchable(r).includes(search.toLowerCase()));if(['clinic','gallery','doctors','locations'].includes(section)&&sort==='default')items.sort((a,b)=>(Number(a.order)||1)-(Number(b.order)||1));if(section==='faqs'&&sort==='default')items.sort((a,b)=>faqTopics().findIndex(t=>t.id===a.topic)-faqTopics().findIndex(t=>t.id===b.topic)||(Number(a.order)||1)-(Number(b.order)||1));if(sort!=='default')items.sort((a,b)=>a.title.localeCompare(b.title)*(sort==='za'?-1:1));$('#result-count').textContent=`${items.length} ${items.length===1?'item':'items'}`;
    const total=items.length,pages=Math.max(1,Math.ceil(total/tablePageSize));tablePage=Math.max(1,Math.min(tablePage,pages));items=items.slice((tablePage-1)*tablePageSize,tablePage*tablePageSize);
    $('#results').innerHTML=!items.length?`<div class="empty">${icon('search')}<h3>${section==='drafts'&&!search?'No drafts yet':'No matching content'}</h3><p>${section==='drafts'&&!search?'Open any website item to save your first draft.':'Try another search or clear your filters.'}</p><button id="clear-search">${section==='drafts'&&!search?'Browse pages':'Clear filters'}</button></div>`:section==='treatments'?treatmentTable(items):section==='faqs'?faqTable(items):section==='locations'?locationCards(items):['clinic','gallery','doctors'].includes(section)?photoTable(items):`<div class="table-wrap"><table><thead><tr><th>Content</th><th>Status</th><th>Actions</th></tr></thead><tbody>${items.map(r=>`<tr><td><div class="table-content">${['doctors','gallery','treatments','articles'].includes(r.section)&&safeURL(r.image)?`<img class="row-thumbnail" src="${safeURL(r.image)}" alt="" loading="lazy">`:`<span class="row-thumbnail placeholder">${icon(r.section)}</span>`}<div><button class="title-button" data-edit="${escape(r.id)}">${escape(r.title)}</button><small>${escape(r.section==='treatments'?(serviceCatalog().find(service=>service.id===r.service)?.name||'Service not selected')+(r.treatment?' · '+capitalizeText(r.treatment):''):r.url)}</small>${['treatments','articles'].includes(r.section)&&r.short_details?`<small>${escape(r.short_details.slice(0,100))}</small>`:''}</div></div></td><td>${badge(r)}</td><td><button class="edit" data-edit="${escape(r.id)}" aria-label="Edit ${escape(r.title)}">Edit</button>${['treatments','articles'].includes(r.section)?` <button class="delete-content" data-delete-content="${escape(r.id)}" aria-label="Delete ${escape(r.title)}">Delete</button>`:''} <a class="text-link" href="${safeURL(r.url)}" target="_blank" rel="noopener" aria-label="Preview ${escape(r.title)}"><span class="preview-text">Preview</span> ${icon('arrowUpRight')}</a></td></tr>`).join('')}</tbody></table></div>`;
    $('#results').insertAdjacentHTML('beforeend',tablePagination(total,pages));bindTablePagination();
    if(animateResults)reveal($$('#results tbody tr, #results .media-card, #results .doctor-card, #results .empty'),16);
    bindEditors();bindPhotoReordering();bindHomepageTreatments();if($('#clear-search'))$('#clear-search').onclick=()=>{if(section==='drafts'&&!search){location.hash='pages';return;}tablePage=1;search='';filter='all';faqTopicFilter='';if($('#faq-topic-filter'))$('#faq-topic-filter').value='';$('#content-search').value='';$('#status-filter').value='all';results();};
  }
  function faqTable(items){return `<div class="table-wrap"><table class="faq-table"><thead><tr><th>Question &amp; answer</th><th>Topic / order</th><th>Status</th><th>Actions</th></tr></thead><tbody>${items.map(r=>`<tr><td><button class="title-button" data-edit="${escape(r.id)}">${escape(r.title)}</button><p class="faq-answer-preview">${escape(r.description)}</p></td><td><span>${escape(faqTopics().find(t=>t.id===r.topic)?.title||'Unassigned')}</span><small class="faq-order">Position ${Number(r.order)||1}</small></td><td>${badge(r)}</td><td><button class="edit" data-edit="${escape(r.id)}" aria-label="Edit ${escape(r.title)}">Edit</button> <button class="delete-content" data-delete-content="${escape(r.id)}" aria-label="Delete ${escape(r.title)}">Delete</button></td></tr>`).join('')}</tbody></table></div>`;}
  function bindEditors(){$$('[data-edit]').forEach(b=>b.onclick=()=>openEditor(all().find(r=>r.id===b.dataset.edit)));$$('[data-delete-content]').forEach(button=>button.onclick=()=>confirmContentDeletion(button.dataset.deleteContent));}
  let contentToDelete=null;
  function confirmContentDeletion(id){
    const record=all().find(record=>record.id===id&&['treatments','articles','faqs','gallery'].includes(record.section));if(!record)return;
    contentToDelete=id;const kind=record.section==='gallery'?'gallery photo':record.section==='faqs'?'FAQ':record.section==='articles'?'article':'treatment';$('#delete-content-title').textContent=`Delete ${kind}?`;$('#confirm-delete-content').textContent=`Delete ${kind}`;$('#delete-content-message').textContent=`Remove “${record.title}” from your ${record.section}?`;
    openDialog($('#delete-content-dialog'));$('#cancel-delete-content').focus();
  }
  $('#cancel-delete-content').onclick=()=>closeDialog($('#delete-content-dialog'));
  $('#delete-content-dialog').addEventListener('close',()=>{contentToDelete=null;});
  $('#confirm-delete-content').onclick=async()=>{
    const record=all().find(record=>record.id===contentToDelete&&['treatments','articles','faqs','gallery'].includes(record.section));if(!record)return;
    const previous={drafts:store.drafts,deletions:store.deletions,activity:store.activity};
    store.drafts=store.drafts.filter(draft=>draft.id!==record.id);
    store.deletions=[...(store.deletions||[]).filter(item=>item.id!==record.id),{id:record.id,section:record.section,title:record.title,slug:record.slug||record.url.replace(/^\/+|\/+$/g,''),url:record.url,deleted_at:new Date().toISOString()}];
    store.activity=[{title:`Deleted ${record.section==='gallery'?'gallery photo':record.section==='faqs'?'FAQ':record.section==='articles'?'article':'treatment'}: ${record.title}`,time:new Date().toISOString()},...store.activity].slice(0,100);
    if(!save()){Object.assign(store,previous);return;}
    await closeDialog($('#delete-content-dialog'));render(true);$('#add').focus();toast(`${record.section==='gallery'?'Gallery photo':record.section==='faqs'?'FAQ':record.section==='articles'?'Article':'Treatment'} removed from this workspace`);
  };
  function settings(){return `<section class="panel"><div class="panel-header"><div><h2>Workspace details</h2><p>These preferences apply to your local dashboard.</p></div></div><form id="settings-form" class="settings-form"><label>Workspace name<input name="name" required maxlength="100" value="${escape(store.settings.name)}"></label><label>Contact email<input name="email" required type="email" value="${escape(store.settings.email)}"></label><button class="primary">Save preferences</button></form></section>`;}
  function render(preserve=false){updatePublishIndicator();section=location.hash.slice(1)||'overview';if(!labels[section])section='overview';if(!preserve){tablePage=1;search='';filter='all';sort='default';faqTopicFilter='';}$('#page-title').textContent=labels[section];$('#breadcrumb').textContent=labels[section];$('#page-description').textContent=descriptions[section]||'Your content, your team, and every first impression — all in one place.';document.title=`${labels[section]} · Dr. Teeth Website Console`;$$('[data-nav]').forEach(a=>{a.classList.toggle('active',a.dataset.nav===section);if(a.dataset.nav===section)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});$('[data-count="pages"]').textContent=count('pages');$('[data-count="drafts"]').textContent=store.drafts.length;setNavigation(false);$('#view').innerHTML=section==='overview'?overview():section==='activity'?`<section class="panel"><div class="panel-header"><h2>Draft activity</h2><span class="badge snapshot">${store.activity.length} changes</span></div>${activity()}</section>`:section==='settings'?settings():collection();
    $('#add').innerHTML=icon('plus')+' '+(({faqs:'Add FAQ',pages:'Add page',treatments:'Add treatment',doctors:'Add doctor',gallery:'Add photo',clinic:'Add clinic photo',locations:'Add location',articles:'Add article'})[section]||'Add content');bindEditors();if(section==='gallery')bindGallerySectionManager();if(section==='treatments')bindCatalogManager();if(section==='faqs'){bindTopicManager();$('#add-faq-topic').innerHTML=icon('plus')+' Add topic';}if($('#content-search')){$('#sort-content').value=sort;$('#content-search').oninput=e=>{tablePage=1;search=e.target.value;results(false);};$('#status-filter').onchange=e=>{tablePage=1;filter=e.target.value;results();};$('#sort-content').onchange=e=>{tablePage=1;sort=e.target.value;results();};results();if($('#faq-topic-filter'))$('#faq-topic-filter').onchange=e=>{tablePage=1;faqTopicFilter=e.target.value;results();};}
    motion($('#view'),[{opacity:0,transform:'translateY(6px)'},{opacity:1,transform:'none'}],{duration:260});
    motion($('.page-heading'),[{opacity:.45,transform:'translateY(3px)'},{opacity:1,transform:'none'}],{duration:220});
    if(section==='overview')reveal($$('.stats .stat, .quick-edits > button'),30);
    if($('#settings-form'))$('#settings-form').onsubmit=e=>{e.preventDefault();const data=new FormData(e.target);store.settings={name:data.get('name').trim(),email:data.get('email').trim()};if(save()){updateWorkspace();toast('Workspace preferences saved');}};
  }
  function updateWorkspace(){$('.workspace strong').textContent=store.settings.name;}
  function orderedCatalog(items,order,key=item=>item){const rank=new Map(items.map((item,index)=>[key(item),index]));return [...items].sort((a,b)=>{const position=id=>order.includes(id)?order.indexOf(id):order.length+rank.get(id);return position(key(a))-position(key(b));});}
  const serviceCatalog=()=>orderedCatalog([...(window.DashboardServices||[]),...(store.services||[])].filter(service=>!(store.deletedServices||[]).includes(service.id)).map(source=>{const service=store.serviceEdits?.[source.id]||source;return {...service,name:capitalizeText(service.name),treatments:orderedCatalog([...new Set([...service.treatments,...(store.treatmentOptions?.[service.id]||[])])],store.optionOrder?.[service.id]||[])};}),store.serviceOrder||[],item=>item.id);
  let selectedCatalogService=null,catalogEditing=null,catalogRemoving=null;
  const assignedService=record=>record.service||serviceCatalog().find(service=>record.url===`/${service.id}/`)?.id;
  const serviceRecords=id=>all().filter(record=>record.section==='treatments'&&assignedService(record)===id);
  function catalogManager(){return `<section class="panel catalog-manager" aria-labelledby="catalog-manager-title"><div class="faq-topics-header"><div><span class="eyebrow">TREATMENT LIBRARY</span><h2 id="catalog-manager-title">Manage services</h2><p class="field-help">Add, edit, and manage your service categories.</p></div><button type="button" id="catalog-add-service" class="primary">${icon('plus')} Add service</button></div><div class="catalog-manager-grid"><div><h3>Services</h3><div id="catalog-services"></div></div></div></section>`;}
  function catalogRow(id,name,index,kind,extra=''){return `<div class="faq-topic-row catalog-row" data-catalog-id="${escape(id)}"><div class="faq-topic-info"><div>${kind==='service'?`<strong>${escape(name)}</strong>`:`<strong>${escape(capitalizeText(name))}</strong>`}${extra}</div></div><div><button type="button" data-catalog-edit="${escape(id)}" data-kind="${kind}" aria-label="Edit ${kind} ${escape(name)}">Edit</button><button type="button" class="delete-content" data-catalog-remove="${escape(id)}" data-kind="${kind}" aria-label="Remove ${kind} ${escape(name)}">Remove</button></div></div>`;}
  function bindCatalogManager(){
    const services=serviceCatalog();if(!services.some(service=>service.id===selectedCatalogService))selectedCatalogService=services[0]?.id||null;
    $('#catalog-services').innerHTML=services.map((service,index)=>catalogRow(service.id,service.name,index,'service',`<small>${service.treatments.length} treatments</small>`)).join('')||'<p class="field-help">Add your first service to get started.</p>';
    $('#catalog-add-service').onclick=()=>openCatalogEditor('service');
    $$('[data-catalog-edit]').forEach(button=>button.onclick=()=>openCatalogEditor(button.dataset.kind,button.dataset.catalogEdit));
    $$('[data-catalog-remove]').forEach(button=>button.onclick=()=>openCatalogRemoval(button.dataset.kind,button.dataset.catalogRemove));
  }
  function writeService(service){store.serviceEdits={...(store.serviceEdits||{}),[service.id]:service};store.treatmentOptions={...(store.treatmentOptions||{}),[service.id]:[]};}
  function openCatalogEditor(kind,id=null){catalogEditing={kind,id,service:selectedCatalogService};const service=serviceCatalog().find(item=>item.id===(kind==='service'?id:selectedCatalogService));$('#catalog-name').value=kind==='service'?service?.name||'':id||'';$('#catalog-editor-title').textContent=`${id?'Edit':'Add'} ${kind==='service'?'service':'treatment'}`;$('#catalog-editor-error').textContent='';openDialog($('#catalog-editor'));$('#catalog-name').focus();}
  $('#catalog-editor-cancel').onclick=$('#catalog-editor-close').onclick=()=>closeDialog($('#catalog-editor'));
  $('#catalog-editor').addEventListener('cancel',event=>{event.preventDefault();closeDialog($('#catalog-editor'));});
  $('#catalog-editor-form').onsubmit=async event=>{
    event.preventDefault();const name=capitalizeText($('#catalog-name').value.trim().replace(/\s+/g,' ')),{kind,id,service:serviceId}=catalogEditing;const services=serviceCatalog(),service=services.find(item=>item.id===(kind==='service'?id:serviceId));
    if(!name)return;if((kind==='service'?services.filter(item=>item.id!==id).map(item=>item.name):(service?.treatments||[]).filter(value=>value!==id)).some(value=>value.toLowerCase()===name.toLowerCase())){$('#catalog-editor-error').textContent='This name already exists.';return;}
    const previous={...store};
    if(kind==='service'){if(id)writeService({...service,name});else{const next={id:'service-'+crypto.randomUUID(),name,treatments:[]};store.services=[...(store.services||[]),next];selectedCatalogService=next.id;}}
    else{writeService({...service,treatments:id?service.treatments.map(value=>value===id?name:value):[...service.treatments,name]});if(id){store.optionOrder={...(store.optionOrder||{}),[serviceId]:(store.optionOrder?.[serviceId]||[]).map(value=>value===id?name:value)};const updates=serviceRecords(serviceId).filter(record=>record.treatment===id).map(record=>({...record,service:serviceId,treatment:name,status:'Draft'}));store.drafts=[...store.drafts.filter(record=>!updates.some(update=>update.id===record.id)),...updates];}}
    store.activity=[{title:`${id?'Edited':'Added'} ${kind==='service'?'service':'treatment option'}: ${name}`,time:new Date().toISOString()},...store.activity].slice(0,100);if(!save()){Object.assign(store,previous);return;}await closeDialog($('#catalog-editor'));render(true);toast('Saved in this browser');
  };
  function openCatalogRemoval(kind,id){const service=serviceCatalog().find(item=>item.id===(kind==='service'?id:selectedCatalogService));if(!service)return;catalogRemoving={kind,id,service:service.id};const assigned=serviceRecords(service.id).filter(record=>kind==='service'||record.treatment===id);$('#catalog-remove-title').textContent=`Remove ${kind==='service'?'service':'treatment'}?`;$('#catalog-remove-message').textContent=kind==='service'?`Remove “${service.name}” and its ${service.treatments.length} treatment options? ${assigned.length} content items use this service.${assigned.length?' Move them to another service; their optional treatment selection will be cleared.':''}`:`Remove “${capitalizeText(id)}”? ${assigned.length} content items use this treatment; their optional treatment selection will be cleared. Their content will be kept.`;$('#catalog-move-label').hidden=kind!=='service'||!assigned.length;$('#catalog-move').disabled=kind!=='service'||!assigned.length;$('#catalog-move').innerHTML='<option value="">Select destination service</option>'+serviceCatalog().filter(item=>item.id!==service.id).map(item=>`<option value="${escape(item.id)}">${escape(item.name)}</option>`).join('');$('#catalog-remove-error').textContent='';openDialog($('#catalog-remove-dialog'));$('#catalog-remove-cancel').focus();}
  $('#catalog-remove-cancel').onclick=()=>closeDialog($('#catalog-remove-dialog'));
  $('#catalog-remove-dialog').addEventListener('cancel',event=>{event.preventDefault();closeDialog($('#catalog-remove-dialog'));});
  $('#catalog-remove-confirm').onclick=async()=>{const {kind,id,service:serviceId}=catalogRemoving,service=serviceCatalog().find(item=>item.id===serviceId),assigned=serviceRecords(serviceId).filter(record=>kind==='service'||record.treatment===id),target=serviceCatalog().find(item=>item.id===$('#catalog-move').value&&item.id!==serviceId);if(kind==='service'&&assigned.length&&!target){$('#catalog-remove-error').textContent='Select another service before removing this one.';return;}const previous={...store};if(kind==='service')store.deletedServices=[...(store.deletedServices||[]),id];else writeService({...service,treatments:service.treatments.filter(value=>value!==id)});const updates=assigned.map(record=>({...record,service:kind==='service'?target.id:serviceId,treatment:'',status:'Draft'}));store.drafts=[...store.drafts.filter(record=>!updates.some(update=>update.id===record.id)),...updates];store.activity=[{title:`Removed ${kind==='service'?'service':'treatment option'}: ${kind==='service'?service.name:id}`,time:new Date().toISOString()},...store.activity].slice(0,100);if(!save()){Object.assign(store,previous);return;}await closeDialog($('#catalog-remove-dialog'));render(true);toast('Removed from this workspace');};

  function fillServices(selected=''){
    $('#treatment-service').innerHTML='<option value="">Select a service</option>'+serviceCatalog().map(service=>`<option value="${escape(service.id)}">${escape(service.name)}</option>`).join('');
    $('#treatment-service').value=selected;
  }
  $('#treatment-service').onchange=()=>{$('#catalog-status').textContent='';};
  $('#add-service').onclick=()=>{$('#new-service').hidden=false;$('#new-service-name').focus();};
  $$('[data-cancel-catalog]').forEach(button=>button.onclick=()=>{$('#'+button.dataset.cancelCatalog).hidden=true;});
  $('#create-service').onclick=()=>{
    const name=capitalizeText($('#new-service-name').value.trim());if(!name){$('#catalog-status').textContent='Enter a service name.';return;}
    const existing=serviceCatalog().find(service=>service.name.toLowerCase()===name.toLowerCase());
    const id=existing?.id||'service-'+crypto.randomUUID();
    if(!existing){store.services=store.services||[];store.services.push({id,name,treatments:[]});if(!save()){store.services.pop();return;}}
    fillServices(id);$('#new-service').hidden=true;$('#new-service-name').value='';$('#catalog-status').textContent=existing?'Existing service selected.':'Service added to this workspace.';
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
    return title.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/['’]/g,'').replace(/&/g,' and ').replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'').slice(0,100).replace(/-+$/g,'')||fallback;
  }
  function uniqueContentSlug(title){
    const base=titleSlug(title,({articles:'article',pages:'page'})[$('#editor-form').elements.section.value]||'treatment'),used=new Set(['dashboard','static','media']);
    for(const topic of faqTopics())used.add(topic.url.replace(/^\/+|\/+$/g,'').toLowerCase());
    let latest=[];try{latest=JSON.parse(localStorage.getItem(key))?.drafts||[];}catch{}
    for(const record of [...records,...store.drafts,...latest,...(store.deletions||[])]){
      if(record.id===editing)continue;
      if(record.slug)used.add(record.slug.toLowerCase());
      for(const alias of record.url_aliases||[])used.add(alias.replace(/^\/+|\/+$/g,'').toLowerCase());
      if(record.url)used.add(record.url.split(/[?#]/)[0].replace(/^\/+|\/+$/g,'').toLowerCase());
    }
    let slug=base,suffix=2;while(used.has(slug))slug=`${base}-${suffix++}`;return slug;
  }
  function contentSlug(){
    const previous=all().find(record=>record.id===editing);
    if($('#editor-form').elements.section.value==='treatments')return uniqueContentSlug($('#editor-form').elements.title.value);
    return previous?.slug||(previous?.url&&!['/services/','/blog/'].includes(previous.url)?previous.url.replace(/^\/+|\/+$/g,''):uniqueContentSlug($('#editor-form').elements.title.value));
  }
  function updateSlugPreview(){
    const preview=$('#treatment-slug-preview'),form=$('#editor-form');preview.hidden=!['treatments','articles','pages'].includes(form.elements.section.value);
    if(form.elements.section.value==='pages'){const previous=all().find(record=>record.id===editing);preview.textContent=form.elements.title.value.trim()?`URL: ${previous?.url||`/${uniqueContentSlug(form.elements.title.value)}/`}`:'The URL is generated automatically from the page title.';return;}
    preview.textContent=form.elements.title.value.trim()?`URL: /${contentSlug()}/`:'The slug is generated automatically from the title.';
  }
  $('#editor-form').elements.title.addEventListener('input',updateSlugPreview);
  const gallerySectionName=value=>['our space','our spaces'].includes(String(value).trim().toLowerCase())?'Our space':String(value).trim();
  const gallerySections=()=>{const sections=new Map(),deleted=(store.deletedGalleryCategories||[]).map(gallerySectionName);for(const value of [...(window.DashboardGallerySections??['Our space','Our team','Our technology']),...(store.galleryCategories||[]),...all().filter(record=>record.section==='gallery').map(record=>record.gallery_category).filter(Boolean)]){const name=gallerySectionName(value);if(name&&!deleted.includes(name)&&name.toLowerCase()!=='all photos'&&!sections.has(name.toLowerCase()))sections.set(name.toLowerCase(),name);}return [...sections.values()];};

  function fillGallerySections(selected=''){selected=gallerySectionName(selected);const select=$('#gallery-section');select.innerHTML='<option value="">Select a section</option>'+gallerySections().map(name=>`<option value="${escape(name)}">${escape(name)}</option>`).join('');select.value=selected;}
  function gallerySectionManager(){return `<section class="panel faq-topics-section" aria-labelledby="gallery-sections-heading"><div class="faq-topics-header"><div><span class="eyebrow">GALLERY LIBRARY</span><h2 id="gallery-sections-heading">Gallery sections</h2><p class="field-help">Organize your photos into sections. Select a section when adding or editing an image.</p></div><button type="button" id="add-gallery-section" class="primary">${icon('plus')} Add section</button></div><div class="gallery-section-list">${gallerySections().map(name=>{const count=all().filter(record=>record.section==='gallery'&&gallerySectionName(record.gallery_category||'')===name).length;return `<div class="gallery-section-item"><strong>${escape(name)}</strong><small>${count} ${count===1?'photo':'photos'}</small><div class="gallery-section-actions"><button type="button" data-edit-gallery-section="${escape(name)}" aria-label="Edit section ${escape(name)}">Edit</button><button type="button" class="delete-content" data-delete-gallery-section="${escape(name)}" aria-label="Delete section ${escape(name)}">Delete</button></div></div>`;}).join('')}</div></section>`;}
  let editingGallerySection=null,deletingGallerySection=null;
  const gallerySectionPhotos=name=>all().filter(record=>record.section==='gallery'&&gallerySectionName(record.gallery_category||'')===name);
  function openGallerySectionEditor(name=null){editingGallerySection=name;$('#new-gallery-section-name').value=name||'';$('#gallery-section-error').textContent='';$('#gallery-section-title').textContent=name?'Edit section':'Add section';$('#gallery-section-form button[type="submit"]').textContent=name?'Save section':'Add section';openDialog($('#gallery-section-dialog'));$('#new-gallery-section-name').focus();}
  function bindGallerySectionManager(){
    $('#add-gallery-section').onclick=()=>openGallerySectionEditor();
    $$('[data-edit-gallery-section]').forEach(button=>button.onclick=()=>openGallerySectionEditor(button.dataset.editGallerySection));
    $$('[data-delete-gallery-section]').forEach(button=>button.onclick=()=>{const name=button.dataset.deleteGallerySection;deletingGallerySection=name;const photos=gallerySectionPhotos(name),destinations=gallerySections().filter(section=>section!==name);$('#delete-gallery-section-message').textContent=photos.length?`“${name}” contains ${photos.length} photos. Move them to another section before deleting it. The images will be kept.`:`Delete “${name}”? This section has no photos.`;$('#gallery-section-move-label').hidden=!photos.length;$('#gallery-section-move').disabled=!photos.length;$('#gallery-section-move').innerHTML='<option value="">Select destination section</option>'+destinations.map(section=>`<option value="${escape(section)}">${escape(section)}</option>`).join('');$('#delete-gallery-section-error').textContent=photos.length&&!destinations.length?'Add another section before deleting this one.':'';$('#confirm-delete-gallery-section').disabled=photos.length>0&&!destinations.length;openDialog($('#delete-gallery-section-dialog'));$('#cancel-delete-gallery-section').focus();});
  }
  $('#cancel-gallery-section').onclick=$('#close-gallery-section').onclick=()=>closeDialog($('#gallery-section-dialog'));
  $('#gallery-section-dialog').addEventListener('cancel',event=>{event.preventDefault();closeDialog($('#gallery-section-dialog'));});
  function moveGallerySectionPhotos(name,destination){const updates=gallerySectionPhotos(name).map(record=>({...record,gallery_category:destination,status:'Draft'}));store.drafts=[...store.drafts.filter(record=>!updates.some(update=>update.id===record.id)),...updates];}
  $('#gallery-section-form').onsubmit=async event=>{
    event.preventDefault();const name=gallerySectionName($('#new-gallery-section-name').value.trim().replace(/\s+/g,' '));if(!name||name.toLowerCase()==='all photos'){$('#gallery-section-error').textContent='Enter a section name other than All photos.';return;}if(gallerySections().some(section=>section!==editingGallerySection&&section.toLowerCase()===name.toLowerCase())){$('#gallery-section-error').textContent='This section already exists.';return;}
    const previous={...store};store.galleryCategories=[...new Set([...(store.galleryCategories||[]).filter(section=>section!==editingGallerySection),name])];store.deletedGalleryCategories=(store.deletedGalleryCategories||[]).filter(section=>section!==name);if(editingGallerySection&&editingGallerySection!==name){store.deletedGalleryCategories=[...store.deletedGalleryCategories,editingGallerySection];moveGallerySectionPhotos(editingGallerySection,name);}store.activity=[{title:`${editingGallerySection?'Updated':'Added'} gallery section: ${name}`,time:new Date().toISOString()},...store.activity].slice(0,100);if(!save()){Object.assign(store,previous);return;}await closeDialog($('#gallery-section-dialog'));render(true);$('#add-gallery-section').focus();toast('Gallery section saved');
  };
  $('#cancel-delete-gallery-section').onclick=()=>closeDialog($('#delete-gallery-section-dialog'));
  $('#delete-gallery-section-dialog').addEventListener('cancel',event=>{event.preventDefault();closeDialog($('#delete-gallery-section-dialog'));});
  $('#confirm-delete-gallery-section').onclick=async()=>{const name=deletingGallerySection;if(!gallerySections().includes(name))return;const photos=gallerySectionPhotos(name),destination=$('#gallery-section-move').value;if(photos.length&&(!gallerySections().includes(destination)||destination===name)){$('#delete-gallery-section-error').textContent='Select a destination section for these photos.';return;}const previous={...store};if(photos.length)moveGallerySectionPhotos(name,destination);store.galleryCategories=(store.galleryCategories||[]).filter(section=>section!==name);store.deletedGalleryCategories=[...new Set([...(store.deletedGalleryCategories||[]),name])];store.activity=[{title:`Deleted gallery section: ${name}`,time:new Date().toISOString()},...store.activity].slice(0,100);if(!save()){Object.assign(store,previous);return;}await closeDialog($('#delete-gallery-section-dialog'));render(true);$('#add-gallery-section').focus();toast('Gallery section deleted');};

  function updateEditorFields(){
    const form=$('#editor-form'),isDoctor=form.elements.section.value==='doctors',isClinic=['clinic','gallery'].includes(form.elements.section.value),isTreatment=form.elements.section.value==='treatments',isLocation=form.elements.section.value==='locations',isArticle=form.elements.section.value==='articles',isPage=form.elements.section.value==='pages',isFAQ=form.elements.section.value==='faqs';
    $('#faq-fields').hidden=!isFAQ;$('#faq-fields').disabled=!isFAQ;
    $('#editor-description-label').textContent=isFAQ?'Answer (required)':'Description';
    form.elements.description.rows=isFAQ?9:5;form.elements.title.maxLength=isFAQ?500:200;
    $('#gallery-section-fields').hidden=form.elements.section.value!=='gallery';$('#gallery-section-fields').disabled=form.elements.section.value!=='gallery';
    $('#editor-form').dataset.section=form.elements.section.value;
    $('#location-fields').hidden=!isLocation;$('#location-fields').disabled=!isLocation;$('.image-upload').hidden=isLocation||isPage||isFAQ;
    form.elements.image_alt.closest('label').hidden=isPage;form.elements.image_alt.disabled=isPage;
    $('#seo-fields').hidden=!(isArticle||isTreatment||isPage);$('#seo-fields').disabled=!(isArticle||isTreatment||isPage);
    $('#seo-description-help').textContent=isPage?'Leave blank to use the page description.':'Leave blank to use short details.';
    $('#seo-image-label').textContent=isPage?'Image alt text':'Thumbnail alt text';
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
    $('#editor-name-label').textContent=isDoctor?'Doctor name':isLocation?'Branch name':isFAQ?'Question (required)':'Title';
    for(const name of ['description','url']){
      const field=form.elements.namedItem(name);
      field.closest('label').hidden=isDoctor||isLocation||((isTreatment||isArticle)&&name==='description')||((isClinic||isTreatment||isArticle||isPage||isFAQ)&&name==='url');
      field.disabled=isDoctor||isLocation||((isTreatment||isArticle)&&name==='description')||((isClinic||isTreatment||isArticle||isPage||isFAQ)&&name==='url');
    }
    updateSlugPreview();
    $('#editor-title').textContent=isFAQ?(editing?'Edit FAQ':'Add FAQ'):isArticle?(editing?'Edit article':'Add article'):isLocation?(editing?'Edit location':'Add location'):isDoctor?(editing?'Edit doctor':'Add doctor'):(isClinic?(editing?'Edit photo':'Add photo'):(editing?'Edit content':'Add content'));
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
    if(form.elements.section.value==='gallery'){fillGallerySections(record?.gallery_category|| (record?.image?.includes('/doctors/')?'Our team':record?'Our space':''));}
    if(form.elements.section.value==='faqs'){form.elements.topic.innerHTML='<option value="">Select a topic</option>'+faqTopics().map(t=>`<option value="${escape(t.id)}">${escape(t.title)}</option>`).join('');form.elements.topic.value=record?.topic||faqTopicFilter||'';form.elements.faq_order.value=record?.order||Math.max(0,...all().filter(r=>r.section==='faqs'&&r.topic===form.elements.topic.value).map(r=>Number(r.order)||0))+1;}
    if(['treatments','articles'].includes(form.elements.section.value)){
      form.elements.short_details.value=record?.short_details??record?.description??'';
      $('#treatment-details').innerHTML=cleanDetails(record?.details||`<p>${escape(record?.description||'')}</p>`);
      if(form.elements.section.value==='treatments'){const service=record?.service||serviceCatalog().find(item=>record?.url===`/${item.id}/`)?.id||'';
      fillServices(service);}syncDetails();
    }
    if(['articles','treatments','pages'].includes(form.elements.section.value)){for(const name of ['seo_title','meta_description','keywords','canonical_url','og_title','og_description','image_alt'])form.elements[name].value=record?.[name]||'';form.elements.robots.value=record?.robots||'index,follow';}
    if(form.elements.section.value==='locations'){for(const name of ['area','address','phone','hours','map_pin'])form.elements[name].value=record?.[name]||'';form.elements.location_order.value=record?.order||Math.max(0,...all().filter(item=>item.section==='locations').map(item=>Number(item.order)||0))+1;}
    $('#location-map-preview').hidden=true;$('#location-map-preview').innerHTML='';
    $('#rich-link-panel').hidden=true;richLinkRange=null;$('#new-service').hidden=true;$('#catalog-status').textContent='';
    showImagePreview();$('#upload-status').textContent=form.elements.image.value?'Current image · Choose a file to replace it.':'No image selected.';$('#discard-notice').hidden=true;
    editorInitial=JSON.stringify(Object.fromEntries(new FormData(form)));
    openDialog($('#editor'));$('.editor-body').scrollTop=0;
  }
  $('#faq-topic').onchange=()=>{if(!editing)$('#editor-form').elements.faq_order.value=Math.max(0,...all().filter(r=>r.section==='faqs'&&r.topic===$('#faq-topic').value).map(r=>Number(r.order)||0))+1;};
  $('#add').onclick=()=>openEditor();function closeEditor(){syncDetails();if(JSON.stringify(Object.fromEntries(new FormData($('#editor-form'))))!==editorInitial){$('#discard-notice').hidden=false;motion($('#discard-notice'),[{opacity:0,transform:'translateY(-4px)'},{opacity:1,transform:'none'}]);$('#keep-editing').focus();}else closeDialog($('#editor'));}
  $('#close-editor').onclick=$('#cancel-editor').onclick=closeEditor;$('#editor').addEventListener('cancel',e=>{e.preventDefault();closeEditor();});$('#keep-editing').onclick=()=>{$('#discard-notice').hidden=true;$('#editor-form input[name="title"]').focus();};$('#discard-editing').onclick=()=>closeDialog($('#editor'));
  $('#editor-form').onsubmit=e=>{e.preventDefault();if(uploading){toast('Wait for the image upload to finish.');return;}syncDetails();const data=Object.fromEntries(new FormData(e.target));Object.keys(data).forEach(k=>data[k]=data[k].trim());if(data.section==='faqs'){const topic=faqTopics().find(t=>t.id===data.topic);data.order=Number(data.faq_order);delete data.faq_order;if(!topic||!Number.isInteger(data.order)||data.order<1){toast('Select a topic and a display order of 1 or more.');return;}data.url=topic.url;data.image='';}
    if(data.section==='pages'){const previous=all().find(record=>record.id===editing);data.url=previous?.url||`/${uniqueContentSlug(data.title)}/`;data.slug=previous?.slug??data.url.replace(/^\/+|\/+$/g,'');if(previous?.image_alt)data.image_alt=previous.image_alt;}if(['articles','treatments','pages'].includes(data.section)){
      if(data.canonical_url&&!/^https?:\/\//i.test(data.canonical_url)){toast('Canonical URLs must begin with https:// or http://.');return;}
      if(!['index,follow','noindex,follow','noindex,nofollow'].includes(data.robots)){toast('Select a valid search engine visibility option.');return;}
      const keywords=new Map(data.keywords.split(',').map(word=>word.trim()).filter(Boolean).map(word=>[word.toLowerCase(),word]));data.keywords=[...keywords.values()].join(', ');
    }if(data.section==='gallery'&&!gallerySections().includes(data.gallery_category)){toast('Select a gallery section.');return;}if(['clinic','gallery'].includes(data.section)){data.url=data.section==='gallery'?'/gallery/':'/about-us/';data.order=Number(data.order);if(!data.alt||!data.image||!Number.isInteger(data.order)||data.order<1){toast('Enter an image, alt text, and a display order of 1 or more.');return;}}if(data.section==='locations'){data.url='/contact/';data.description=data.address;data.order=Number(data.location_order);delete data.location_order;if(!data.area||!data.address||!/^\+?[0-9 ()-]{6,40}$/.test(data.phone)||!Number.isInteger(data.order)||data.order<1){toast('Enter an area, address, valid phone number, and display order.');return;}}if(data.section==='articles'){
      data.slug=contentSlug();const previous=all().find(record=>record.id===editing);data.url=previous?.url&&!['/blog/','/services/'].includes(previous.url)?previous.url:`/${data.slug}/`;
      data.details=cleanDetails(data.details);const text=document.createElement('div');text.innerHTML=data.details;data.description=text.textContent.trim();
      if(!data.short_details||!data.description){toast('Enter short details and article details.');return;}
    }if(data.section==='treatments'){data.title=capitalizeText(data.title);data.slug=contentSlug();data.url=`/${data.slug}/`;data.details=cleanDetails(data.details);const text=document.createElement('div');text.innerHTML=data.details;data.description=text.textContent.trim();if(!serviceCatalog().some(service=>service.id===data.service)||!data.short_details||!data.description){toast('Select a service and enter short details and details.');return;}if(data.treatment&&!serviceCatalog().find(service=>service.id===data.service).treatments.includes(data.treatment)){toast('Choose a treatment belonging to the selected service.');return;}}if(data.section==='doctors'){const previous=all().find(r=>r.id===editing);Object.assign(data,{description:previous?.description||'',url:previous?.url||'/our-doctors/',image:data.image||previous?.image||'',appointment_url:previous?.appointment_url||'/appointment/',order:Number(previous?.order)||Math.max(0,...all().filter(r=>r.section==='doctors').map(r=>Number(r.order)||0))+1});}if(!data.title||(!data.description&&data.section!=='doctors')||!/^\/(?!\/)/.test(data.url)){toast('Enter a title, required details, and website path beginning with /.');return;}if(data.section==='doctors'&&(!data.specialty||!data.qualifications)){toast('Enter a specialty and qualifications.');return;}if(data.image&&!/^(\/(?!\/)|https?:\/\/)/.test(data.image)){toast('Use a local image path or an HTTPS image URL.');return;}const entry={...data,id:editing||`draft-${crypto.randomUUID()}`,status:'Draft'};store.drafts=store.drafts.filter(r=>r.id!==entry.id);store.drafts.push(entry);store.activity.unshift({title:`Saved draft: ${entry.title}`,time:new Date().toISOString()});store.activity=store.activity.slice(0,100);if(save()){closeDialog($('#editor'));render(true);toast(serverURL?'Draft saved · Ready to publish':'Draft saved in this browser');}};
  const serverURL=document.body.dataset.serverUrl;
  let serverRevision=0,syncTimer=null,syncChain=Promise.resolve(),serverConflict=false;
  function syncStatus(message,error=false){const node=$('#server-save-status');if(node){node.textContent=message;node.classList.toggle('save-error',error);}}
  const csrfToken=()=>document.cookie.split('; ').find(value=>value.startsWith('csrftoken='))?.split('=').slice(1).join('=')||'';
  async function serverRequest(url,method,state){const response=await fetch(url,{method,credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':decodeURIComponent(csrfToken())},body:JSON.stringify({state,revision:serverRevision})});const data=await response.json();if(!response.ok){if(response.status===409)serverConflict=true;throw Error(data.error||'Could not save to the server.');}serverRevision=data.revision;return data;}
  function scheduleServerSave(){if(!serverURL)return;clearTimeout(syncTimer);syncStatus('Saving draft…');syncTimer=setTimeout(()=>{syncChain=syncChain.then(async()=>{if(serverConflict)throw Error('Reload to resolve a workspace conflict.');await serverRequest(serverURL,'PUT',store);syncStatus('Draft saved to server');}).catch(error=>{syncStatus(error.message,true);toast(error.message);});},350);}
  function useServerWorkspace(data){publishedSettings=data.published_settings||{};serverRevision=data.revision;records=data.records;window.DashboardLocations=[];window.DashboardFAQs=[];window.DashboardFAQTopics=data.topics;window.DashboardServices=data.services;window.DashboardGallerySections=data.gallery_sections||[];store={drafts:[],deletions:[],activity:[],settings:{name:'Dr. Teeth Family Dental',email:'info@drteethfamilydental.com'},...data.state};localStorage.setItem(key,JSON.stringify(store));updateWorkspace();render();syncStatus(data.published?'Connected · Website published':'Connected · Drafts save to server');}
  $('#publish-changes').onclick=async()=>{if(!serverURL)return;const button=$('#publish-changes');button.disabled=true;clearTimeout(syncTimer);try{await syncChain;if(serverConflict)throw Error('Reload to resolve a workspace conflict before publishing.');syncStatus('Publishing…');const data=await serverRequest(document.body.dataset.publishUrl,'POST',store);useServerWorkspace(data);toast('Changes published to your website');}catch(error){syncStatus(error.message,true);toast(error.message);}finally{button.disabled=false;}};

  $('#menu').onclick=()=>setNavigation(!$('#sidebar').classList.contains('open'));$('#nav-backdrop').onclick=()=>setNavigation(false);
  $('#account').onclick=()=>openDialog($('#account-dialog'));$('#close-account').onclick=()=>closeDialog($('#account-dialog'));
  function globalResults(){const query=$('#global-query').value.toLowerCase().trim();const items=all().filter(r=>!query||`${searchable(r)} ${labels[r.section]}`.toLowerCase().includes(query)).slice(0,8);queryIndex=0;$('#global-results').innerHTML=items.length?items.map((r,i)=>`<button class="command-result ${i===0?'selected':''}" data-record="${escape(r.id)}"><span class="content-icon">${icon(r.section)}</span><span><strong>${escape(r.title)}</strong><small>${labels[r.section]} · ${r.status}</small></span><span>${icon('enter')}</span></button>`).join(''):'<div class="empty"><h3>No results found</h3><p>Try a different title or content type.</p></div>';$$('.command-result').forEach(b=>b.onclick=async()=>{await closeDialog($('#search-dialog'));openEditor(all().find(r=>r.id===b.dataset.record));});}
  function openSearch(){$('#global-query').value='';globalResults();openDialog($('#search-dialog'));$('#global-query').focus();}
  ['search-dialog','account-dialog'].forEach(id=>$('#'+id).addEventListener('cancel',e=>{e.preventDefault();closeDialog($('#'+id));}));
  $('#open-search').onclick=openSearch;$('#close-search').onclick=()=>closeDialog($('#search-dialog'));$('#global-query').oninput=globalResults;
  $('#global-query').onkeydown=e=>{const items=$$('.command-result');if(!items.length)return;if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();queryIndex=(queryIndex+(e.key==='ArrowDown'?1:-1)+items.length)%items.length;items.forEach((b,i)=>b.classList.toggle('selected',i===queryIndex));items[queryIndex].scrollIntoView({block:'nearest'});}if(e.key==='Enter'){e.preventDefault();items[queryIndex].click();}};
  document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();if(!$('#editor').open)openSearch();}});
  window.addEventListener('hashchange',()=>{render();window.scrollTo({top:0});});document.addEventListener('keydown',e=>{if(e.key==='Escape'){setNavigation(false);}});
  if(serverURL){$('#publish-changes').hidden=false;$('.preview-notice p').innerHTML='<strong>Website workspace</strong><span> Drafts save to the server. Publish changes to update your website.</span>';$('.sidebar-bottom small').textContent='Shared drafts · Publish when ready.';$('.preview-label').textContent='Connected';$$('.editor-note').forEach(node=>node.innerHTML='<span class="status-dot"></span> Server draft · Publish changes to update your website.');}
  fetch(serverURL||document.body.dataset.contentUrl).then(r=>{if(!r.ok)throw Error('Content unavailable');return r.json();}).then(data=>{if(serverURL){const legacy=store;useServerWorkspace(data);if(!Object.keys(data.state).length&&(legacy.drafts.length||legacy.services?.length||legacy.faqTopics?.length||legacy.galleryCategories?.length)){store=legacy;updateWorkspace();render();scheduleServerSave();}}else{records=[...data,...(window.DashboardLocations||[]),...(window.DashboardFAQs||[])];updateWorkspace();render();}}).catch(()=>{$('#view').innerHTML='<div class="panel empty"><h3>Could not load website content</h3><p>Reload the page to try again.</p></div>';});
})();
