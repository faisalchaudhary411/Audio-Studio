(function () {
  function startFeaturedMarquee() {
    var viewport = document.querySelector('[data-featured-viewport]');
    var track = document.querySelector('[data-featured-track]');
    var set = document.querySelector('[data-featured-set]');
    if (!viewport || !track || !set) return;
    if (track.dataset.marquee === '1') return;

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      track.dataset.marquee = '1';
      return;
    }

    // Measure after layout
    var setWidth = set.getBoundingClientRect().width;
    if (setWidth < 20) {
      setTimeout(startFeaturedMarquee, 200);
      return;
    }

    // Clone once for seamless loop (only after we know we'll animate)
    var clone = set.cloneNode(true);
    clone.removeAttribute('data-featured-set');
    clone.setAttribute('aria-hidden', 'true');
    // neutralize links in clone for a11y / focus
    clone.querySelectorAll('a').forEach(function (a) {
      a.setAttribute('tabindex', '-1');
    });
    track.appendChild(clone);

    track.dataset.marquee = '1';

    var pos = 0;
    var speed = 0.4; // px per frame ~24px/s at 60fps
    var paused = false;

    viewport.addEventListener('mouseenter', function () { paused = true; });
    viewport.addEventListener('mouseleave', function () { paused = false; });
    viewport.addEventListener('touchstart', function () { paused = true; }, { passive: true });
    viewport.addEventListener('touchend', function () { paused = false; }, { passive: true });

    function frame() {
      if (!paused) {
        pos += speed;
        if (pos >= setWidth) pos -= setWidth;
        track.style.transform = 'translate3d(' + (-pos) + 'px,0,0)';
      }
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      setTimeout(startFeaturedMarquee, 100);
    });
  } else {
    setTimeout(startFeaturedMarquee, 100);
  }
  window.addEventListener('load', function () {
    setTimeout(startFeaturedMarquee, 50);
  });
})();
