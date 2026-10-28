const $ = (selector, scope = document) => scope.querySelector(selector);
const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
const intro = $('#intro');
let introFrame, introTimer;
const introStyles = getComputedStyle(intro);
const introRun = parseFloat(introStyles.getPropertyValue('--intro-run')) || 3300;
const introExit = parseFloat(introStyles.getPropertyValue('--intro-exit')) || 500;
function playIntro(force = false) {
  cancelAnimationFrame(introFrame); clearTimeout(introTimer);
  const mobileHome = document.body.dataset.page === 'index' && matchMedia('(max-width: 960px)').matches;
  if (reduceMotion.matches && !force && !mobileHome) { intro.classList.add('is-done'); return; }
  intro.classList.add('intro-requested');
  intro.classList.remove('is-done'); intro.classList.add('replaying');
  void intro.offsetWidth; intro.classList.remove('replaying');
  const start = performance.now();
  function tick(now) {
    const progress = Math.min((now-start)/introRun,1);
    $('#intro-count').textContent = String(Math.round(progress*100)).padStart(3,'0');
    if (progress < 1) introFrame = requestAnimationFrame(tick);
  }
  introFrame = requestAnimationFrame(tick);
  introTimer = setTimeout(()=>intro.classList.add('is-done'),introRun+introExit);
}
let hasSeenIntro = false;
try { hasSeenIntro = sessionStorage.getItem('fuem-intro-v4') === 'seen'; sessionStorage.setItem('fuem-intro-v4','seen'); } catch {}
const mobileHomeIntro = document.body.dataset.page === 'index' && matchMedia('(max-width: 960px)').matches;
if (hasSeenIntro && !mobileHomeIntro) intro.classList.add('is-done'); else playIntro();

reduceMotion.addEventListener('change',()=>{
  if(reduceMotion.matches){intro.classList.add('is-done');$$('.reveal').forEach(e=>e.classList.add('visible'));}
});

const dropdown=$('.nav-dropdown'),dropdownToggle=$('.dropdown-toggle'),mega=$('#club-menu');
function setDropdown(open){dropdown?.classList.toggle('open',open);dropdownToggle?.setAttribute('aria-expanded',String(open));if(mega)mega.inert=!open;}
dropdownToggle?.addEventListener('mouseenter',()=>setDropdown(true));
dropdownToggle?.addEventListener('click',()=>setDropdown(true));
dropdownToggle?.addEventListener('keydown',e=>{if(e.key==='ArrowDown'){e.preventDefault();setDropdown(true);$('a',mega)?.focus();}});
dropdown?.addEventListener('focusout',event=>{
  if(event.relatedTarget && dropdown.contains(event.relatedTarget))return;
  setDropdown(false);
});
$('#header')?.addEventListener('mouseleave',()=>setDropdown(false));
$$('.desktop-nav > a,.header-actions > a,.brand').forEach(a=>a.addEventListener('mouseenter',()=>setDropdown(false)));
document.addEventListener('click',e=>{if(!dropdown?.contains(e.target))setDropdown(false);});
const menuToggle=$('#menu-toggle'),mobileMenu=$('#mobile-menu');
function setMenu(open){
  document.body.classList.toggle('menu-open',open);menuToggle.setAttribute('aria-expanded',String(open));
  menuToggle.setAttribute('aria-label',open?'Cerrar menú':'Abrir menú');mobileMenu.inert=!open;
  $('#contenido').inert=open;$('.footer').inert=open;
  if(open)setDropdown(false);
  else menuToggle.focus({preventScroll:true});
}
menuToggle?.addEventListener('click',()=>setMenu(!document.body.classList.contains('menu-open')));

// The bar follows scroll direction; small movements accumulate to avoid jitter.
const siteHeader = $('#header');
let lastHeaderScroll = Math.max(0, window.scrollY), directionDistance = 0, headerScrollFrame;
function updateHeader() {
  headerScrollFrame = null;
  const y = Math.max(0, window.scrollY), delta = y-lastHeaderScroll;
  lastHeaderScroll = y;
  siteHeader.classList.toggle('is-scrolled',y>24);
  if (y<siteHeader.offsetHeight || document.body.classList.contains('menu-open') ||
      dropdown?.classList.contains('open') || siteHeader.contains(document.activeElement)) {
    siteHeader.classList.remove('is-hidden'); directionDistance=0; return;
  }
  if (!delta) return;
  if (Math.sign(delta)!==Math.sign(directionDistance)) directionDistance=0;
  directionDistance+=delta;
  if (Math.abs(directionDistance)>=8) siteHeader.classList.toggle('is-hidden',directionDistance>0);
}
window.addEventListener('scroll',()=>{
  if (!headerScrollFrame) headerScrollFrame=requestAnimationFrame(updateHeader);
},{passive:true});
siteHeader.addEventListener('focusin',()=>siteHeader.classList.remove('is-hidden'));
window.addEventListener('pageshow',updateHeader);
updateHeader();

