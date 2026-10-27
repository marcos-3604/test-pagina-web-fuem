/* One owner for the silent, inline background video. No demonstration controls. */
(() => {
  const video = document.querySelector('#hero-video');
  if (!video) return;
  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  const limited = matchMedia('(max-width: 768px)').matches || Boolean(connection && (
    connection.saveData || /^(slow-2g|2g)$/.test(connection.effectiveType || '')
  ));
  const source = limited
    ? video.dataset.nightLite || video.dataset.nightHd
    : video.dataset.nightHd || video.dataset.nightLite;
  if (!source) return;

  // These properties must be set before assigning src, especially on iOS.
  video.defaultMuted = true;
  video.muted = true;
  video.autoplay = true;
  video.loop = true;
  video.playsInline = true;
  video.controls = false;
  video.preload = 'auto';
  ['muted', 'autoplay', 'loop', 'playsinline', 'webkit-playsinline'].forEach(name => video.setAttribute(name, ''));
  video.removeAttribute('controls');
  video.setAttribute('disablepictureinpicture', '');
  if ('disablePictureInPicture' in video) video.disablePictureInPicture = true;
  if ('disableRemotePlayback' in video) video.disableRemotePlayback = true;
  video.dataset.nightSrc = source;
  video.dataset.quality = limited ? '900p-lite' : '1080p';

  let pendingPlay = false;
  let gestureRetryArmed = false;
  const gestureEvents = ['pointerdown', 'touchend', 'keydown'];

  function onScreen() {
    const bounds = video.getBoundingClientRect();
    // A synchronous script may run before the hero has acquired its layout.
    // Do not mistake that first zero-sized measurement for a manual pause.
    if (!bounds.width || !bounds.height) return document.readyState === 'loading';
    return bounds.bottom > 0 && bounds.top < innerHeight && bounds.right > 0 && bounds.left < innerWidth;
  }

  function stopWhenHidden() {
    if (!video.paused) video.pause();
    video.dataset.playback = 'paused';
  }

  function disarmGestureRetry() {
    if (!gestureRetryArmed) return;
    gestureRetryArmed = false;
    gestureEvents.forEach(name => document.removeEventListener(name, retryFromGesture, true));
  }

  function armGestureRetry() {
    if (gestureRetryArmed) return;
    gestureRetryArmed = true;
    gestureEvents.forEach(name => document.addEventListener(name, retryFromGesture, { capture: true, passive: true }));
  }

  function playFailed(error) {
    pendingPlay = false;
    if (document.hidden || !onScreen()) {
      stopWhenHidden();
      return;
    }
    video.dataset.playback = error && error.name === 'NotAllowedError' ? 'blocked' : 'waiting';
    // Browser/device policy can require a real gesture. Retry on an actual
    // interaction; never claim playback succeeded or run a polling loop.
    armGestureRetry();
  }

  function tryPlay() {
    if (document.hidden || !onScreen()) {
      stopWhenHidden();
      return;
    }
    if (pendingPlay || !video.paused) return;
    video.muted = true;
    pendingPlay = true;
    video.dataset.playback = 'loading';
    try {
      const promise = video.play();
      if (promise && typeof promise.then === 'function') {
        promise.then(() => {
          pendingPlay = false;
          if (document.hidden || !onScreen()) stopWhenHidden();
          else if (!video.paused) {
            video.dataset.playback = 'playing';
            disarmGestureRetry();
          }
        }, playFailed);
      } else pendingPlay = false;
    } catch (error) {
      playFailed(error);
    }
  }

  function retryFromGesture() { tryPlay(); }

  video.addEventListener('playing', () => {
    if (document.hidden || !onScreen()) {
      stopWhenHidden();
      return;
    }
    video.dataset.playback = 'playing';
    disarmGestureRetry();
  });
  video.addEventListener('loadeddata', tryPlay);
  video.addEventListener('canplay', tryPlay);
  document.addEventListener('DOMContentLoaded', tryPlay, { once: true });
  document.addEventListener('visibilitychange', tryPlay);
  window.addEventListener('pageshow', tryPlay);
  window.addEventListener('pagehide', stopWhenHidden);

  if ('IntersectionObserver' in window) {
    const visibility = new IntersectionObserver(() => tryPlay(), { threshold: 0 });
    visibility.observe(video);
  }
  const intro = document.querySelector('#intro');
  if (intro && 'MutationObserver' in window) {
    const introVisibility = new MutationObserver(() => {
      if (intro.classList.contains('is-done')) {
        tryPlay();
        introVisibility.disconnect();
      }
    });
    introVisibility.observe(intro, { attributes: true, attributeFilter: ['class'] });
  }

  // Choosing and assigning the source once avoids competing downloads/reloads.
  video.src = source;
  tryPlay();
})();
