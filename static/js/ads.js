// ===== VoxCraft — Ads (interstitial), ported from show_interstitial_ad() =====
// Only meaningful for free users — pages pass window.VOXCRAFT_IS_PRO from Flask.
(function () {
  window.VoxCraftAds = window.VoxCraftAds || {};

  window.VoxCraftAds.showInterstitial = function (onDone) {
    if (window.VOXCRAFT_IS_PRO) {
      onDone();
      return;
    }

    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:99999;background:#101820;display:flex;align-items:center;justify-content:center;';
    overlay.innerHTML = `
      <div style="background:#182530;border:1px solid rgba(232,169,60,0.3);border-radius:20px;padding:1.5rem;max-width:460px;width:90%;text-align:center;">
        <div style="color:rgba(245,242,234,0.4);font-size:0.72rem;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.8rem;">Sponsored — Preparing Your Audio</div>
        <div style="min-height:120px;display:flex;align-items:center;justify-content:center;margin:0.5rem 0;" id="voxcraft-interstitial-slot"></div>
        <div style="color:rgba(245,242,234,0.45);font-size:0.85rem;margin:0.6rem 0;" id="voxcraft-interstitial-timer">Ad closes in 5s…</div>
        <button id="voxcraft-interstitial-skip" disabled style="background:#E8A93C;color:#1A1204;border:none;padding:0.6rem 1.4rem;border-radius:12px;font-weight:700;cursor:not-allowed;font-size:0.88rem;opacity:0.5;">Please wait…</button>
        <div style="color:rgba(245,242,234,0.25);font-size:0.75rem;margin-top:0.8rem;"><a href="/pricing" style="color:#E8A93C;text-decoration:none;">Remove ads with Pro →</a></div>
      </div>
    `;
    document.body.appendChild(overlay);

    const slot = overlay.querySelector('#voxcraft-interstitial-slot');
    const script = document.createElement('script');
    script.async = true;
    script.setAttribute('data-cfasync', 'false');
    script.src = 'https://pl29723111.effectivecpmnetwork.com/5b0c617f15e7e87967b22cafcc23e1b7/invoke.js';
    const container = document.createElement('div');
    container.id = 'container-5b0c617f15e7e87967b22cafcc23e1b7-interstitial';
    slot.appendChild(script);
    slot.appendChild(container);

    const timerEl = overlay.querySelector('#voxcraft-interstitial-timer');
    const skipBtn = overlay.querySelector('#voxcraft-interstitial-skip');
    let s = 5;

    function finish() {
      overlay.remove();
      onDone();
    }
    skipBtn.onclick = finish;

    const iv = setInterval(() => {
      s -= 1;
      if (s <= 0) {
        clearInterval(iv);
        finish();
      } else {
        timerEl.textContent = `Ad closes in ${s}s…`;
        if (s <= 2) {
          skipBtn.disabled = false;
          skipBtn.style.cursor = 'pointer';
          skipBtn.style.opacity = '1';
          skipBtn.textContent = `Skip Ad (${s})`;
        }
      }
    }, 1000);
  };
})();
