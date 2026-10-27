(() => {
  document.querySelectorAll('.partner-marquee').forEach(marquee => {
    marquee.addEventListener('focusout', () => requestAnimationFrame(() => {
      if (!marquee.contains(document.activeElement)) marquee.scrollLeft = 0;
    }));
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver(entries => {
        marquee.classList.toggle('is-offscreen', !entries[0].isIntersecting);
      });
      observer.observe(marquee);
    }
  });
})();