$$('a',mobileMenu).forEach(a=>a.addEventListener('click',()=>setMenu(false)));
matchMedia('(min-width:961px)').addEventListener('change',e=>{if(e.matches&&document.body.classList.contains('menu-open'))setMenu(false);});

// Keep keyboard focus inside the visible header and menu while the page is inert.
document.addEventListener('keydown',e=>{
  if(e.key!=='Tab'||!document.body.classList.contains('menu-open'))return;
  const stops=$$('a[href],button:not([disabled])',$('#header')).concat($$('a[href]',mobileMenu)).filter(el=>el.getClientRects().length);
  const first=stops[0],last=stops[stops.length-1];
  if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
  else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){
  if(document.body.classList.contains('menu-open')){setMenu(false);menuToggle.focus();}
  if(dropdown?.classList.contains('open')){setDropdown(false);dropdownToggle.focus();}
}});

function countUp(element){
  if(element.dataset.counted)return;element.dataset.counted='true';if(reduceMotion.matches)return;
  const target=Number(element.dataset.count),decimals=Number(element.dataset.decimals||0);
  const format=new Intl.NumberFormat('es-ES',{minimumFractionDigits:decimals,maximumFractionDigits:decimals});
  const start=performance.now();
  function frame(now){
    if(reduceMotion.matches){element.textContent=format.format(target);return;}
    const progress=Math.min((now-start)/1300,1);element.textContent=format.format(target*(1-Math.pow(1-progress,3)));
    if(progress<1)requestAnimationFrame(frame);
  }requestAnimationFrame(frame);
}
if('IntersectionObserver'in window){
  if(!reduceMotion.matches)document.body.classList.add('motion-ready');
  const reveal=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){
    entry.target.classList.add('visible');if(!entry.target.matches('[data-home-telemetry]'))$$('[data-count]',entry.target).forEach(countUp);reveal.unobserve(entry.target);
  }}),{threshold:.1});$$('.reveal').forEach(e=>reveal.observe(e));
}else $$('.spec-panel').forEach(e=>e.classList.add('visible'));

const systems={
  aero:["01","DISE\u00d1AR EL AIRE.","Analizar c\u00f3mo fluye el aire alrededor del monoplaza para estudiar su comportamiento y desarrollar el conjunto aerodin\u00e1mico.","./assets/responsive/instagram-simulacion-0be7e2d6-960.webp"],
  dynamics:["02","CADA APOYO CUENTA.","Suspensi\u00f3n, direcci\u00f3n y neum\u00e1ticos trabajan en conjunto. La puesta a punto transforma los datos y las sensaciones en decisiones para la pista.","./assets/responsive/gallery-03-1404c9f0-960.webp"],
  power:["03","ENERG\u00cdA EN MOVIMIENTO.","Integrar el conjunto de propulsi\u00f3n es conectar rendimiento, fiabilidad y control. Cada sistema aporta al funcionamiento del monoplaza.","./assets/responsive/gallery-01-dc6df415-960.webp"]
};
const systemTabs=$$('.system-tabs [role=tab]');
function selectSystem(button,focus=false){
  systemTabs.forEach(b=>{b.setAttribute('aria-selected',String(b===button));b.tabIndex=b===button?0:-1;});
  const[number,title,description,image]=systems[button.dataset.system];
  $('.system-number').textContent=number;$('#system-title').textContent=title;$('#system-description').textContent=description;
  $('#system-image').src=image;$('#system-image').alt=title;
  const panel=$('#system-panel');panel.setAttribute('aria-labelledby',button.id);panel.classList.remove('switching');void panel.offsetWidth;panel.classList.add('switching');if(focus)button.focus();
}
systemTabs.forEach((button,i)=>{
  button.addEventListener('click',()=>selectSystem(button));
  button.addEventListener('keydown',e=>{
    let next;if(e.key==='ArrowRight')next=(i+1)%systemTabs.length;if(e.key==='ArrowLeft')next=(i-1+systemTabs.length)%systemTabs.length;
    if(e.key==='Home')next=0;if(e.key==='End')next=systemTabs.length-1;
    if(next!==undefined){e.preventDefault();selectSystem(systemTabs[next],true);}
  });
});

