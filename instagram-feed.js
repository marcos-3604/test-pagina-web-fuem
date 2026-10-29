/* Optional public feed: generated privately by instagram_feed.py. No Meta token. */
(() => {
  'use strict';
  const script = document.currentScript;
  if (!script || !document.querySelector('.news-grid,.gallery-grid')) return;
  const feedURL = new URL('./instagram-feed.json', script.src);
  const en = document.documentElement.lang.startsWith('en');
  const home = document.body.dataset.page === 'index';
  const node = (tag, className, text) => {
    const value = document.createElement(tag);
    if (className) value.className = className;
    if (text !== undefined) value.textContent = text;
    return value;
  };
  const shortcode = value => {
    try {
      const url = new URL(value);
      if (url.protocol !== 'https:' || !['instagram.com', 'www.instagram.com'].includes(url.hostname) || url.username || url.password || url.port) return '';
      return url.pathname.match(/^\/(?:[\w.]+\/)?(?:p|reel)\/([A-Za-z0-9_-]{1,100})\/?$/)?.[1] || '';
    } catch { return ''; }
  };
  const validate = post => {
    if (!post || typeof post.id !== 'string' || !/^\d{1,40}$/.test(post.id) || typeof post.caption !== 'string' || post.caption.length > 4400 || [...post.caption].length > 2200 || !shortcode(post.url) || typeof post.timestamp !== 'string') return null;
    if (!/^\.\/instagram-media\/[0-9]{1,40}-[a-f0-9]{12}\.(jpg|png|webp)$/.test(post.image)) return null;
    const image = new URL(post.image, feedURL);
    if (image.origin !== location.origin || !['IMAGE', 'CAROUSEL_ALBUM'].includes(post.mediaType)) return null;
    const time = new Date(post.timestamp);
    if (!Number.isFinite(time.getTime())) return null;
    return { ...post, image: image.href, time, shortcode: shortcode(post.url) };
  };
  const title = post => post.caption.split('\n').find(line => line.trim())?.trim().slice(0, 150) || (en ? 'From the team’s Instagram' : 'Desde el Instagram del equipo');
  const photo = post => {
    const image = node('img'); image.src = post.image; image.alt = title(post); image.loading = 'lazy'; image.decoding = 'async';
    return image;
  };
  const link = (post, className) => {
    const card = node('a', className); card.href = post.url; card.target = '_blank'; card.rel = 'noopener noreferrer'; card.dataset.instagramPost = post.id;
    return card;
  };
  const newsCard = (post, username) => {
    const card = link(post, 'news-card hover-tile reveal visible');
    const picture = node('div', 'news-image'); picture.append(photo(post), node('span', 'instagram-badge', '↗ INSTAGRAM'));
    const copy = node('div', 'news-card-copy');
    const label = node('p', 'small-label', '@' + username.toUpperCase() + ' ');
    label.append(node('span', '', new Intl.DateTimeFormat(en ? 'en-GB' : 'es-ES', { timeZone: 'Europe/Madrid' }).format(post.time)));
    copy.append(label, node('h3', '', title(post)), node('p', '', post.caption.slice(0, 450)), node('span', 'card-arrow', en ? 'View post ↗' : 'Ver publicación ↗'));
    card.append(picture, copy); return card;
  };
  const galleryCard = post => {
    const card = link(post, 'gallery-tile hover-tile reveal visible'); card.dataset.category = 'equipo';
    card.append(photo(post), node('span', '', title(post) + ' ↗ INSTAGRAM'));
    return card;
  };
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  fetch(feedURL, { credentials: 'omit', cache: 'no-cache', signal: controller.signal })
    .then(async response => {
      if (!response.ok) return null;
      if (Number(response.headers.get('content-length') || 0) > 160000) return null;
      if (!response.body?.getReader) return null;
      const reader = response.body.getReader();
      const chunks = []; let size = 0;
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > 160000) { await reader.cancel(); return null; }
        chunks.push(value);
      }
      const bytes = new Uint8Array(size); let offset = 0;
      chunks.forEach(chunk => { bytes.set(chunk, offset); offset += chunk.byteLength; });
      return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
    })
    .then(feed => {
      if (!feed || feed.schema !== 1 || !/^[A-Za-z0-9_.]{1,30}$/.test(feed.username) || !Array.isArray(feed.posts) || feed.posts.length > 50) return;
      const seen = new Set();
      const posts = feed.posts.map(validate).filter(post => post && !seen.has(post.shortcode) && seen.add(post.shortcode)).sort((a, b) => b.time - a.time).slice(0, 24);
      if (!posts.length) return; // Keep curated fallback when there are no eligible photos.
      document.querySelectorAll('.news-grid').forEach(grid => {
        const selected = posts.slice(0, home ? 3 : 24);
        const keys = new Set(selected.map(post => post.shortcode));
        const cards = selected.map(post => newsCard(post, feed.username));
        grid.querySelectorAll('a.news-card').forEach(card => { if (keys.has(shortcode(card.href))) card.remove(); });
        grid.prepend(...cards);
        // The home retains three Instagram cards while preserving independent club news.
        if (home) {
          let count = 0;
          grid.querySelectorAll('a.news-card').forEach(card => { if (shortcode(card.href) && ++count > 3) card.remove(); });
        }
      });
      document.querySelectorAll('.gallery-grid').forEach(grid => {
        const current = new Set(Array.from(grid.querySelectorAll('[data-instagram-post]'), card => card.dataset.instagramPost));
        const cards = posts.filter(post => !current.has(post.id)).map(galleryCard);
        const updateFilter = () => {
          const active = document.querySelector('[data-filter].active')?.dataset.filter || 'all';
          cards.forEach(card => { card.hidden = active !== 'all' && active !== 'equipo'; });
        };
        grid.prepend(...cards); updateFilter();
        document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', updateFilter));
      });
    })
    .catch(() => { /* A failed optional update must not block the existing site. */ })
    .finally(() => clearTimeout(timeout));
})();
