// ===== VoxCraft notifications.js =====
// Fetches /api/announcements (admin-published discounts/updates) and renders
// them two ways: a bell dropdown (all live announcements) and, for at most
// one item flagged "banner", a dismissible top strip. No accounts involved —
// "read" and "dismissed" state both live in localStorage on this device.

const NOTIF_SEEN_KEY = 'voxcraft_notif_last_seen';   // newest id the visitor has opened the bell to
const NOTIF_DISMISSED_KEY = 'voxcraft_notif_dismissed'; // banner ids explicitly closed

function notifGetLastSeen(){
  return parseInt(localStorage.getItem(NOTIF_SEEN_KEY) || '0', 10) || 0;
}
function notifSetLastSeen(id){
  const n = parseInt(id, 10);
  if(!Number.isNaN(n) && n > notifGetLastSeen()){
    localStorage.setItem(NOTIF_SEEN_KEY, String(n));
  }
}
function notifGetDismissed(){
  try{ return JSON.parse(localStorage.getItem(NOTIF_DISMISSED_KEY) || '[]'); }
  catch(e){ return []; }
}
function notifDismiss(id){
  const list = notifGetDismissed();
  if(!list.includes(id)){
    list.push(id);
    // cap so this never grows unbounded for a long-lived visitor
    while(list.length > 50) list.shift();
    localStorage.setItem(NOTIF_DISMISSED_KEY, JSON.stringify(list));
  }
}

const NOTIF_TYPE_LABEL = { discount: 'Discount', update: 'Update', general: 'News' };

function notifRenderList(items){
  const list = document.getElementById('notif-list');
  if(!list) return;
  if(!items.length){
    list.innerHTML = '<div class="notif-dropdown__empty">Nothing new right now.</div>';
    return;
  }
  list.innerHTML = items.map(a => `
    <div class="notif-item">
      <span class="notif-item__type notif-item__type--${a.type}">${NOTIF_TYPE_LABEL[a.type] || 'News'}</span>
      <div class="notif-item__title">${notifEscape(a.title)}</div>
      <div class="notif-item__msg">${notifEscape(a.message)}</div>
      ${a.link_url ? `<a class="notif-item__link" href="${notifEscape(a.link_url)}">${notifEscape(a.link_text || 'Learn more')} →</a>` : ''}
    </div>
  `).join('');
}

function notifEscape(str){
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}

function notifInitBell(items){
  const bell = document.getElementById('notif-bell');
  const dropdown = document.getElementById('notif-dropdown');
  const badge = document.getElementById('notif-badge');
  if(!bell || !dropdown || !badge) return;

  const lastSeen = notifGetLastSeen();
  const unread = items.filter(a => parseInt(a.id, 10) > lastSeen).length;
  if(unread > 0){
    badge.textContent = unread > 9 ? '9+' : String(unread);
    badge.hidden = false;
  }

  notifRenderList(items);

  bell.addEventListener('click', (e) => {
    e.stopPropagation();
    const open = dropdown.hidden;
    dropdown.hidden = !open;
    bell.setAttribute('aria-expanded', open ? 'true' : 'false');
    if(open && items.length){
      notifSetLastSeen(items[0].id); // items[0] is newest — API returns newest-first
      badge.hidden = true;
    }
  });
  document.addEventListener('click', (e) => {
    if(!dropdown.hidden && !dropdown.contains(e.target) && e.target !== bell){
      dropdown.hidden = true;
      bell.setAttribute('aria-expanded', 'false');
    }
  });
}

const BANNER_AUTO_DISMISS_MS = 12000; // longer so marquee can complete a loop

function notifInitBanner(items){
  const banner = document.getElementById('announce-banner');
  const badgeEl = document.getElementById('announce-banner-badge');
  const textEl = document.getElementById('announce-banner-text');
  const textDup = document.getElementById('announce-banner-text-dup');
  // ...
  const line = `${pick.title} — ${pick.message}`;
  textEl.textContent = line;
  if (textDup) textDup.textContent = line;
  const linkEl = document.getElementById('announce-banner-link');
  const closeEl = document.getElementById('announce-banner-close');
  if(!banner) return;

  const dismissed = notifGetDismissed();
  const pick = items.find(a => a.banner && !dismissed.includes(a.id));
  if(!pick) return;

  badgeEl.textContent = NOTIF_TYPE_LABEL[pick.type] || 'News';
  badgeEl.className = `announce-banner__badge announce-banner__badge--${pick.type}`;
  const line = `${pick.title} — ${pick.message}`;
  textEl.textContent = line;
  if(textDup) textDup.textContent = line;

  if(pick.link_url){
    linkEl.href = pick.link_url;
    linkEl.textContent = pick.link_text || 'Learn more';
    linkEl.hidden = false;
  } else {
    linkEl.hidden = true;
  }

  banner.hidden = false;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    banner.classList.add('is-visible');
  }));

  let dismissTimer = null;
  function hideToast(){
    if(dismissTimer) clearTimeout(dismissTimer);
    notifDismiss(pick.id);
    banner.classList.remove('is-visible');
    setTimeout(() => { banner.hidden = true; }, 350);
  }

  dismissTimer = setTimeout(hideToast, BANNER_AUTO_DISMISS_MS);
  closeEl.addEventListener('click', hideToast);
}

async function notifInit(){
  try{
    const res = await fetch('/api/announcements');
    if(!res.ok) return;
    const items = await res.json();
    if(!Array.isArray(items) || !items.length) return;
    notifInitBell(items);
    notifInitBanner(items);
  } catch(e){
    // silent — a failed notifications fetch shouldn't break the rest of the page
  }
}

document.addEventListener('DOMContentLoaded', notifInit);
