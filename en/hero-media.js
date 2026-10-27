/* Choose once, before the video gets a source, so only one variant downloads. */
(() => {
  const video = document.querySelector("#hero-video");
  if (!video) return;
  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  const limited = Boolean(connection && (
    connection.saveData || /^(slow-2g|2g)$/.test(connection.effectiveType || "")
  ));
  const source = limited ? video.dataset.nightLite : video.dataset.nightHd;
  video.dataset.nightSrc = source;
  video.dataset.quality = limited ? "900p-lite" : "1080p";
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
    video.autoplay = false;
    video.preload = "none";
  }
  video.src = source;
})();
