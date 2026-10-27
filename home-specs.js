/* The requested home animation is independent of the generic page reveals. */
(() => {
  const panel = document.querySelector('[data-home-telemetry]');
  if (!panel) return;
  const rows = [...panel.querySelectorAll('.spec-row')];
  const intro = document.querySelector('#intro');
  const introVisible = () => intro && !intro.classList.contains('is-done') && getComputedStyle(intro).display !== 'none';
  const frames = new Map();
  const format = element => new Intl.NumberFormat(document.documentElement.lang === 'en' ? 'en-GB' : 'es-ES', {
    minimumFractionDigits: Number(element.dataset.decimals || 0),
    maximumFractionDigits: Number(element.dataset.decimals || 0)
  });
  let observer;

  function finish(row) {
    cancelAnimationFrame(frames.get(row));
    frames.delete(row);
    const number = row.querySelector('[data-count]');
    if (number) number.textContent = format(number).format(Number(number.dataset.count));
    row.classList.remove('telemetry-playing');
    row.classList.add('telemetry-complete');
  }

  function playRow(row) {
    if (row.classList.contains('telemetry-complete') || frames.has(row)) return;
    if (!panel.classList.contains('telemetry-activated')) panel.classList.add('telemetry-activated');
    const number = row.querySelector('[data-count]');
    const formatter = number && format(number);
    const target = number && Number(number.dataset.count);
    const delay = rows.indexOf(row) * 140;
    row.style.setProperty('--telemetry-delay', delay + 'ms');
    row.classList.add('telemetry-playing');
    if (number) number.textContent = formatter.format(0);
    const start = performance.now() + delay;
    function tick(now) {
      const progress = Math.max(0, Math.min((now - start) / 1600, 1));
      if (number) number.textContent = formatter.format(target * (1 - Math.pow(1 - progress, 3)));
      if (progress < 1) frames.set(row, requestAnimationFrame(tick));
      else finish(row);
    }
    frames.set(row, requestAnimationFrame(tick));
  }

  function watchRows() {
    observer?.disconnect();
    if ('IntersectionObserver' in window) {
      observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting && !introVisible()) {
            playRow(entry.target);
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.4, rootMargin: '0px 0px -20px 0px' });
      rows.forEach(row => observer.observe(row));
    } else rows.forEach(playRow);
  }

  panel.classList.add('telemetry-ready');
  watchRows();
  if (intro) {
    new MutationObserver(() => {
      if (!introVisible()) watchRows();
    }).observe(intro, { attributes: true, attributeFilter: ['class'] });
  }
  panel.querySelector('[data-replay-telemetry]')?.addEventListener('click', () => {
    frames.forEach(id => cancelAnimationFrame(id));
    frames.clear();
    rows.forEach(row => {
      row.classList.remove('telemetry-playing', 'telemetry-complete');
      const number = row.querySelector('[data-count]');
      if (number) number.textContent = format(number).format(Number(number.dataset.count));
    });
    panel.classList.remove('telemetry-activated');
    void panel.offsetWidth;
    watchRows();
    const bounds = panel.getBoundingClientRect();
    if (bounds.top < 0 || bounds.top > innerHeight * 0.5) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) [...frames.keys()].forEach(finish);
  });
})();
