/**
 * VoxCraft audio background worker.
 * Decodes base64 → Uint8Array / Blob off the main thread so the UI stays responsive
 * even for large (20–50 MB+) clone / batch audio payloads.
 *
 * Message in:  { id, b64, mime, filename }
 * Message out: { id, ok: true, buffer: ArrayBuffer, mime, filename }
 *           or { id, ok: false, error: string }
 */
self.onmessage = function (e) {
  const msg = e.data || {};
  const id = msg.id;
  try {
    const b64 = msg.b64;
    if (!b64 || typeof b64 !== 'string') {
      self.postMessage({ id: id, ok: false, error: 'missing b64' });
      return;
    }
    // Pure base64 decode without atob on huge strings blocking (chunked)
    const binary = base64ToUint8Array(b64);
    const buffer = binary.buffer;
    self.postMessage(
      { id: id, ok: true, buffer: buffer, mime: msg.mime || 'audio/wav', filename: msg.filename || 'audio.wav' },
      [buffer]
    );
  } catch (err) {
    self.postMessage({ id: id, ok: false, error: (err && err.message) || String(err) });
  }
};

function base64ToUint8Array(b64) {
  // Strip data-url prefix if present
  const comma = b64.indexOf(',');
  if (comma !== -1 && b64.slice(0, comma).indexOf('base64') !== -1) {
    b64 = b64.slice(comma + 1);
  }
  // Remove whitespace
  b64 = b64.replace(/[\s\r\n]+/g, '');

  const lookup = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  const len = b64.length;
  // Approximate output length
  let padding = 0;
  if (len > 0 && b64[len - 1] === '=') padding++;
  if (len > 1 && b64[len - 2] === '=') padding++;
  const outLen = ((len * 3) / 4) - padding | 0;
  const out = new Uint8Array(outLen);

  let j = 0;
  for (let i = 0; i < len; i += 4) {
    const a = lookup.indexOf(b64[i]);
    const b = lookup.indexOf(b64[i + 1]);
    const c = b64[i + 2] === '=' ? 0 : lookup.indexOf(b64[i + 2]);
    const d = b64[i + 3] === '=' ? 0 : lookup.indexOf(b64[i + 3]);
    const n = (a << 18) | (b << 12) | (c << 6) | d;
    if (j < outLen) out[j++] = (n >> 16) & 0xff;
    if (j < outLen) out[j++] = (n >> 8) & 0xff;
    if (j < outLen) out[j++] = n & 0xff;
  }
  return out;
}
