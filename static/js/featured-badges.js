/**
 * Featured logos marquee — clones the badge set so CSS can scroll seamlessly.
 * Safe to call once on DOM ready. Does nothing if reduced-motion is preferred.
 */
(function () {
  function initFeaturedMarquee() {
    var track = document.querySelector('[data-featured-track]');
    if (!track || track.dataset.featuredReady === '1') return;

    var set = track.querySelector('.featured-badges__set');
    if (!set || !set.children.length) return;

    // Respect accessibility
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      track.dataset.featuredReady = '1';
      return;
    }

    // Clone set enough times to always fill ~2 viewports (smooth loop)
    var viewport = track.parentElement;
    var minWidth = (viewport && viewport.offsetWidth ? viewport.offsetWidth : 800) * 2;
    var guard = 0;
    while (track.scrollWidth < minWidth && guard < 8) {
      track.appendChild(set.cloneNode(true));
      guard++;
    }
    // Always at least one clone for seamless -50% style loops
    if (track.querySelectorAll('.featured-badges__set').length < 2) {
      track.appendChild(set.cloneNode(true));
    }

    // Shift by width of first set only
    var first = track.querySelector('.featured-badges__set');
    if (first) {
      var shift = first.offsetWidth;
      track.style.setProperty('--featured-shift', '-' + shift + 'px');
      // Duration scales with content width so speed feels constant
      var pxPerSec = 40; // gentle professional pace
      var duration = Math.max(28, Math.round(shift / pxPerSec));
      track.style.animationDuration = duration + 's';
    }

    track.dataset.featuredReady = '1';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFeaturedMarquee);
  } else {
    initFeaturedMarquee();
  }

  // Recalc on resize (debounced)
  var t;
  window.addEventListener('resize', function () {
    clearTimeout(t);
    t = setTimeout(function () {
      var track = document.querySelector('[data-featured-track]');
      if (!track) return;
      var first = track.querySelector('.featured-badges__set');
      if (!first) return;
      var shift = first.offsetWidth;
      track.style.setProperty('--featured-shift', '-' + shift + 'px');
      track.style.animationDuration = Math.max(28, Math.round(shift / 40)) + 's';
    }, 150);
  });
})();
