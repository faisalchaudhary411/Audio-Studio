# VoxCraft — API discoverability (the /developers page)

5 files, same repo structure. app.py confirmed built on the correct base
(CLONE_CHAR_LIMIT = 1400 intact).

## Files
- app.py (MODIFIED)
- templates/base.html (MODIFIED — footer link)
- templates/pricing.html (MODIFIED — cross-link)
- templates/contact.html (MODIFIED — new topic option)
- templates/developers.html (NEW)

## The gap this fixes

The API itself (POST /api/v1/tts, admin key issuance, quota tracking)
worked, but nothing on the site told anyone it existed. No nav link, no
footer link, no page explaining what it does or how to get access — the
only place "API" appeared was inside the admin panel and in an email that
only gets sent AFTER someone has already paid, which they can't do if
they never knew to ask in the first place.

## What this adds

**New page: /developers** — explains what the API does, a real curl
example, the response format (including the X-Quota-* headers), stated
limits (fixed monthly allowance, per-request cap, quota-only-on-success),
an honest explanation of why plans are sized per-customer rather than
fixed tiers (matches how admin_api_keys.html actually works — quota is a
free-form number, not a dropdown of preset plans), an FAQ with FAQPage
schema, and a "Request API access" CTA.

**Contact form gets a new topic**: "Developer API access" — so someone
clicking through from /developers lands on a pre-filled form instead of
having to guess which existing topic (Support? Partnership?) fits.
/contact now also accepts ?topic=X to pre-select any dropdown option, not
just this one.

**Discoverability wiring**: added to the footer (present on every page)
rather than the primary nav — nav is already fairly packed with links a
typical consumer visitor needs, and developers are a narrower audience
better served by a footer link plus a direct cross-link from Pricing
("Building your own app? See the developer API"), which is exactly where
someone evaluating paid plans would naturally look for this. Added to
sitemap.xml as well.

## Testing performed
- Python AST syntax check against the exact final merged app.py.
- Jinja2 parse check on all 4 touched/new templates.
- Full Flask render test: confirmed developers.html renders with the
  correct character limit pulled from the real API_MAX_CHARS_PER_REQUEST
  constant (not a hardcoded duplicate number that could drift out of
  sync), confirmed the FAQ JSON-LD is valid with all 5 Q&As, confirmed
  the footer link resolves correctly, confirmed pricing.html's cross-link
  renders, and confirmed contact.html correctly pre-selects the "API
  Access" topic when passed via the URL.