$$('[data-close-dialog]').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));
$$('dialog').forEach(d=>d.addEventListener('click',e=>{
  if(e.target!==d)return;const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();
}));
const contact=$('#contact-dialog');
const contactDescriptions={team:"Cu\u00e9ntanos qu\u00e9 estudias en la Universidad Europea, qu\u00e9 te apasiona y en qu\u00e9 \u00e1rea te gustar\u00eda aportar al equipo.",partner:"Nos gustar\u00eda conocer tu empresa y explorar c\u00f3mo podemos impulsar juntos el proyecto de Formula UEM.",general:"Para conocer m\u00e1s sobre el club o ponerte en contacto con nosotros, escr\u00edbenos. Nos encantar\u00e1 leerte."};
$$('[data-contact]').forEach(b=>b.addEventListener('click',()=>{
  const type=b.dataset.contact;$('#contact-description').textContent=contactDescriptions[type];
  const subject=type==='partner'?"Colaboraci\u00f3n con Formula UEM":type==='team'?"Quiero formar parte de Formula UEM":'Contacto Formula UEM';
  const recipient=type==='partner'?"logisticafuem83@gmail.com":"bomfuem@gmail.com";
  $('#contact-email').href=`mailto:${recipient}?subject=${encodeURIComponent(subject)}`;contact.showModal();
}));
$('#contact-form')?.addEventListener('submit',e=>{
  e.preventDefault();const form=new FormData(e.currentTarget);
  const name=String(form.get('name')).trim(),email=String(form.get('email')).trim(),interest=String(form.get('interest')),message=String(form.get('message')).trim();
  const body=`Hola, equipo de Formula UEM:\n\n${message}\n\nNombre: ${name}\nEmail de contacto: ${email}\nMotivo: ${interest}`;
  const recipient=e.currentTarget.elements.interest.selectedIndex===1?"logisticafuem83@gmail.com":"bomfuem@gmail.com";
  $('#draft-preview').textContent=body;$('#draft-send').href=`mailto:${recipient}?subject=${encodeURIComponent(interest)}&body=${encodeURIComponent(body)}`;$('#draft-dialog').showModal();
});
const galleryDialog=$('#gallery-dialog'),galleryItems=$$('[data-gallery]');let galleryIndex=0;
function showGallery(index){
  const visibleItems=galleryItems.filter(item=>!item.hidden);galleryIndex=(index+visibleItems.length)%visibleItems.length;const item=visibleItems[galleryIndex];
  $('#gallery-large').src=item.dataset.gallery;$('#gallery-large').alt=item.dataset.caption;$('#gallery-caption').textContent=`${galleryIndex+1} / ${visibleItems.length} — ${item.dataset.caption}`;
  if(!galleryDialog.open)galleryDialog.showModal();
}
galleryItems.forEach(item=>item.addEventListener('click',()=>showGallery(galleryItems.filter(i=>!i.hidden).indexOf(item))));
$('#gallery-prev')?.addEventListener('click',()=>showGallery(galleryIndex-1));$('#gallery-next')?.addEventListener('click',()=>showGallery(galleryIndex+1));
galleryDialog?.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'){e.preventDefault();showGallery(galleryIndex-1);}if(e.key==='ArrowRight'){e.preventDefault();showGallery(galleryIndex+1);}});
let galleryTouch;
$('#gallery-large')?.addEventListener('touchstart',e=>{
  galleryTouch=e.touches.length===1?{x:e.touches[0].clientX,y:e.touches[0].clientY}:null;
},{passive:true});
$('#gallery-large')?.addEventListener('touchcancel',()=>{galleryTouch=null;},{passive:true});
$('#gallery-large')?.addEventListener('touchend',e=>{
  if(!galleryTouch||e.touches.length){galleryTouch=null;return;}
  const end=e.changedTouches[0],dx=end.clientX-galleryTouch.x,dy=end.clientY-galleryTouch.y;
  if(Math.abs(dx)>55&&Math.abs(dx)>Math.abs(dy)*1.5)showGallery(galleryIndex+(dx<0?1:-1));
  galleryTouch=null;
},{passive:true});
$$('[data-filter]').forEach(b=>b.addEventListener('click',()=>{
  $$('[data-filter]').forEach(other=>{other.classList.toggle('active',other===b);other.setAttribute('aria-pressed',String(other===b));});
  galleryItems.forEach(item=>{item.hidden=b.dataset.filter!=='all'&&item.dataset.category!==b.dataset.filter;});
}));
