// ===== VoxCraft — Ads (interstitial), ported from show_interstitial_ad() =====
// Only meaningful for free users — pages pass window.VOXCRAFT_IS_PRO from Flask.
(function () {
  window.VoxCraftAds = window.VoxCraftAds || {};

  window.VoxCraftAds.showInterstitial = function (onDone) {
    // Keep disruptive interstitials off by default while the site is being
    // reviewed for AdSense. The tool action continues immediately.
    if (!window.VOXCRAFT_ENABLE_INTERSTITIAL) {
      onDone();
      return;
    }
    if (window.VOXCRAFT_IS_PRO) {
      onDone();
      return;
    }

    // Show the interstitial only every 3rd generation, not on every single
    // click — the previous version fired before literally every generate
    // action across all 8 tools, which reads as disruptive/intrusive to
    // ad-experience reviews. Counter persists per-session (sessionStorage)
    // so it holds across navigating between different tool pages.
    const GEN_INTERVAL = 3;
    const count = (parseInt(sessionStorage.getItem('voxcraft_gen_count') || '0', 10) + 1);
    sessionStorage.setItem('voxcraft_gen_count', String(count));

    if (count % GEN_INTERVAL !== 0) {
      onDone();
      return;
    }

    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:99999;background:#101820;display:flex;align-items:center;justify-content:center;';
    const iframe = document.createElement('iframe');
    iframe.src = '/ads/slot/interstitial';
    iframe.style.cssText = 'width:100%;height:100%;border:0;';
    overlay.appendChild(iframe);
    document.body.appendChild(overlay);

    function onMessage(e) {
      if (e.data === 'voxcraft-interstitial-done') {
        window.removeEventListener('message', onMessage);
        overlay.remove();
        onDone();
      }
    }
    window.addEventListener('message', onMessage);

    // Safety net: if the iframe never loads (ad blocker, network issue),
    // don't trap the user — auto-continue after 6s regardless.
    setTimeout(() => {
      if (document.body.contains(overlay)) {
        window.removeEventListener('message', onMessage);
        overlay.remove();
        onDone();
      }
    }, 6000);
  };

  // ---- Popunder: once per session, on first button-like click (ported from POPUNDER_SCRIPT) ----
  // BUG FIX: this used to fire on ANY button/link click site-wide, including
  // the mobile nav hamburger toggle — so simply opening the nav menu popped
  // an ad tab. Excluding clicks inside the nav header entirely; this is
  // meant to trigger on content/tool interactions, not UI chrome.
  window.VoxCraftAds.initPopunder = function () {
    // Paused while AdSense reviews the site — see enable_popunder_ctx in
    // app.py for how to switch this back on (ENABLE_POPUNDER=1 env var,
    // no code change needed).
    if (!window.VOXCRAFT_ENABLE_POPUNDER) return;
    if (window.VOXCRAFT_IS_PRO) return;
    if (sessionStorage.getItem('voxcraft_popunder_shown')) return;
    let triggered = false;
    document.addEventListener('click', function (e) {
      if (triggered) return;
      if (e.target.closest('.nav')) return; // nav header (hamburger, nav links) never triggers this
      if (e.target.closest('button, a, [role="button"]')) {
        triggered = true;
        sessionStorage.setItem('voxcraft_popunder_shown', '1');
        setTimeout(function () {
          const w = window.open('about:blank', '_blank');
          if (w) {
            w.location = 'https://www.effectivecpmnetwork.com/y29b51ygf?key=6d81ae914eae0a29f481ed4a8117e686';
            w.blur();
            window.focus();
          }
        }, 300);
      }
    }, { once: true });
  };

  document.addEventListener('DOMContentLoaded', () => {
    window.VoxCraftAds.initPopunder();
  });
})();
