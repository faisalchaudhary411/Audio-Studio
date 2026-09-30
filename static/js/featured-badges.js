/**
 * Featured badges marquee
 * - HTML has ONE set of badges (no doubles on screen)
 * - This script clones the set, then starts CSS animation
 */
(function () {
  function init() {
    var track = document.querySelector('[data-featured-track]');
    if (!track || track.dataset.ready === '1') return;

    var set = track.querySelector('[data-featured-set]');
    if (!set || !set.children.length) return;

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      track.dataset.ready = '1';
      return;
    }

    // Clone until we cover ~2x viewport (smooth loop)
    var viewport = track.parentElement;
    var need = (viewport && viewport.offsetWidth ? viewport.offsetWidth : 900) * 2;
    var guard = 0;
    while (track.scrollWidth < need && guard < 6) {
      var clone = set.cloneNode(true);
      clone.removeAttribute('data-featured-set');
      clone.setAttribute('aria-hidden', 'true');
      track.appendChild(clone);
      guard++;
    }
    if (track.querySelectorAll('.featured-badges__set').length < 2) {
      var c = set.cloneNode(true);
      c.removeAttribute('data-featured-set');
      c.setAttribute('aria-hidden', 'true');
      track.appendChild(c);
    }

    // Shift by width of the original set only
    var w = set.offsetWidth;
    if (w < 10) {
      // images may not be laid out yet — retry once
      track.dataset.ready = '0';
      setTimeout(init, 300);
      return;
    }

    track.style.setProperty('--featured-shift', '-' + w + 'px');
    var duration = Math.max(25, Math.round(w / 35)); // ~35px/sec
    track.style.setProperty('--featured-duration', duration + 's');
    track.classList.add('is-animated');
    track.dataset.ready = '1';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.addEventListener('load', function () {
    var track = document.querySelector('[data-featured-track]');
    if (track && track.dataset.ready !== '1') init();
    else if (track) {
      var set = track.querySelector('[data-featured-set]');
      if (set && set.offsetWidth > 10) {
        track.style.setProperty('--featured-shift', '-' + set.offsetWidth + 'px');
      }
    }
  });
})();
