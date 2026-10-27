(() => {
  document.querySelectorAll(".partner-marquee").forEach(marquee => {
    const button = document.querySelector(`[aria-controls="${marquee.id}"]`);
    if (!marquee || !button) return;
    let paused = false;
    function update() {
      marquee.classList.toggle("is-paused", paused);
      button.hidden = false;
      button.setAttribute("aria-pressed", String(paused));
      button.setAttribute("aria-label", paused ? "Resume partner carousel" : "Pause partner carousel");
      button.querySelector(".partner-pause-label").textContent = paused ? "Resume" : "Pause";
      button.firstElementChild.textContent = paused ? "▷" : "Ⅱ";
    }
    button.addEventListener("click", () => { paused = !paused; update(); });
    marquee.addEventListener("focusout", () => requestAnimationFrame(() => {
      if (!marquee.contains(document.activeElement)) marquee.scrollLeft = 0;
    }));
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(entries => {
        marquee.classList.toggle("is-offscreen", !entries[0].isIntersecting);
      });
      observer.observe(marquee);
    }
    update();
  });
})();
