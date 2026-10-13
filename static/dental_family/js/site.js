/* Plain browser JavaScript. No React, Next.js, Tailwind runtime, or build step. */
(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const animate = (element, frames, options) => {
    if (!reduced.matches && element?.animate) return element.animate(frames, options);
  };


  // Search/filter treatments and reveal listing cards in batches of six.
  $$('[data-treatment-library], [data-article-library]').forEach(grid => {
    const articles=grid.hasAttribute('data-article-library');
    const cards=$$(articles?'.blog-card':'.treatment-card--card',grid),batch=6;
    if(articles&&cards.length<=batch)return;
    const search=articles?null:$('[data-treatment-search]'),service=articles?null:$('[data-treatment-service]');
    const reset=articles?null:$('[data-treatment-reset]'),resultCount=articles?null:$('[data-treatment-filter-status]');
    const normalize=value=>String(value||'').normalize('NFKD').replace(/\p{M}/gu,'').toLocaleLowerCase().trim();
    let matching=cards,visible=Math.min(batch,cards.length);
    const controls=document.createElement('div');controls.className=articles?'treatment-load-more article-load-more':'treatment-load-more';
    const button=document.createElement('button');button.type='button';button.className='button';button.textContent='See more';button.setAttribute('aria-controls',grid.id);
    const status=document.createElement('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');controls.append(button,status);grid.after(controls);
    const empty=document.createElement('div');empty.className='treatment-library-empty';empty.hidden=true;
    empty.innerHTML='<h3>No treatments found</h3><p>Try another search or choose a different service.</p><button type="button" class="button">Clear filters</button>';
    if(!articles)grid.after(empty);
    function update(){const shown=new Set(matching.slice(0,visible));cards.forEach(card=>card.hidden=!shown.has(card));status.textContent=`${Math.min(visible,matching.length)} of ${matching.length} ${articles?'articles':'treatments'}`;button.hidden=visible>=matching.length;if(!articles){grid.hidden=!matching.length;empty.hidden=!!matching.length;if(resultCount)resultCount.textContent=`${matching.length} ${matching.length===1?'treatment':'treatments'}`;if(reset)reset.hidden=!normalize(search?.value)&&!service?.value;}}
    function filter(){const query=normalize(search?.value),selected=service?.value||'';matching=cards.filter(card=>(!selected||card.dataset.service===selected)&&normalize(card.dataset.search||`${$('h3',card)?.textContent||''} ${$('p',card)?.textContent||''}`).includes(query));visible=Math.min(batch,matching.length);update();}
    search?.addEventListener('input',filter);service?.addEventListener('change',filter);
    if(service?.dataset.servicesUrl){
      const refreshServices=()=>fetch(service.dataset.servicesUrl,{headers:{Accept:'application/json'},cache:'no-store'})
        .then(response=>{if(!response.ok)throw new Error('Services unavailable');return response.json();})
        .then(data=>{
          if(!Array.isArray(data.services)||!data.services.every(item=>typeof item.id==='string'&&typeof item.name==='string'))return;
          const selected=service.value;
          service.replaceChildren(new Option('All services',''),...data.services.map(item=>new Option(item.name,item.id)));
          service.value=data.services.some(item=>item.id===selected)?selected:'';
          filter();
        }).catch(()=>{/* Keep rendered options if the backend is temporarily unavailable. */});
      refreshServices();
      window.addEventListener('focus',refreshServices);
    }
    const clearFilters=()=>{if(search)search.value='';if(service)service.value='';filter();search?.focus({preventScroll:true});};
    $('button',empty).addEventListener('click',clearFilters);reset?.addEventListener('click',clearFilters);
    button.addEventListener('click',()=>{const firstNew=visible;visible=Math.min(visible+batch,matching.length);update();matching.slice(firstNew,visible).forEach(card=>animate(card,[{opacity:0,transform:'translateY(12px)'},{opacity:1,transform:'none'}],{duration:300,easing:'cubic-bezier(.22,1,.36,1)'}));matching[firstNew]?.focus({preventScroll:true});});
    update();
  });

  // Navigation: desktop hover/focus panels and the mobile menu.
  const nav = $('#main-nav');
  const toggle = $('.menu-toggle');
  const desktop = matchMedia('(min-width: 761px)');
  const items = $$('.doctor-nav--item');
  function closePanels(except) {
    items.forEach(item => {
      if (item !== except) {
        const panel = $('.doctor-nav--dropdown', item);
        if (panel) panel.hidden = true;
      }
    });
  }
  function closeMenu() {
    nav?.classList.remove('open');
    if (toggle) {
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Open navigation');
      toggle.textContent = '☰';
    }
    closePanels();
    $$('.more-nav').forEach(details => { details.open = false; });
  }
  items.forEach(item => {
    const panel = $('.doctor-nav--dropdown', item);
    if (!panel) return;
    const open = () => {
      if (!desktop.matches) return;
      closePanels(item);
      panel.hidden = false;
    };
    item.addEventListener('mouseenter', open);
    item.addEventListener('mouseleave', () => { panel.hidden = true; });
    item.addEventListener('focusin', open);
    item.addEventListener('focusout', event => {
      if (!item.contains(event.relatedTarget)) panel.hidden = true;
    });
  });
  toggle?.addEventListener('click', () => {
    const opening = !nav.classList.contains('open');
    closeMenu();
    if (opening) {
      nav.classList.add('open');
      toggle.setAttribute('aria-expanded', 'true');
      toggle.setAttribute('aria-label', 'Close navigation');
      toggle.textContent = '✕';
      animate(nav, [{opacity: .4, transform: 'translateY(-8px)'}, {opacity: 1, transform: 'none'}], {duration: 220});
    }
  });
  nav?.addEventListener('click', event => { if (event.target.closest('a')) closeMenu(); });
  document.addEventListener('pointerdown', event => {
    if (!nav?.contains(event.target) && !toggle?.contains(event.target)) closeMenu();
    $$('.more-nav').forEach(details => { if (!details.contains(event.target)) details.open = false; });
  });
  document.addEventListener('focusin', event => {
    if (!nav?.contains(event.target) && !toggle?.contains(event.target)) closeMenu();
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const explore = $('.more-nav[open]');
    const openPanel = items.find(item => !$('.doctor-nav--dropdown', item)?.hidden);
    if (explore) { explore.open = false; $('summary', explore)?.focus(); }
    else if (openPanel) { closePanels(); $('.doctor-nav--trigger', openPanel)?.focus(); closePanels(); }
    else if (nav?.classList.contains('open')) { closeMenu(); toggle?.focus(); }
  });
  desktop.addEventListener('change', closeMenu);

  // Original spring-like reading progress, implemented with requestAnimationFrame.
  const progress = $('.reading-progress');
  let progressTarget = 0, progressValue = 0, progressFrame = 0;
  function tickProgress() {
    progressValue = reduced.matches ? progressTarget : progressValue + (progressTarget - progressValue) * .18;
    if (progress) progress.style.transform = `scaleX(${progressValue})`;
    if (Math.abs(progressTarget - progressValue) > .0001) progressFrame = requestAnimationFrame(tickProgress);
    else progressFrame = 0;
  }
  function updateProgress() {
    const distance = document.documentElement.scrollHeight - innerHeight;
    progressTarget = distance > 0 ? scrollY / distance : 0;
    if (!progressFrame) progressFrame = requestAnimationFrame(tickProgress);
  }
  addEventListener('scroll', updateProgress, {passive: true});
  addEventListener('resize', updateProgress);
  updateProgress();
  $$('a[href="#top"]').forEach(link => link.addEventListener('click', event => {
    event.preventDefault();
    scrollTo({top: 0, left: 0, behavior: reduced.matches ? 'instant' : 'smooth'});
  }));

  // Viewport entrances, hero stagger, and motion links.
  const entranceObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const node = entry.target;
      const hero = node.hasAttribute('data-hero-enter');
      animate(node, [{opacity: hero ? .6 : .7, transform: `translateY(${hero ? 16 : 18}px)`}, {opacity: 1, transform: 'none'}], {
        duration: hero ? 700 : 650, delay: Number(node.dataset.heroEnter || 0) * 1000,
        easing: 'cubic-bezier(.22,1,.36,1)',
      });
      entranceObserver.unobserve(node);
    });
  }, {threshold: .08});
  $$('[data-reveal], [data-hero-enter]').forEach(node => entranceObserver.observe(node));

  // Gentle parallax follows the pointer, retaining the source spring parameters.
  const scene = $('.hero--scene'), layer = $('.hero--imageLayer');
  if (scene && layer) {
    let targetX = 0, targetY = 0, x = 0, y = 0, vx = 0, vy = 0, frame = 0, previous = 0;
    function step(time) {
      const dt = Math.min((time - (previous || time)) / 1000, .032) || 1 / 60;
      previous = time;
      vx += (70 * (targetX - x) - 25 * vx) * dt;
      vy += (70 * (targetY - y) - 25 * vy) * dt;
      x += vx * dt; y += vy * dt;
      layer.style.transform = `translate(${x}px, ${y}px)`;
      if (Math.abs(targetX-x)+Math.abs(targetY-y)+Math.abs(vx)+Math.abs(vy) > .01) frame = requestAnimationFrame(step);
      else {frame = 0; previous = 0;}
    }
    const schedule = () => { if (!frame) frame = requestAnimationFrame(step); };
    scene.addEventListener('pointermove', event => {
      if (reduced.matches || event.pointerType !== 'mouse') return;
      const rect = scene.getBoundingClientRect();
      targetX = (event.clientX-rect.left-rect.width/2)/rect.width*-16;
      targetY = (event.clientY-rect.top-rect.height/2)/rect.height*-12;
      schedule();
    });
    scene.addEventListener('pointerleave', () => {targetX = targetY = 0; schedule();});
  }

  // Count-up figures keep their hidden sizers and accessible final values.
  const statsObserver = new IntersectionObserver(entries => entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    const stat = entry.target, number = $('.clinic-stats--animatedNumber', stat);
    const value = number?.textContent || '', suffix = value.endsWith('K') ? 'K' : '';
    if (number && !reduced.matches) {
      const final = parseInt(value, 10), delay = Number(stat.dataset.statIndex || 0) * 120;
      setTimeout(() => {
        const start = performance.now();
        const count = now => {
          const t = Math.min((now-start)/1500, 1);
          number.textContent = `${Math.round(final*(1-Math.pow(1-t,3)))}${suffix}`;
          if (t < 1) requestAnimationFrame(count);
        };
        requestAnimationFrame(count);
        animate(stat, [{opacity:.5,transform:'translateY(12px)'},{opacity:1,transform:'none'}], {duration:500});
      }, delay);
    }
    statsObserver.unobserve(stat);
  }), {threshold:.6});
  $$('.clinic-stats--stat').forEach((stat, index) => {stat.dataset.statIndex = index; statsObserver.observe(stat);});

  // Accessible accordion controls; height transitions match the source duration.
  $$('.accordion-item').forEach(item => {
    const button = $('h3 button', item), panel = $('.accordion-panel', item);
    if (!button || !panel) return;
    let running;
    button.addEventListener('click', () => {
      const opening = button.getAttribute('aria-expanded') !== 'true';
      const height = panel.getBoundingClientRect().height;
      running?.cancel();
      button.setAttribute('aria-expanded', String(opening));
      item.classList.toggle('expanded', opening);
      panel.setAttribute('aria-hidden', String(!opening));
      panel.inert = !opening;
      const end = opening ? panel.firstElementChild.getBoundingClientRect().height : 0;
      panel.style.height = opening ? 'auto' : '0px';
      panel.style.opacity = opening ? '1' : '0';
      running = animate(panel, [{height:`${height}px`,opacity:opening?0:1},{height:`${end}px`,opacity:opening?1:0}], {
        duration:300,easing:'cubic-bezier(.22,1,.36,1)',
      });
      const vertical = $$('.accordion-plus path', item)[1];
      if (vertical) { vertical.style.opacity = opening ? '0' : '1'; vertical.style.transform = opening ? 'scaleY(0)' : 'none'; }
    });
  });

  // Before/after image slider.
  $$('[data-comparison]').forEach(root => {
    const input = $('input[type=range]', root), before = $('.smile-comparison--before', root), divider = $('.smile-comparison--divider', root);
    const update = () => {
      const value = Number(input.value);
      before.style.clipPath = `inset(0 ${100-value}% 0 0)`;
      divider.style.left = `${value}%`;
      input.setAttribute('aria-valuetext', `${value}% before, ${100-value}% after`);
    };
    input.addEventListener('input', update);
    update();
  });

  // Testimonials: fade/slide, six-second autoplay, focus/hover pause, swipe, dots.
  const carousel = $('[aria-roledescription=carousel]');
  if (carousel) {
    const slides = $$('[aria-roledescription=slide]', carousel), dots = $$('[aria-label^="Show review"]', carousel);
    const counter = $('.patient-reviews--cardFoot > span:last-child', carousel);
    let active = 0, timer, hovered = false, focused = false, visible = false, paused = false, touch;
    function schedule() {
      clearTimeout(timer);
      const playing = !reduced.matches && !hovered && !focused && visible && !paused && !document.hidden;
      $('#patient-review-cards').setAttribute('aria-live', playing ? 'off' : 'polite');
      if (playing) timer = setTimeout(() => select(active+1), 6000);
    }
    function select(index) {
      active = (index+slides.length)%slides.length;
      slides.forEach((slide, i) => {
        const current = i === active;
        slide.setAttribute('aria-hidden', String(!current)); slide.inert = !current;
        slide.style.visibility = current ? 'visible' : 'hidden';
        slide.style.opacity = current ? '1' : '0';
        slide.style.transform = current ? 'none' : 'translateX(14px)';
        if (current) animate(slide, [{opacity:0,transform:'translateX(14px)'},{opacity:1,transform:'none'}], {duration:400});
      });
      dots.forEach((dot,i) => {if(i===active)dot.setAttribute('aria-current','true');else dot.removeAttribute('aria-current');});
      if (counter) counter.firstChild.textContent = `${String(active+1).padStart(2,'0')} `;
      schedule();
    }
    dots.forEach((dot,i) => dot.addEventListener('click', () => select(i)));
    $('[aria-label="Previous review"]',carousel)?.addEventListener('click',()=>select(active-1));
    $('[aria-label="Next review"]',carousel)?.addEventListener('click',()=>select(active+1));
    carousel.addEventListener('mouseenter',()=>{hovered=true;schedule();});
    carousel.addEventListener('mouseleave',()=>{hovered=false;schedule();});
    carousel.addEventListener('focusin',()=>{focused=true;schedule();});
    carousel.addEventListener('focusout',event=>{if(!carousel.contains(event.relatedTarget)){focused=false;schedule();}});
    carousel.addEventListener('touchstart',event=>{touch=event.touches[0].clientX;paused=true;schedule();},{passive:true});
    carousel.addEventListener('touchend',event=>{const distance=touch-event.changedTouches[0].clientX;if(Math.abs(distance)>45)select(active+(distance>0?1:-1));},{passive:true});
    document.addEventListener('visibilitychange',schedule);
    reduced.addEventListener('change',schedule);
    new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;schedule();},{threshold:.25}).observe(carousel.closest('section'));
  }

  // Gallery filters and native dialog lightbox, including keyboard navigation.
  const gallery = $('.gallery-grid'), dialog = $('dialog.lightbox');
  if (gallery && dialog) {
    const cards = $$('button',gallery), filters = $$('.filter-row button');
    const image = $('.lightbox-image img',dialog), caption = $('[aria-live]',dialog);
    let active=0, opener, imageAnimation;
    function show(index) {
      active=(index+cards.length)%cards.length;
      const source=$('img',cards[active]);
      imageAnimation?.cancel();
      image.parentElement.style.opacity='1';
      image.src=source.src; image.alt=source.alt; image.removeAttribute('srcset');
      caption.textContent=`${source.alt} · ${active+1}/${cards.length}`;
      imageAnimation=animate(image.parentElement,[{opacity:.3},{opacity:1}],{duration:450});
    }
    function close() {dialog.close();opener?.focus();}
    cards.forEach((card,index)=>card.addEventListener('click',()=>{opener=card;show(index);dialog.showModal();}));
    filters.forEach(button=>button.addEventListener('click',()=>{
      const category=$('.filter-label',button).textContent;
      const previous=new Map(cards.filter(card=>!card.hidden).map(card=>[card,card.getBoundingClientRect()]));
      const oldMarker=$('.filter-active')?.getBoundingClientRect();
      filters.forEach(filter=>{
        const current=filter===button;
        filter.setAttribute('aria-pressed',String(current));
        $('.filter-active',filter)?.remove();
        if(current){
          const marker=document.createElement('span');marker.className='filter-active';marker.setAttribute('aria-hidden','true');filter.prepend(marker);
          if(oldMarker){const rect=marker.getBoundingClientRect();animate(marker,[{transform:`translate(${oldMarker.left-rect.left}px, ${oldMarker.top-rect.top}px) scaleX(${oldMarker.width/rect.width})`},{transform:'none'}],{duration:250,easing:'cubic-bezier(.22,1,.36,1)'});}
        }
      });
      cards.forEach(card=>{
        card.hidden=category!=='All photos'&&card.dataset.category!==category;
      });
      cards.filter(card=>!card.hidden).forEach(card=>{
        const before=previous.get(card),after=card.getBoundingClientRect();
        const first=before?{opacity:1,transform:`translate(${before.left-after.left}px, ${before.top-after.top}px)`}:{opacity:0,transform:'scale(.97)'};
        animate(card,[first,{opacity:1,transform:'none'}],{duration:300,easing:'cubic-bezier(.22,1,.36,1)'});
      });
    }));
    $('.lightbox-close',dialog).addEventListener('click',close);
    $('[aria-label="Previous photo"]',dialog).addEventListener('click',()=>show(active-1));
    $('[aria-label="Next photo"]',dialog).addEventListener('click',()=>show(active+1));
    dialog.addEventListener('click',event=>{if(event.target===dialog)close();});
    dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
    document.addEventListener('keydown',event=>{if(!dialog.open)return;if(event.key==='ArrowRight'){event.preventDefault();show(active+1);}if(event.key==='ArrowLeft'){event.preventDefault();show(active-1);}});
  }

  // Preserve the existing email composer. It does not submit to a backend.
  $$('[data-contact-form]').forEach(form=>{
    const textarea=$('textarea',form), count=$('.contact-form--messageMeta > span',form);
    const status=$('[data-form-status]',form);
    function clear(input) {
      input.setAttribute('aria-invalid','false');
      const error=document.getElementById(`${input.id}-error`);error?.remove();
      const described=(input.getAttribute('aria-describedby')||'').split(' ').filter(value=>value&&value!==`${input.id}-error`);
      if(described.length)input.setAttribute('aria-describedby',described.join(' '));else input.removeAttribute('aria-describedby');
    }
    form.addEventListener('input',event=>{
      status.hidden=true;
      if(event.target.matches('input,textarea'))clear(event.target);
      if(count)count.textContent=`${textarea.value.length}/2,000`;
    });
    form.addEventListener('submit',event=>{
      event.preventDefault();
      let first;
      for(const [name,message] of [['name','Please enter your name.'],['email','Please enter a valid email address.'],['message','Please tell us how we can help.']]) {
        const input=form.elements.namedItem(name);clear(input);
        if(!input.value.trim()||(name==='email'&&!input.validity.valid)) {
          const error=document.createElement('p');error.id=`${input.id}-error`;error.className='contact-form--error';error.textContent=message;
          input.closest('.contact-form--field').append(error);
          input.setAttribute('aria-invalid','true');input.setAttribute('aria-describedby',`${input.getAttribute('aria-describedby')||''} ${error.id}`.trim());
          first ||= input;
        }
      }
      if(first){first.focus();return;}
      const data=new FormData(form),topic=data.get('topic');
      const body=`Name: ${String(data.get('name')).trim()}\nReply email: ${String(data.get('email')).trim()}\nTopic: ${topic}\n\n${textarea.value.trim()}`;
      location.href=`mailto:${encodeURIComponent(form.dataset.contactEmail||'info@drteethfamilydental.com')}?subject=${encodeURIComponent(`Website inquiry: ${topic}`)}&body=${encodeURIComponent(body)}`;
      status.hidden=false;
    });
  });
  $$('[data-retry]').forEach(button=>button.addEventListener('click',()=>location.reload()));
})();
