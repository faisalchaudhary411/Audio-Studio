// ===== VoxCraft — Contact form (progressive enhancement) =====
// The form works with plain method="post" with no JS at all (server-side
// behavior in app.py's /contact route is unchanged for that path). This
// only upgrades it to submit via fetch() so success/errors show inline
// instead of a full page reload — same server-side checks either way
// (honeypot, rate limit, timing token, disposable-email), just a
// different response shape (JSON vs. a re-rendered page) triggered by the
// X-Requested-With header below.
(function () {
  const form = document.getElementById('contact-form');
  if (!form) return;

  const successBox = document.getElementById('contact-success');
  const reqIdEl = document.getElementById('contact-req-id');
  const formErrorBox = document.getElementById('contact-form-error');
  const tokenField = document.getElementById('contact-token-field');
  const submitBtn = document.getElementById('contact-submit-btn');
  const submitLabel = document.getElementById('contact-submit-label');

  const fieldErrorEls = {
    name: document.getElementById('contact-name-error'),
    email: document.getElementById('contact-email-error'),
    message: document.getElementById('contact-message-error'),
  };

  function clearErrors() {
    formErrorBox.style.display = 'none';
    formErrorBox.textContent = '';
    Object.values(fieldErrorEls).forEach((el) => {
      if (!el) return;
      el.style.display = 'none';
      el.textContent = '';
    });
  }

  function showErrors(errors) {
    clearErrors();
    if (!errors) return;
    if (errors.form) {
      formErrorBox.textContent = errors.form;
      formErrorBox.style.display = 'block';
    }
    ['name', 'email', 'message'].forEach((field) => {
      if (errors[field] && fieldErrorEls[field]) {
        fieldErrorEls[field].textContent = errors[field];
        fieldErrorEls[field].style.display = 'block';
      }
    });
  }

  function setSubmitting(isSubmitting) {
    submitBtn.disabled = isSubmitting;
    submitLabel.textContent = isSubmitting ? 'Sending…' : 'Send message';
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearErrors();
    setSubmitting(true);

    try {
      const res = await fetch(form.action || window.location.href, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: new FormData(form),
      });

      // A fresh contact_token comes back on every response (success or
      // error) — the timing token is generated per-request server-side,
      // so keep the hidden field current in case of a retry after an
      // error, without the user ever seeing a page reload.
      let data = {};
      try { data = await res.json(); } catch (parseErr) { /* fall through to generic error below */ }

      if (data.contact_token && tokenField) tokenField.value = data.contact_token;

      if (data.redirect) {
        window.location.href = data.redirect;
        return; // leave the button disabled — we're navigating away
      }

      if (data.submitted) {
        form.style.display = 'none';
        if (reqIdEl && data.req_id) reqIdEl.textContent = data.req_id;
        else if (data.req_id) {
          // First submission ever with a req_id and no pre-existing
          // element (submitted wasn't server-rendered this time) —
          // build the line fresh.
          successBox.querySelector('p').innerHTML =
            'Message sent — reference <strong id="contact-req-id">' + data.req_id + '</strong>.';
        }
        successBox.style.display = 'block';
        successBox.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
      }

      if (!res.ok || data.errors) {
        showErrors(data.errors || { form: 'Something went wrong — please try again.' });
        setSubmitting(false);
        return;
      }

      // Unexpected shape — fail safe rather than leaving the button stuck.
      showErrors({ form: 'Something went wrong — please try again.' });
      setSubmitting(false);
    } catch (networkErr) {
      showErrors({ form: 'Network error — check your connection and try again.' });
      setSubmitting(false);
    }
  });
})();
